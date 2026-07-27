import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict


class AnalyticsRollupRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    parking_area_id: uuid.UUID
    period_type: str
    period_start: date
    avg_co: float | None
    avg_no2: float | None
    avg_co2: float | None
    max_smoke: float | None
    avg_pm25: float | None
    safe_hours: float
    moderate_hours: float
    unsafe_hours: float
    total_alerts: int
    environmental_score: float | None
    estimated_carbon_kg: float | None


class AnalyticsRollupGenerateResponse(BaseModel):
    rollup: AnalyticsRollupRead
    reading_count: int
