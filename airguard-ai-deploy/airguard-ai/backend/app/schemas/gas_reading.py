import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class GasReadingIngest(BaseModel):
    """
    Payload a sensor gateway posts for a single multi-gas telemetry sample.
    Every gas/environment field is optional — a sensor node may only report
    the subset of parameters it's physically equipped to measure — but at
    least one value must be present or the reading is meaningless.
    """
    sensor_id: uuid.UUID

    co: float | None = Field(default=None, ge=0, description="ppm")
    co2: float | None = Field(default=None, ge=0, description="ppm")
    no2: float | None = Field(default=None, ge=0, description="ppm")
    so2: float | None = Field(default=None, ge=0, description="ppm")
    nh3: float | None = Field(default=None, ge=0, description="ppm")
    h2s: float | None = Field(default=None, ge=0, description="ppm")
    methane: float | None = Field(default=None, ge=0, description="ppm")
    lpg: float | None = Field(default=None, ge=0, description="ppm")
    smoke: float | None = Field(default=None, ge=0, description="ppm")
    pm25: float | None = Field(default=None, ge=0, description="µg/m³")
    pm10: float | None = Field(default=None, ge=0, description="µg/m³")

    temperature: float | None = Field(default=None, description="°C")
    humidity: float | None = Field(default=None, ge=0, le=100, description="%")
    wind_speed: float | None = Field(default=None, ge=0, description="m/s")
    wind_direction: float | None = Field(default=None, ge=0, le=360, description="degrees")

    recorded_at: datetime | None = Field(
        default=None, description="Defaults to server time if the sensor gateway doesn't supply one"
    )

    @model_validator(mode="after")
    def _at_least_one_gas_value(self):
        gas_fields = ("co", "co2", "no2", "so2", "nh3", "h2s", "methane", "lpg", "smoke", "pm25", "pm10")
        if all(getattr(self, f) is None for f in gas_fields):
            raise ValueError("At least one gas concentration value must be provided")
        return self


class GasReadingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sensor_id: uuid.UUID
    parking_area_id: uuid.UUID

    co: float | None
    co2: float | None
    no2: float | None
    so2: float | None
    nh3: float | None
    h2s: float | None
    methane: float | None
    lpg: float | None
    smoke: float | None
    pm25: float | None
    pm10: float | None

    temperature: float | None
    humidity: float | None
    wind_speed: float | None
    wind_direction: float | None

    recorded_at: datetime
