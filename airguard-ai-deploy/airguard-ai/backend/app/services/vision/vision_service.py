"""
Orchestration for Module 7f: run an uploaded camera frame through object
detection + the smoke/fire heuristic, cross-reference the detected vehicle
count against vehicles this platform actually knows are parked there (from
Module 7c's vehicle tracking) to flag likely unauthorized parking, and —
above a confidence threshold — raise a real alert through the exact same
Alert + notification pipeline a gas-threshold breach uses. A camera
detecting smoke and a sensor detecting CO should behave identically from
the alert system's point of view.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import AlertChannel, AlertSeverity, VehicleStatus
from app.repositories.alert_repository import AlertRepository
from app.repositories.camera_frame_analysis_repository import CameraFrameAnalysisRepository
from app.repositories.parking_area_repository import ParkingAreaRepository
from app.repositories.vehicle_repository import VehicleRepository
from app.services.vision.object_detector import object_detector
from app.services.vision.smoke_fire_detector import smoke_fire_detector

logger = logging.getLogger(__name__)


class VisionError(Exception):
    pass


class VisionService:
    def __init__(self, db: Session):
        self.db = db
        self.areas = ParkingAreaRepository(db)
        self.vehicles = VehicleRepository(db)
        self.alerts = AlertRepository(db)
        self.analyses = CameraFrameAnalysisRepository(db)

    def analyze_frame(self, parking_area_id: uuid.UUID, image_bytes: bytes):
        area = self.areas.get(parking_area_id)
        if area is None:
            raise VisionError("Parking area not found")

        detection = object_detector.detect(image_bytes, confidence_threshold=settings.VISION_DETECTION_CONFIDENCE)
        smoke_fire = smoke_fire_detector.analyze(image_bytes)

        registered_parked = self.vehicles.list(parking_area_id=parking_area_id, status=VehicleStatus.PARKED, limit=1000)
        registered_count = len(registered_parked)
        # A camera seeing meaningfully more vehicles than the system has
        # recorded as parked there suggests unregistered/unauthorized
        # vehicles — a real, if simple, cross-check between two independent
        # signals (vision vs. gate-tracked entries) rather than trusting
        # either alone.
        unauthorized_suspected = detection.vehicle_count > registered_count + 1

        alert_id = None
        if smoke_fire.fire_detected and smoke_fire.fire_confidence >= settings.VISION_ALERT_CONFIDENCE_THRESHOLD:
            alert_id = self._raise_alert(area, "fire", smoke_fire.fire_confidence).id
        elif smoke_fire.smoke_detected and smoke_fire.smoke_confidence >= settings.VISION_ALERT_CONFIDENCE_THRESHOLD:
            alert_id = self._raise_alert(area, "smoke", smoke_fire.smoke_confidence).id

        record = self.analyses.create(
            parking_area_id=parking_area_id,
            vehicle_count=detection.vehicle_count,
            person_count=detection.person_count,
            detected_objects=[
                {"class_name": o.class_name, "confidence": round(o.confidence, 3), "bbox": list(o.bbox)}
                for o in detection.objects
            ],
            registered_parked_count=registered_count,
            unauthorized_parking_suspected=unauthorized_suspected,
            smoke_detected=smoke_fire.smoke_detected,
            smoke_confidence=smoke_fire.smoke_confidence,
            fire_detected=smoke_fire.fire_detected,
            fire_confidence=smoke_fire.fire_confidence,
            alert_id=alert_id,
        )
        return record

    def _raise_alert(self, area, hazard_type: str, confidence: float):
        alert = self.alerts.create(
            parking_area_id=area.id,
            title=f"Camera detected possible {hazard_type} at {area.name}",
            message=(
                f"CCTV analysis flagged {hazard_type} with {confidence * 100:.0f}% confidence. "
                f"This is a classical color-heuristic detector, not a validated fire-detection "
                f"system — verify with gas sensor readings and, if available, direct observation."
            ),
            severity=AlertSeverity.CRITICAL,
            channels=[AlertChannel.DASHBOARD.value, AlertChannel.EMAIL.value, AlertChannel.SMS.value, AlertChannel.PUSH.value],
        )

        try:
            from app.tasks.notification_tasks import dispatch_alert_notifications

            dispatch_alert_notifications.delay(str(alert.id))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not enqueue notification dispatch for vision alert %s: %s", alert.id, exc)

        return alert
