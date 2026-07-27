import uuid
from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, UUIDPrimaryKeyMixin


class AnalyticsRollup(Base, UUIDPrimaryKeyMixin):
    """
    Precomputed aggregate statistics per parking area per period, used to
    power the historical analytics & sustainability dashboards without
    scanning raw gas_readings on every request.
    """
    __tablename__ = "analytics_rollups"
    __table_args__ = (
        UniqueConstraint("parking_area_id", "period_type", "period_start", name="uq_rollup_period"),
    )

    parking_area_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("parking_areas.id"), nullable=False, index=True
    )
    period_type: Mapped[str] = mapped_column(String(20), nullable=False)  # daily/weekly/monthly/yearly
    period_start: Mapped[date] = mapped_column(Date, nullable=False)

    avg_co: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_no2: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_co2: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_smoke: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_pm25: Mapped[float | None] = mapped_column(Float, nullable=True)
    unsafe_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    moderate_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    safe_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_alerts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    environmental_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-100
    estimated_carbon_kg: Mapped[float | None] = mapped_column(Float, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AnalyticsRollup {self.period_type} {self.period_start} area={self.parking_area_id}>"
