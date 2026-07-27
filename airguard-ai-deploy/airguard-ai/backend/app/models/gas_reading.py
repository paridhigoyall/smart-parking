import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, UUIDPrimaryKeyMixin


class GasReading(Base, UUIDPrimaryKeyMixin):
    """
    A single timestamped telemetry sample from one sensor.
    High write-volume table — kept lean and indexed for time-series queries.
    """
    __tablename__ = "gas_readings"
    __table_args__ = (
        Index("ix_gas_readings_parking_time", "parking_area_id", "recorded_at"),
        Index("ix_gas_readings_sensor_time", "sensor_id", "recorded_at"),
    )

    sensor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sensors.id"), nullable=False)
    parking_area_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parking_areas.id"), nullable=False
    )

    # Gas concentrations (ppm unless noted)
    co: Mapped[float | None] = mapped_column(Float, nullable=True)
    co2: Mapped[float | None] = mapped_column(Float, nullable=True)
    no2: Mapped[float | None] = mapped_column(Float, nullable=True)
    so2: Mapped[float | None] = mapped_column(Float, nullable=True)
    nh3: Mapped[float | None] = mapped_column(Float, nullable=True)
    h2s: Mapped[float | None] = mapped_column(Float, nullable=True)
    methane: Mapped[float | None] = mapped_column(Float, nullable=True)
    lpg: Mapped[float | None] = mapped_column(Float, nullable=True)
    smoke: Mapped[float | None] = mapped_column(Float, nullable=True)
    pm25: Mapped[float | None] = mapped_column(Float, nullable=True)  # µg/m³
    pm10: Mapped[float | None] = mapped_column(Float, nullable=True)  # µg/m³

    # Environment
    temperature: Mapped[float | None] = mapped_column(Float, nullable=True)  # °C
    humidity: Mapped[float | None] = mapped_column(Float, nullable=True)     # %
    wind_speed: Mapped[float | None] = mapped_column(Float, nullable=True)   # m/s
    wind_direction: Mapped[float | None] = mapped_column(Float, nullable=True)  # degrees 0-360

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    sensor: Mapped["Sensor"] = relationship(back_populates="gas_readings")
    parking_area: Mapped["ParkingArea"] = relationship(back_populates="gas_readings")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<GasReading parking={self.parking_area_id} at={self.recorded_at}>"
