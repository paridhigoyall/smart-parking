from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import RiskLevel


class ParkingArea(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "parking_areas"

    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "Parking A"
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    zone_description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    capacity: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    occupied_slots: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Map coordinates (relative x/y on the plant map, 0-1000 canvas space)
    map_x: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    map_y: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    current_risk_level: Mapped[RiskLevel] = mapped_column(default=RiskLevel.SAFE, nullable=False)
    current_risk_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_closed: Mapped[bool] = mapped_column(default=False, nullable=False)

    sensors: Mapped[list["Sensor"]] = relationship(back_populates="parking_area")
    gas_readings: Mapped[list["GasReading"]] = relationship(back_populates="parking_area")
    predictions: Mapped[list["Prediction"]] = relationship(back_populates="parking_area")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="parking_area")
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="parking_area")
    vehicles: Mapped[list["Vehicle"]] = relationship(back_populates="parking_area")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ParkingArea {self.code} risk={self.current_risk_level}>"
