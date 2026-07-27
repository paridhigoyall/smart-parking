from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.weather import WeatherRecord


class WeatherRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, *, source: str, **fields) -> WeatherRecord:
        record = WeatherRecord(source=source, **fields)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_latest(self) -> WeatherRecord | None:
        stmt = select(WeatherRecord).order_by(WeatherRecord.recorded_at.desc()).limit(1)
        return self.db.scalar(stmt)

    def list(self, limit: int = 100) -> list[WeatherRecord]:
        stmt = select(WeatherRecord).order_by(WeatherRecord.recorded_at.desc()).limit(limit)
        return list(self.db.scalars(stmt))
