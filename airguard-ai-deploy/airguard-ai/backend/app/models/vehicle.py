import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import VehicleStatus


class Vehicle(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "vehicles"

    plate_number: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    vehicle_type: Mapped[str] = mapped_column(String(50), default="car", nullable=False)  # car/truck/tanker/forklift
    driver_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    parking_area_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parking_areas.id"), nullable=True
    )
    status: Mapped[VehicleStatus] = mapped_column(default=VehicleStatus.ENTERED, nullable=False)

    entered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    parked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    exited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    parking_area: Mapped["ParkingArea"] = relationship(back_populates="vehicles")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Vehicle {self.plate_number} status={self.status}>"
