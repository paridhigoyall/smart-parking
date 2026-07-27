import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import SensorStatus, SensorType


class Sensor(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "sensors"

    serial_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    sensor_type: Mapped[SensorType] = mapped_column(nullable=False)
    parking_area_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parking_areas.id"), nullable=False
    )

    status: Mapped[SensorStatus] = mapped_column(default=SensorStatus.ONLINE, nullable=False)
    battery_level: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)  # percent
    health_score: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)  # 0-100
    failure_probability: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # 0-1
    last_calibrated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    firmware_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    install_location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    parking_area: Mapped["ParkingArea"] = relationship(back_populates="sensors")
    gas_readings: Mapped[list["GasReading"]] = relationship(back_populates="sensor")
    maintenance_logs: Mapped[list["MaintenanceLog"]] = relationship(back_populates="sensor")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Sensor {self.serial_number} type={self.sensor_type} status={self.status}>"
