from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy.orm import Session

from app.repositories.alert_repository import AlertRepository
from app.repositories.analytics_rollup_repository import AnalyticsRollupRepository
from app.repositories.gas_reading_repository import GasReadingRepository
from app.repositories.parking_area_repository import ParkingAreaRepository
from app.services.analytics_engine import RollupResult, analytics_engine

_PERIOD_LENGTHS = {
    "daily": timedelta(days=1),
    "weekly": timedelta(weeks=1),
    "monthly": timedelta(days=30),  # approximate on purpose — a calendar-exact
                                     # month rollup is a fine follow-up
    "yearly": timedelta(days=365),
}


class AnalyticsError(Exception):
    pass


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db
        self.areas = ParkingAreaRepository(db)
        self.readings = GasReadingRepository(db)
        self.alerts = AlertRepository(db)
        self.rollups = AnalyticsRollupRepository(db)

    def generate_rollup(self, parking_area_id: uuid.UUID, period_type: str, period_start: date):
        if period_type not in _PERIOD_LENGTHS:
            raise AnalyticsError(f"Unknown period_type '{period_type}'; expected one of {list(_PERIOD_LENGTHS)}")

        area = self.areas.get(parking_area_id)
        if area is None:
            raise AnalyticsError(f"Parking area {parking_area_id} not found")

        start_dt = datetime.combine(period_start, time.min, tzinfo=timezone.utc)
        end_dt = start_dt + _PERIOD_LENGTHS[period_type]

        readings = self.readings.list(parking_area_id=parking_area_id, start=start_dt, end=end_dt, limit=100_000)
        readings = list(reversed(readings))  # repo returns newest-first; engine wants oldest-first

        area_alerts = self.alerts.list(parking_area_id=parking_area_id, limit=100_000)
        alert_count = sum(1 for a in area_alerts if start_dt <= a.created_at.replace(tzinfo=timezone.utc) < end_dt)

        result: RollupResult = analytics_engine.compute_rollup(readings, alert_count, period_end=end_dt)

        rollup = self.rollups.upsert(
            parking_area_id=parking_area_id,
            period_type=period_type,
            period_start=period_start,
            avg_co=result.avg_co,
            avg_no2=result.avg_no2,
            avg_co2=result.avg_co2,
            max_smoke=result.max_smoke,
            avg_pm25=result.avg_pm25,
            safe_hours=result.safe_hours,
            moderate_hours=result.moderate_hours,
            unsafe_hours=result.unsafe_hours,
            total_alerts=result.total_alerts,
            environmental_score=result.environmental_score,
            estimated_carbon_kg=result.estimated_carbon_kg,
        )
        return rollup, result.reading_count
