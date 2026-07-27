from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import RecommendationAction
from app.models.recommendation import Recommendation


class RecommendationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        parking_area_id: uuid.UUID,
        action: RecommendationAction,
        rank: int,
        risk_score: float,
        exposure_score: str,
        confidence_score: float,
        air_quality_score: float,
        explanation: str,
        model_version: str = "rule_engine_v1",
    ) -> Recommendation:
        rec = Recommendation(
            parking_area_id=parking_area_id,
            action=action,
            rank=rank,
            risk_score=risk_score,
            exposure_score=exposure_score,
            confidence_score=confidence_score,
            air_quality_score=air_quality_score,
            explanation=explanation,
            model_version=model_version,
        )
        self.db.add(rec)
        self.db.commit()
        self.db.refresh(rec)
        return rec

    def list(
        self, *, parking_area_id: uuid.UUID | None = None, skip: int = 0, limit: int = 100
    ) -> list[Recommendation]:
        stmt = select(Recommendation)
        if parking_area_id is not None:
            stmt = stmt.where(Recommendation.parking_area_id == parking_area_id)
        stmt = stmt.order_by(Recommendation.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt))

    def get_latest_for_area(self, parking_area_id: uuid.UUID) -> Recommendation | None:
        stmt = (
            select(Recommendation)
            .where(Recommendation.parking_area_id == parking_area_id)
            .order_by(Recommendation.created_at.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)
