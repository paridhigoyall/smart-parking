import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, UUIDPrimaryKeyMixin


class MaintenanceLog(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "maintenance_logs"

    sensor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sensors.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)  # calibration/repair/battery_swap/inspection
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    performed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sensor: Mapped["Sensor"] = relationship(back_populates="maintenance_logs")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<MaintenanceLog sensor={self.sensor_id} event={self.event_type}>"
