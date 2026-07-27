import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, UUIDPrimaryKeyMixin


class CameraFrameAnalysis(Base, UUIDPrimaryKeyMixin):
    """
    Result of running one uploaded camera frame through the vision
    pipeline: object detection (vehicles/people) plus the classical
    smoke/fire color-heuristic. Persisted for audit/history, the same
    pattern as gas readings and predictions.
    """
    __tablename__ = "camera_frame_analyses"

    parking_area_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parking_areas.id"), nullable=False, index=True
    )

    vehicle_count: Mapped[int] = mapped_column(Integer, nullable=False)
    person_count: Mapped[int] = mapped_column(Integer, nullable=False)
    detected_objects: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    registered_parked_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unauthorized_parking_suspected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    smoke_detected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    smoke_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fire_detected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fire_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    alert_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("alerts.id"), nullable=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, default="yolov8n+color_heuristic_v1")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    parking_area: Mapped["ParkingArea"] = relationship()
    alert: Mapped["Alert"] = relationship()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CameraFrameAnalysis area={self.parking_area_id} vehicles={self.vehicle_count} fire={self.fire_detected}>"
