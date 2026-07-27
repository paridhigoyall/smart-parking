"""
Orchestration layer for Module 3: pulls every open parking area's latest
reading, runs it through the risk engine, and hands the results to the
recommendation engine to produce a ranked list + explanation + suggested
safety actions. Also persists a snapshot of recommendations for audit /
history purposes.
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.enums import RiskLevel
from app.repositories.gas_reading_repository import GasReadingRepository
from app.repositories.parking_area_repository import ParkingAreaRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.services.recommendation_engine import (
    ActionSuggestion,
    ParkingRecommendation,
    RankedArea,
    recommendation_engine,
)
from app.services.risk_engine import risk_engine


class ParkingRecommendationService:
    def __init__(self, db: Session):
        self.db = db
        self.areas = ParkingAreaRepository(db)
        self.readings = GasReadingRepository(db)
        self.recommendations = RecommendationRepository(db)

    def _ranked_areas(self, *, include_closed: bool = False) -> list[RankedArea]:
        ranked: list[RankedArea] = []
        for area in self.areas.list(limit=500):
            if area.is_closed and not include_closed:
                continue
            reading = self.readings.get_latest_for_area(area.id)
            if reading is None:
                continue  # no data yet — can't be assessed, so can't be recommended
            assessment = risk_engine.classify(reading)
            ranked.append(RankedArea(area=area, assessment=assessment))
        return ranked

    def get_recommendation(self, *, persist: bool = True) -> ParkingRecommendation:
        ranked = self._ranked_areas()
        result = recommendation_engine.recommend(ranked)

        if persist:
            for r in result.ranked_areas:
                action = (
                    recommendation_engine.suggest_actions(r.assessment, r.area.name)[0].action
                )
                self.recommendations.create(
                    parking_area_id=r.area.id,
                    action=action,
                    rank=r.rank,
                    risk_score=r.assessment.risk_score,
                    exposure_score=r.assessment.exposure_label,
                    confidence_score=r.assessment.confidence_score,
                    air_quality_score=r.assessment.air_quality_score,
                    explanation=(
                        result.explanation if r is result.top_choice
                        else f"Ranked #{r.rank} — risk score {r.assessment.risk_score:.0f}/100 "
                             f"({r.assessment.risk_level.value})."
                    ),
                )

        return result

    def get_actions_for_area(self, area_id: uuid.UUID) -> tuple[list[ActionSuggestion], RiskLevel] | None:
        area = self.areas.get(area_id)
        if area is None:
            return None
        reading = self.readings.get_latest_for_area(area_id)
        if reading is None:
            return None
        assessment = risk_engine.classify(reading)
        return recommendation_engine.suggest_actions(assessment, area.name), assessment.risk_level
