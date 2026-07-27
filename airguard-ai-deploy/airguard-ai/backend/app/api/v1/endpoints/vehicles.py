import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import UserRole, VehicleStatus
from app.models.user import User
from app.repositories.vehicle_repository import VehicleRepository
from app.schemas.vehicle import VehicleEntryCreate, VehicleParkRequest, VehicleRead
from app.services.vehicle_service import VehicleTrackingError, VehicleTrackingService

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])

_GATE_ROLES = (UserRole.ADMIN, UserRole.SECURITY_GUARD, UserRole.SAFETY_OFFICER, UserRole.FACTORY_MANAGER)


@router.get("", response_model=list[VehicleRead])
def list_vehicles(
    parking_area_id: uuid.UUID | None = Query(default=None),
    status_filter: VehicleStatus | None = Query(default=None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list:
    return VehicleRepository(db).list(parking_area_id=parking_area_id, status=status_filter, skip=skip, limit=limit)


@router.post("/entry", response_model=VehicleRead, status_code=status.HTTP_201_CREATED)
def register_vehicle_entry(
    payload: VehicleEntryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_GATE_ROLES)),
):
    """Log a vehicle entering the site at the gate, before it's assigned a parking area."""
    service = VehicleTrackingService(db)
    try:
        return service.register_entry(
            plate_number=payload.plate_number, vehicle_type=payload.vehicle_type, driver_name=payload.driver_name
        )
    except VehicleTrackingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{vehicle_id}/park", response_model=VehicleRead)
def park_vehicle(
    vehicle_id: uuid.UUID,
    payload: VehicleParkRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_GATE_ROLES)),
):
    """Assign a vehicle to a parking area — increments that area's occupied_slots,
    and enforces capacity and closed-area rules."""
    service = VehicleTrackingService(db)
    try:
        return service.park(vehicle_id, payload.parking_area_id)
    except VehicleTrackingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{vehicle_id}/exit", response_model=VehicleRead)
def exit_vehicle(
    vehicle_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_GATE_ROLES)),
):
    """Log a vehicle leaving the site — decrements occupied_slots if it was parked."""
    service = VehicleTrackingService(db)
    try:
        return service.exit_site(vehicle_id)
    except VehicleTrackingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
