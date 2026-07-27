import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import RiskLevel


class GasForecastRead(BaseModel):
    gas: str
    current_value: float
    predicted_value: float
    trend: str
    slope_per_minute: float
    r_squared: float
    confidence: float
    data_points: int


class AreaForecastRead(BaseModel):
    parking_area_id: uuid.UUID
    horizon_minutes: int
    target_at: datetime
    predicted_risk_level: RiskLevel | None
    predicted_risk_score: float
    dominant_gas: str | None
    confidence: float
    gas_forecasts: list[GasForecastRead]


class PredictionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    parking_area_id: uuid.UUID
    horizon_minutes: int
    model_name: str
    predicted_values: dict[str, float]
    gas_trends: dict[str, str]
    predicted_risk_level: RiskLevel
    predicted_risk_score: float
    dominant_gas: str | None
    confidence: float
    generated_at: datetime
    target_at: datetime


class TrendPoint(BaseModel):
    timestamp: datetime
    value: float
    kind: str  # "actual" | "forecast"


class TrendChartRead(BaseModel):
    parking_area_id: uuid.UUID
    gas: str
    unit: str
    points: list[TrendPoint]
