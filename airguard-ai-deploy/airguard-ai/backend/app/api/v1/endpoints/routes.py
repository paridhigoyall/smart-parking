import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.route import RoutePoint, RouteRead
from app.services.route_service import RouteError, RouteService

router = APIRouter(prefix="/routes", tags=["Routes"])


@router.get("/to/{parking_area_id}", response_model=RouteRead)
def get_safest_route(
    parking_area_id: uuid.UUID,
    gate_x: float | None = Query(default=None),
    gate_y: float | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Safest route from the plant gate to a parking area, routed around any
    other parking area currently UNSAFE or closed. Coordinates are on the
    same 0-1000 plant-map canvas used by the interactive map — pass
    gate_x/gate_y to route from a different entry point than the default.
    """
    service = RouteService(db)
    gate = (gate_x, gate_y) if gate_x is not None and gate_y is not None else None
    try:
        result = service.route_to(parking_area_id, gate=gate)
    except RouteError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return RouteRead(
        destination_area_id=parking_area_id,
        waypoints=[RoutePoint(x=x, y=y) for x, y in result.waypoints],
        status=result.status,
        avoided_hazards=result.avoided_hazards,
        total_distance=round(result.total_distance, 1),
        notes=result.notes,
    )
