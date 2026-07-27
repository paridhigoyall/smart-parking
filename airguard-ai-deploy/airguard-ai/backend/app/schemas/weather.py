import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WeatherRecordCreate(BaseModel):
    temperature: float | None = None
    humidity: float | None = None
    wind_speed: float | None = None
    wind_direction: float | None = None
    rain_mm: float | None = None
    pressure_hpa: float | None = None
    forecast_summary: str | None = None


class WeatherRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    temperature: float | None
    humidity: float | None
    wind_speed: float | None
    wind_direction: float | None
    rain_mm: float | None
    pressure_hpa: float | None
    forecast_summary: str | None
    recorded_at: datetime
