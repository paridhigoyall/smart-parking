import uuid
from datetime import datetime

from sqlalchemy import ARRAY, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, UUIDPrimaryKeyMixin
from app.models.enums import AlertChannel, AlertSeverity, AlertStatus


class Alert(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "alerts"

    parking_area_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parking_areas.id"), nullable=False, index=True
    )
    triggered_by_reading_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gas_readings.id"), nullable=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(nullable=False)
    status: Mapped[AlertStatus] = mapped_column(default=AlertStatus.OPEN, nullable=False)
    channels: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    gas_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    measured_value: Mapped[float | None] = mapped_column(nullable=True)
    threshold_value: Mapped[float | None] = mapped_column(nullable=True)

    acknowledged_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    parking_area: Mapped["ParkingArea"] = relationship(back_populates="alerts")
    acknowledged_by: Mapped["User"] = relationship(back_populates="acknowledged_alerts")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Alert {self.severity} '{self.title}' status={self.status}>"
