"""
Sensor ingestion orchestration.

This is the single entry point every incoming telemetry sample flows
through: persist the raw reading, run it through the risk engine, update
the owning parking area's live risk state, keep the sensor's "last seen"
timestamp fresh, and — if the reading crosses into UNSAFE territory — raise
a dashboard alert (email/SMS/push delivery is wired up in the Alerting
module; this module only creates the alert record).
"""
from dataclasses import dataclass
import logging

from sqlalchemy.orm import Session

from app.models.enums import AlertChannel, AlertSeverity, RiskLevel
from app.models.gas_reading import GasReading
from app.models.sensor import Sensor
from app.repositories.alert_repository import AlertRepository
from app.repositories.gas_reading_repository import GasReadingRepository
from app.repositories.parking_area_repository import ParkingAreaRepository
from app.repositories.sensor_repository import SensorRepository
from app.schemas.gas_reading import GasReadingIngest
from app.services.risk_engine import RiskAssessment, risk_engine

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    reading: GasReading
    assessment: RiskAssessment
    alert_raised: bool


class IngestionError(Exception):
    """Raised for domain-level ingestion failures (e.g. unknown sensor)."""


class IngestionService:
    def __init__(self, db: Session):
        self.db = db
        self.sensors = SensorRepository(db)
        self.readings = GasReadingRepository(db)
        self.areas = ParkingAreaRepository(db)
        self.alerts = AlertRepository(db)

    def ingest(self, payload: GasReadingIngest) -> IngestionResult:
        sensor: Sensor | None = self.sensors.get(payload.sensor_id)
        if sensor is None:
            raise IngestionError(f"Unknown sensor_id: {payload.sensor_id}")

        area = self.areas.get(sensor.parking_area_id)
        if area is None:
            raise IngestionError(f"Sensor {sensor.id} references a parking area that no longer exists")

        fields = payload.model_dump(exclude={"sensor_id", "recorded_at"}, exclude_none=True)
        if payload.recorded_at is not None:
            fields["recorded_at"] = payload.recorded_at
        reading = self.readings.create(sensor_id=sensor.id, parking_area_id=area.id, **fields)

        self.sensors.mark_seen(sensor, at=reading.recorded_at)

        assessment = risk_engine.classify(reading)
        self.areas.update_risk_state(area, assessment.risk_level, assessment.risk_score)

        alert_raised = False
        if assessment.risk_level == RiskLevel.UNSAFE and assessment.dominant_gas is not None:
            dominant = next((f for f in assessment.factors if f.gas == assessment.dominant_gas), None)
            if dominant and not self.alerts.has_open_alert_for_gas(area.id, dominant.gas):
                alert = self.alerts.create(
                    parking_area_id=area.id,
                    title=f"Unsafe {dominant.gas.upper()} level at {area.name}",
                    message=(
                        f"{dominant.gas.upper()} reached {dominant.value:g} "
                        f"({dominant.percent_of_threshold:.0f}% of the unsafe threshold of "
                        f"{dominant.threshold:g}). Overall risk score is {assessment.risk_score:.0f}/100."
                    ),
                    severity=AlertSeverity.CRITICAL,
                    triggered_by_reading_id=reading.id,
                    gas_type=dominant.gas,
                    measured_value=dominant.value,
                    threshold_value=dominant.threshold,
                    channels=[
                        AlertChannel.DASHBOARD.value,
                        AlertChannel.EMAIL.value,
                        AlertChannel.SMS.value,
                        AlertChannel.PUSH.value,
                    ],
                )
                alert_raised = True

                try:
                    from app.tasks.notification_tasks import dispatch_alert_notifications

                    dispatch_alert_notifications.delay(str(alert.id))
                except Exception as exc:  # noqa: BLE001
                    # Notification delivery is best-effort: if the broker is
                    # unreachable, the alert itself must still be created and
                    # ingestion must still succeed. It'll just live as a
                    # dashboard-only alert until the next successful dispatch.
                    logger.warning("Could not enqueue notification dispatch for alert %s: %s", alert.id, exc)

        return IngestionResult(reading=reading, assessment=assessment, alert_raised=alert_raised)
