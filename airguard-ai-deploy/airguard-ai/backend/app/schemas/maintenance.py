import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MaintenanceLogCreate(BaseModel):
    event_type: str = Field(description="calibration | repair | battery_swap | inspection")
    notes: str | None = None
    performed_by: str | None = None


class MaintenanceLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sensor_id: uuid.UUID
    event_type: str
    notes: str | None
    performed_by: str | None
    created_at: datetime


class MaintenanceAssessmentRead(BaseModel):
    sensor_id: uuid.UUID
    health_score: float
    failure_probability: float
    calibration_needed: bool
    issues: list[str]
    suggested_status: str | None
    assessed_at: datetime
