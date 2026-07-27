import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SensorStatus, SensorType


class SensorBase(BaseModel):
    serial_number: str = Field(min_length=1, max_length=100)
    sensor_type: SensorType
    parking_area_id: uuid.UUID
    firmware_version: str | None = None
    install_location: str | None = None


class SensorCreate(SensorBase):
    pass


class SensorUpdate(BaseModel):
    status: SensorStatus | None = None
    battery_level: float | None = Field(default=None, ge=0, le=100)
    firmware_version: str | None = None
    install_location: str | None = None
    parking_area_id: uuid.UUID | None = None


class SensorRead(SensorBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: SensorStatus
    battery_level: float
    health_score: float
    failure_probability: float
    last_calibrated_at: datetime | None
    last_seen_at: datetime | None
