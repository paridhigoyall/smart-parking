import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import RiskLevel


class GasFactorRead(BaseModel):
    gas: str
    value: float
    threshold: float
    percent_of_threshold: float
    weight: float


class RiskAssessmentRead(BaseModel):
    parking_area_id: uuid.UUID
    parking_area_code: str
    risk_score: float
    risk_level: RiskLevel
    exposure_label: str
    confidence_score: float
    air_quality_score: float
    dominant_gas: str | None
    data_completeness: float
    reading_age_seconds: float | None
    assessed_at: datetime
    factors: list[GasFactorRead]
    based_on_reading_id: uuid.UUID | None = None
