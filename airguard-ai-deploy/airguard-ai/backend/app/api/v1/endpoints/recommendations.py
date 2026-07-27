import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.recommendation_repository import RecommendationRepository
from app.schemas.recommendation import (
    ActionSupportRead,
    ActionSuggestionRead,
    ParkingRecommendationRead,
    RankedAreaRead,
    RecommendationHistoryRead,
)
from app.schemas.risk import GasFactorRead, RiskAssessmentRead
from app.services.parking_recommendation_service import ParkingRecommendationService

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


def _assessment_to_schema(area_id: uuid.UUID, area_code: str, assessment, reading_id=None) -> RiskAssessmentRead:
    return RiskAssessmentRead(
        parking_area_id=area_id,
        parking_area_code=area_code,
        risk_score=assessment.risk_score,
        risk_level=assessment.risk_level,
        exposure_label=assessment.exposure_label,
        confidence_score=assessment.confidence_score,
        air_quality_score=assessment.air_quality_score,
        dominant_gas=assessment.dominant_gas,
        data_completeness=assessment.data_completeness,
        reading_age_seconds=assessment.reading_age_seconds,
        assessed_at=assessment.assessed_at,
        factors=[
            GasFactorRead(gas=f.gas, value=f.value, threshold=f.threshold,
                          percent_of_threshold=f.percent_of_threshold, weight=f.weight)
            for f in assessment.factors
        ],
        based_on_reading_id=reading_id,
    )


@router.get("/parking", response_model=ParkingRecommendationRead)
def recommend_parking(
    persist: bool = Query(default=True, description="Store this recommendation snapshot for audit history"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Rank every open parking area with current sensor data and recommend the
    safest one, with a plain-language explanation of why it was chosen over
    the runner-up.
    """
    service = ParkingRecommendationService(db)
    result = service.get_recommendation(persist=persist)

    if not result.ranked_areas:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No open parking areas currently have sensor data to base a recommendation on.",
        )

    return ParkingRecommendationRead(
        generated_at=datetime.now(timezone.utc),
        top_choice_area_id=result.top_choice.area.id if result.top_choice else None,
        top_choice_area_name=result.top_choice.area.name if result.top_choice else None,
        explanation=result.explanation,
        ranked_areas=[
            RankedAreaRead(
                rank=r.rank,
                parking_area_id=r.area.id,
                parking_area_code=r.area.code,
                parking_area_name=r.area.name,
                assessment=_assessment_to_schema(r.area.id, r.area.code, r.assessment),
            )
            for r in result.ranked_areas
        ],
    )


@router.get("/actions/{area_id}", response_model=ActionSupportRead)
def get_suggested_actions(
    area_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    AI decision support for a single parking area: what should be done
    right now — park here, ventilate, delay entry, close the area,
    activate exhaust, or evacuate — based on its latest reading.
    """
    service = ParkingRecommendationService(db)
    result = service.get_actions_for_area(area_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parking area not found or has no sensor data yet.",
        )
    suggestions, risk_level = result
    return ActionSupportRead(
        parking_area_id=area_id,
        risk_level=risk_level,
        suggestions=[ActionSuggestionRead(action=s.action, reason=s.reason) for s in suggestions],
    )


@router.get("/history", response_model=list[RecommendationHistoryRead])
def get_recommendation_history(
    parking_area_id: uuid.UUID | None = Query(default=None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list:
    return RecommendationRepository(db).list(parking_area_id=parking_area_id, skip=skip, limit=limit)
