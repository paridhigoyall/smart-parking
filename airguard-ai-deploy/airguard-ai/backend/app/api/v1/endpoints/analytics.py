import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.analytics_rollup_repository import AnalyticsRollupRepository
from app.schemas.analytics import AnalyticsRollupGenerateResponse, AnalyticsRollupRead
from app.services.analytics_service import AnalyticsError, AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])

_MANAGE_ROLES = (UserRole.ADMIN, UserRole.SAFETY_OFFICER, UserRole.ENVIRONMENTAL_OFFICER, UserRole.FACTORY_MANAGER)


@router.post("/rollups/generate", response_model=AnalyticsRollupGenerateResponse, status_code=status.HTTP_201_CREATED)
def generate_rollup(
    parking_area_id: uuid.UUID = Query(...),
    period_type: str = Query(..., description="daily | weekly | monthly | yearly"),
    period_start: date = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    """
    Compute (or recompute) a rollup for one period from raw gas readings and
    alerts — average/max gas levels, hours spent in each risk band, alert
    count, an environmental score, and a rough carbon-footprint estimate.
    """
    service = AnalyticsService(db)
    try:
        rollup, reading_count = service.generate_rollup(parking_area_id, period_type, period_start)
    except AnalyticsError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return AnalyticsRollupGenerateResponse(rollup=rollup, reading_count=reading_count)


@router.get("/rollups", response_model=list[AnalyticsRollupRead])
def list_rollups(
    parking_area_id: uuid.UUID | None = Query(default=None),
    period_type: str | None = Query(default=None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list:
    return AnalyticsRollupRepository(db).list(parking_area_id=parking_area_id, period_type=period_type, limit=limit)
