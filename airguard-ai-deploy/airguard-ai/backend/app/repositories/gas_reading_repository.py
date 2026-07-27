from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.gas_reading import GasReading


class GasReadingRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, *, sensor_id: uuid.UUID, parking_area_id: uuid.UUID, **fields) -> GasReading:
        reading = GasReading(sensor_id=sensor_id, parking_area_id=parking_area_id, **fields)
        self.db.add(reading)
        self.db.commit()
        self.db.refresh(reading)
        return reading

    def get_latest_for_area(self, parking_area_id: uuid.UUID) -> GasReading | None:
        stmt = (
            select(GasReading)
            .where(GasReading.parking_area_id == parking_area_id)
            .order_by(GasReading.recorded_at.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def get_latest_for_sensor(self, sensor_id: uuid.UUID) -> GasReading | None:
        stmt = (
            select(GasReading)
            .where(GasReading.sensor_id == sensor_id)
            .order_by(GasReading.recorded_at.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        parking_area_id: uuid.UUID | None = None,
        sensor_id: uuid.UUID | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[GasReading]:
        stmt = select(GasReading)
        if parking_area_id is not None:
            stmt = stmt.where(GasReading.parking_area_id == parking_area_id)
        if sensor_id is not None:
            stmt = stmt.where(GasReading.sensor_id == sensor_id)
        if start is not None:
            stmt = stmt.where(GasReading.recorded_at >= start)
        if end is not None:
            stmt = stmt.where(GasReading.recorded_at <= end)
        stmt = stmt.order_by(GasReading.recorded_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt))
