from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import RiskLevel
from app.models.parking_area import ParkingArea
from app.schemas.parking_area import ParkingAreaCreate, ParkingAreaUpdate


class ParkingAreaRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, area_id: uuid.UUID) -> ParkingArea | None:
        return self.db.get(ParkingArea, area_id)

    def get_by_code(self, code: str) -> ParkingArea | None:
        return self.db.scalar(select(ParkingArea).where(ParkingArea.code == code))

    def list(self, skip: int = 0, limit: int = 100) -> list[ParkingArea]:
        return list(
            self.db.scalars(select(ParkingArea).order_by(ParkingArea.code).offset(skip).limit(limit))
        )

    def create(self, payload: ParkingAreaCreate) -> ParkingArea:
        area = ParkingArea(**payload.model_dump())
        self.db.add(area)
        self.db.commit()
        self.db.refresh(area)
        return area

    def update(self, area: ParkingArea, payload: ParkingAreaUpdate) -> ParkingArea:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(area, field, value)
        self.db.commit()
        self.db.refresh(area)
        return area

    def update_risk_state(self, area: ParkingArea, risk_level: RiskLevel, risk_score: float) -> ParkingArea:
        area.current_risk_level = risk_level
        area.current_risk_score = risk_score
        self.db.commit()
        self.db.refresh(area)
        return area

    def delete(self, area: ParkingArea) -> None:
        self.db.delete(area)
        self.db.commit()
