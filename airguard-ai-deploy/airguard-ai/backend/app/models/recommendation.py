import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, UUIDPrimaryKeyMixin
from app.models.enums import RecommendationAction


class Recommendation(Base, UUIDPrimaryKeyMixin):
    """
    An AI-generated recommendation (which parking area to use, or which
    safety action to take) together with a human-readable explanation of
    *why* the recommendation engine reached that conclusion.
    """
    __tablename__ = "recommendations"

    parking_area_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parking_areas.id"), nullable=False, index=True
    )
    action: Mapped[RecommendationAction] = mapped_column(nullable=False)
    rank: Mapped[int] = mapped_column(default=1, nullable=False)  # 1 = top recommendation

    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    exposure_score: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "Very Low"
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    air_quality_score: Mapped[float] = mapped_column(Float, nullable=False)

    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), default="rule_engine_v1", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    parking_area: Mapped["ParkingArea"] = relationship(back_populates="recommendations")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Recommendation area={self.parking_area_id} action={self.action} rank={self.rank}>"
