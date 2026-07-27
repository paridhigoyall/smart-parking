import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import VehicleStatus


class VehicleEntryCreate(BaseModel):
    plate_number: str = Field(min_length=1, max_length=20)
    vehicle_type: str = Field(default="car", description="car | truck | tanker | forklift")
    driver_name: str | None = None


class VehicleParkRequest(BaseModel):
    parking_area_id: uuid.UUID


class VehicleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    plate_number: str
    vehicle_type: str
    driver_name: str | None
    parking_area_id: uuid.UUID | None
    status: VehicleStatus
    entered_at: datetime | None
    parked_at: datetime | None
    exited_at: datetime | None
