from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import SensorStatus
from app.models.sensor import Sensor
from app.schemas.sensor import SensorCreate, SensorUpdate


class SensorRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, sensor_id: uuid.UUID) -> Sensor | None:
        return self.db.get(Sensor, sensor_id)

    def get_by_serial(self, serial_number: str) -> Sensor | None:
        return self.db.scalar(select(Sensor).where(Sensor.serial_number == serial_number))

    def list(
        self, parking_area_id: uuid.UUID | None = None, skip: int = 0, limit: int = 100
    ) -> list[Sensor]:
        stmt = select(Sensor)
        if parking_area_id is not None:
            stmt = stmt.where(Sensor.parking_area_id == parking_area_id)
        stmt = stmt.order_by(Sensor.serial_number).offset(skip).limit(limit)
        return list(self.db.scalars(stmt))

    def create(self, payload: SensorCreate) -> Sensor:
        sensor = Sensor(**payload.model_dump())
        self.db.add(sensor)
        self.db.commit()
        self.db.refresh(sensor)
        return sensor

    def update(self, sensor: Sensor, payload: SensorUpdate) -> Sensor:
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(sensor, field, value)
        self.db.commit()
        self.db.refresh(sensor)
        return sensor

    def mark_seen(self, sensor: Sensor, at: datetime | None = None) -> Sensor:
        sensor.last_seen_at = at or datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(sensor)
        return sensor

    def update_health(
        self, sensor: Sensor, *, health_score: float, failure_probability: float, status: SensorStatus | None = None
    ) -> Sensor:
        sensor.health_score = health_score
        sensor.failure_probability = failure_probability
        if status is not None:
            sensor.status = status
        self.db.commit()
        self.db.refresh(sensor)
        return sensor

    def record_calibration(self, sensor: Sensor, at: datetime | None = None) -> Sensor:
        sensor.last_calibrated_at = at or datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(sensor)
        return sensor

    def reset_battery(self, sensor: Sensor, level: float = 100.0) -> Sensor:
        sensor.battery_level = level
        self.db.commit()
        self.db.refresh(sensor)
        return sensor

    def delete(self, sensor: Sensor) -> None:
        self.db.delete(sensor)
        self.db.commit()
