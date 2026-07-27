"""
Predictive Maintenance Engine.

Assesses a sensor's health from signals actually available on the device
record and its recent telemetry — no separate hardware diagnostics channel
exists, so this works entirely from what the platform already observes:

  - Battery level (as last reported by the device)
  - Time since last calibration
  - Time since the device was last heard from at all (staleness)
  - Flatlined readings — a sensor reporting the exact same value for an
    unrealistically long stretch is a classic stuck-sensor signature

Combines these into a 0-100 health score and a 0-1 failure probability,
each traceable to the specific issues found — same explainability
philosophy as the risk and recommendation engines.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.models.gas_reading import GasReading
from app.models.sensor import Sensor

STALE_WARNING_MINUTES = 30
STALE_CRITICAL_MINUTES = 120
CALIBRATION_DUE_DAYS = 90
CALIBRATION_OVERDUE_DAYS = 180
LOW_BATTERY_PCT = 25
CRITICAL_BATTERY_PCT = 10
FLATLINE_MIN_SAMPLES = 5


@dataclass
class MaintenanceAssessment:
    health_score: float          # 0-100, higher is healthier
    failure_probability: float   # 0-1
    calibration_needed: bool
    issues: list[str] = field(default_factory=list)
    suggested_status: str | None = None  # a SensorStatus value, if this assessment implies a change


class PredictiveMaintenanceEngine:
    def assess(
        self, sensor: Sensor, recent_readings: list[GasReading], *, now: datetime | None = None
    ) -> MaintenanceAssessment:
        now = now or datetime.now(timezone.utc)
        issues: list[str] = []
        deductions = 0.0  # accumulated health-score deduction, 0-100 scale
        suggested_status: str | None = None

        # --- Staleness -----------------------------------------------------
        if sensor.last_seen_at is None:
            issues.append("Sensor has never reported a reading")
            deductions += 40
            suggested_status = "offline"
        else:
            last_seen = sensor.last_seen_at
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            minutes_since_seen = (now - last_seen).total_seconds() / 60
            if minutes_since_seen > STALE_CRITICAL_MINUTES:
                issues.append(f"No data for {minutes_since_seen:.0f} minutes — likely offline")
                deductions += 40
                suggested_status = "offline"
            elif minutes_since_seen > STALE_WARNING_MINUTES:
                issues.append(f"No data for {minutes_since_seen:.0f} minutes")
                deductions += 15

        # --- Battery ---------------------------------------------------------
        if sensor.battery_level <= CRITICAL_BATTERY_PCT:
            issues.append(f"Battery critically low ({sensor.battery_level:.0f}%)")
            deductions += 25
        elif sensor.battery_level <= LOW_BATTERY_PCT:
            issues.append(f"Battery low ({sensor.battery_level:.0f}%)")
            deductions += 10

        # --- Calibration -----------------------------------------------------
        calibration_needed = False
        if sensor.last_calibrated_at is None:
            issues.append("Never calibrated")
            calibration_needed = True
            deductions += 15
        else:
            calibrated_at = sensor.last_calibrated_at
            if calibrated_at.tzinfo is None:
                calibrated_at = calibrated_at.replace(tzinfo=timezone.utc)
            days_since_cal = (now - calibrated_at).total_seconds() / 86400
            if days_since_cal > CALIBRATION_OVERDUE_DAYS:
                issues.append(f"Calibration overdue by {days_since_cal - CALIBRATION_OVERDUE_DAYS:.0f} days")
                calibration_needed = True
                deductions += 20
            elif days_since_cal > CALIBRATION_DUE_DAYS:
                issues.append(f"Calibration due (last calibrated {days_since_cal:.0f} days ago)")
                calibration_needed = True
                deductions += 8

        # --- Flatline detection ------------------------------------------
        flatline_gas = self._detect_flatline(recent_readings)
        if flatline_gas:
            issues.append(f"{flatline_gas.upper()} readings have been identical for {FLATLINE_MIN_SAMPLES}+ consecutive samples — possible stuck sensor")
            deductions += 20
            suggested_status = suggested_status or "faulty"

        health_score = max(0.0, 100.0 - deductions)
        failure_probability = min(1.0, deductions / 100.0)

        return MaintenanceAssessment(
            health_score=round(health_score, 1),
            failure_probability=round(failure_probability, 3),
            calibration_needed=calibration_needed,
            issues=issues,
            suggested_status=suggested_status,
        )

    @staticmethod
    def _detect_flatline(readings: list[GasReading]) -> str | None:
        """Readings should be sorted newest-first. Returns the gas name if any
        tracked gas has been reporting an identical value for
        FLATLINE_MIN_SAMPLES+ consecutive samples."""
        if len(readings) < FLATLINE_MIN_SAMPLES:
            return None

        from app.services.risk_engine import _TRACKED_GASES

        window = readings[:FLATLINE_MIN_SAMPLES]
        for gas in _TRACKED_GASES:
            values = [getattr(r, gas, None) for r in window]
            if any(v is None for v in values):
                continue
            if len(set(values)) == 1 and values[0] != 0:
                # all identical and non-zero (zero-flatlines are common and
                # legitimate for e.g. LPG sensors in a clean area)
                return gas
        return None


maintenance_engine = PredictiveMaintenanceEngine()
