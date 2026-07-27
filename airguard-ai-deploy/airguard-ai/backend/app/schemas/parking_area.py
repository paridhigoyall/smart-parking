import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import RiskLevel


class ParkingAreaBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=20)
    zone_description: str | None = Field(default=None, max_length=500)
    capacity: int = Field(default=50, ge=0)
    map_x: float = 0.0
    map_y: float = 0.0
    latitude: float | None = None
    longitude: float | None = None


class ParkingAreaCreate(ParkingAreaBase):
    pass


class ParkingAreaUpdate(BaseModel):
    name: str | None = None
    zone_description: str | None = None
    capacity: int | None = Field(default=None, ge=0)
    occupied_slots: int | None = Field(default=None, ge=0)
    map_x: float | None = None
    map_y: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    is_closed: bool | None = None


class ParkingAreaRead(ParkingAreaBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    occupied_slots: int
    current_risk_level: RiskLevel
    current_risk_score: float
    is_closed: bool
