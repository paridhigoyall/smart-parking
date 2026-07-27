"""
Historical Analytics Engine.

Computes a rollup of a parking area's conditions over a period (day/week/
month/year) from raw gas_readings and alerts: average/max gas levels,
hours spent in each risk band, alert counts, an overall environmental
score, and a rough carbon-footprint estimate.

Safe/Moderate/Unsafe hours are approximated by treating each reading as
representative of the time until the next reading (capped, so a long gap
in data doesn't get counted as hours of any risk level) — a reasonable
approximation for irregularly-sampled sensor data without needing a
separate time-series aggregation store.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.models.enums import RiskLevel
from app.models.gas_reading import GasReading
from app.services.risk_engine import risk_engine

# If the gap between two consecutive readings exceeds this, we don't know
# what happened in between (sensor offline?) — cap the attributed duration
# rather than assuming that risk level held for the whole gap.
MAX_ATTRIBUTED_GAP_MINUTES = 30

# Rough estimate: kg CO2-equivalent per ppm-hour of excess CO2 above
# ambient (~420ppm), scaled by a nominal enclosed-area air volume. This is
# a heuristic for a *relative* sustainability trend indicator, not a
# certified emissions calculation — labeled as such wherever it's surfaced.
CARBON_ESTIMATE_FACTOR = 0.0018
AMBIENT_CO2_PPM = 420.0


@dataclass
class RollupResult:
    reading_count: int
    avg_co: float | None = None
    avg_no2: float | None = None
    avg_co2: float | None = None
    max_smoke: float | None = None
    avg_pm25: float | None = None
    safe_hours: float = 0.0
    moderate_hours: float = 0.0
    unsafe_hours: float = 0.0
    total_alerts: int = 0
    environmental_score: float | None = None
    estimated_carbon_kg: float | None = None


class AnalyticsEngine:
    def compute_rollup(
        self, readings: list[GasReading], alert_count: int, *, period_end: datetime
    ) -> RollupResult:
        """`readings` must be sorted oldest -> newest, all within the period."""
        if not readings:
            return RollupResult(reading_count=0, total_alerts=alert_count)

        co_values = [r.co for r in readings if r.co is not None]
        no2_values = [r.no2 for r in readings if r.no2 is not None]
        co2_values = [r.co2 for r in readings if r.co2 is not None]
        smoke_values = [r.smoke for r in readings if r.smoke is not None]
        pm25_values = [r.pm25 for r in readings if r.pm25 is not None]

        hours_by_level = {RiskLevel.SAFE: 0.0, RiskLevel.MODERATE: 0.0, RiskLevel.UNSAFE: 0.0}
        air_quality_scores: list[float] = []

        for i, reading in enumerate(readings):
            assessment = risk_engine.classify(reading, now=reading.recorded_at)
            air_quality_scores.append(assessment.air_quality_score)

            next_time = readings[i + 1].recorded_at if i + 1 < len(readings) else period_end
            gap_minutes = (next_time - reading.recorded_at).total_seconds() / 60
            attributed_minutes = min(max(gap_minutes, 0), MAX_ATTRIBUTED_GAP_MINUTES)
            hours_by_level[assessment.risk_level] += attributed_minutes / 60

        environmental_score = sum(air_quality_scores) / len(air_quality_scores) if air_quality_scores else None

        avg_co2 = sum(co2_values) / len(co2_values) if co2_values else None
        estimated_carbon_kg = None
        if avg_co2 is not None:
            excess_ppm = max(0.0, avg_co2 - AMBIENT_CO2_PPM)
            total_hours = sum(hours_by_level.values())
            estimated_carbon_kg = round(excess_ppm * total_hours * CARBON_ESTIMATE_FACTOR, 3)

        return RollupResult(
            reading_count=len(readings),
            avg_co=self._avg(co_values),
            avg_no2=self._avg(no2_values),
            avg_co2=avg_co2,
            max_smoke=max(smoke_values) if smoke_values else None,
            avg_pm25=self._avg(pm25_values),
            safe_hours=round(hours_by_level[RiskLevel.SAFE], 3),
            moderate_hours=round(hours_by_level[RiskLevel.MODERATE], 3),
            unsafe_hours=round(hours_by_level[RiskLevel.UNSAFE], 3),
            total_alerts=alert_count,
            environmental_score=round(environmental_score, 2) if environmental_score is not None else None,
            estimated_carbon_kg=estimated_carbon_kg,
        )

    @staticmethod
    def _avg(values: list[float]) -> float | None:
        return round(sum(values) / len(values), 3) if values else None


analytics_engine = AnalyticsEngine()
