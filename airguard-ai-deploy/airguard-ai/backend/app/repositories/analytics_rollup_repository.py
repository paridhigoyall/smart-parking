from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analytics import AnalyticsRollup


class AnalyticsRollupRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, parking_area_id: uuid.UUID, period_type: str, period_start: date) -> AnalyticsRollup | None:
        stmt = select(AnalyticsRollup).where(
            AnalyticsRollup.parking_area_id == parking_area_id,
            AnalyticsRollup.period_type == period_type,
            AnalyticsRollup.period_start == period_start,
        )
        return self.db.scalar(stmt)

    def upsert(self, *, parking_area_id: uuid.UUID, period_type: str, period_start: date, **fields) -> AnalyticsRollup:
        existing = self.get(parking_area_id, period_type, period_start)
        if existing:
            for k, v in fields.items():
                setattr(existing, k, v)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        rollup = AnalyticsRollup(
            parking_area_id=parking_area_id, period_type=period_type, period_start=period_start, **fields
        )
        self.db.add(rollup)
        self.db.commit()
        self.db.refresh(rollup)
        return rollup

    def list(
        self, *, parking_area_id: uuid.UUID | None = None, period_type: str | None = None, limit: int = 100
    ) -> list[AnalyticsRollup]:
        stmt = select(AnalyticsRollup)
        if parking_area_id is not None:
            stmt = stmt.where(AnalyticsRollup.parking_area_id == parking_area_id)
        if period_type is not None:
            stmt = stmt.where(AnalyticsRollup.period_type == period_type)
        stmt = stmt.order_by(AnalyticsRollup.period_start.desc()).limit(limit)
        return list(self.db.scalars(stmt))
