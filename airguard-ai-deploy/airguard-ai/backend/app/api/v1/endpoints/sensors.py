import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import SensorStatus, UserRole
from app.models.user import User
from app.repositories.gas_reading_repository import GasReadingRepository
from app.repositories.maintenance_log_repository import MaintenanceLogRepository
from app.repositories.parking_area_repository import ParkingAreaRepository
from app.repositories.sensor_repository import SensorRepository
from app.schemas.maintenance import MaintenanceAssessmentRead, MaintenanceLogCreate, MaintenanceLogRead
from app.schemas.sensor import SensorCreate, SensorRead, SensorUpdate
from app.services.maintenance_engine import maintenance_engine

router = APIRouter(prefix="/sensors", tags=["Sensors"])

_MANAGE_ROLES = (UserRole.ADMIN, UserRole.SAFETY_OFFICER, UserRole.ENVIRONMENTAL_OFFICER)


@router.get("", response_model=list[SensorRead])
def list_sensors(
    parking_area_id: uuid.UUID | None = Query(default=None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list:
    return SensorRepository(db).list(parking_area_id=parking_area_id, skip=skip, limit=limit)


@router.post("", response_model=SensorRead, status_code=status.HTTP_201_CREATED)
def register_sensor(
    payload: SensorCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    sensors = SensorRepository(db)
    if sensors.get_by_serial(payload.serial_number):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Serial number already registered")
    if not ParkingAreaRepository(db).get(payload.parking_area_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="parking_area_id does not exist")
    return sensors.create(payload)


@router.get("/{sensor_id}", response_model=SensorRead)
def get_sensor(
    sensor_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    sensor = SensorRepository(db).get(sensor_id)
    if not sensor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor not found")
    return sensor


@router.patch("/{sensor_id}", response_model=SensorRead)
def update_sensor(
    sensor_id: uuid.UUID,
    payload: SensorUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    repo = SensorRepository(db)
    sensor = repo.get(sensor_id)
    if not sensor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor not found")
    return repo.update(sensor, payload)


@router.get("/{sensor_id}/health", response_model=MaintenanceAssessmentRead)
def get_sensor_health(
    sensor_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Live predictive-maintenance assessment: health score, failure
    probability, whether calibration is due, and the specific issues
    driving that assessment (stale data, low battery, overdue calibration,
    flatlined readings). Also persists the score/probability onto the
    sensor record so they show up in the plain sensor list too.
    """
    sensor = SensorRepository(db).get(sensor_id)
    if not sensor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor not found")

    recent = GasReadingRepository(db).list(sensor_id=sensor_id, limit=20)  # newest-first
    assessment = maintenance_engine.assess(sensor, recent)

    suggested_status = SensorStatus(assessment.suggested_status) if assessment.suggested_status else None
    SensorRepository(db).update_health(
        sensor,
        health_score=assessment.health_score,
        failure_probability=assessment.failure_probability,
        status=suggested_status,
    )

    return MaintenanceAssessmentRead(
        sensor_id=sensor_id,
        health_score=assessment.health_score,
        failure_probability=assessment.failure_probability,
        calibration_needed=assessment.calibration_needed,
        issues=assessment.issues,
        suggested_status=assessment.suggested_status,
        assessed_at=datetime.now(timezone.utc),
    )


@router.post("/{sensor_id}/maintenance-logs", response_model=MaintenanceLogRead, status_code=status.HTTP_201_CREATED)
def log_maintenance_event(
    sensor_id: uuid.UUID,
    payload: MaintenanceLogCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    """
    Record a maintenance event. `calibration` events reset the sensor's
    last-calibrated timestamp; `battery_swap` events reset battery to 100%
    — both real side effects, not just a log entry, so the next health
    assessment reflects the work that was actually done.
    """
    repo = SensorRepository(db)
    sensor = repo.get(sensor_id)
    if not sensor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor not found")

    if payload.event_type == "calibration":
        repo.record_calibration(sensor)
    elif payload.event_type == "battery_swap":
        repo.reset_battery(sensor)

    return MaintenanceLogRepository(db).create(
        sensor_id=sensor_id, event_type=payload.event_type, notes=payload.notes, performed_by=payload.performed_by
    )


@router.get("/{sensor_id}/maintenance-logs", response_model=list[MaintenanceLogRead])
def list_maintenance_logs(
    sensor_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list:
    if not SensorRepository(db).get(sensor_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor not found")
    return MaintenanceLogRepository(db).list_for_sensor(sensor_id)


@router.delete("/{sensor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sensor(
    sensor_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> None:
    repo = SensorRepository(db)
    sensor = repo.get(sensor_id)
    if not sensor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor not found")
    repo.delete(sensor)
