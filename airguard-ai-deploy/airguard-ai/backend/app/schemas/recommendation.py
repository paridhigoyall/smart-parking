import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import RecommendationAction, RiskLevel
from app.schemas.risk import RiskAssessmentRead


class RankedAreaRead(BaseModel):
    rank: int
    parking_area_id: uuid.UUID
    parking_area_code: str
    parking_area_name: str
    assessment: RiskAssessmentRead


class ParkingRecommendationRead(BaseModel):
    generated_at: datetime
    top_choice_area_id: uuid.UUID | None
    top_choice_area_name: str | None
    explanation: str
    ranked_areas: list[RankedAreaRead]


class ActionSuggestionRead(BaseModel):
    action: RecommendationAction
    reason: str


class ActionSupportRead(BaseModel):
    parking_area_id: uuid.UUID
    risk_level: RiskLevel
    suggestions: list[ActionSuggestionRead]


class RecommendationHistoryRead(BaseModel):
    id: uuid.UUID
    parking_area_id: uuid.UUID
    action: RecommendationAction
    rank: int
    risk_score: float
    exposure_score: str
    confidence_score: float
    air_quality_score: float
    explanation: str
    model_version: str
    created_at: datetime

    model_config = {"from_attributes": True, "protected_namespaces": ()}
