import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.gas_reading_repository import GasReadingRepository
from app.repositories.parking_area_repository import ParkingAreaRepository
from app.schemas.parking_area import ParkingAreaCreate, ParkingAreaRead, ParkingAreaUpdate
from app.schemas.risk import GasFactorRead, RiskAssessmentRead
from app.services.risk_engine import risk_engine

router = APIRouter(prefix="/parking-areas", tags=["Parking Areas"])

_MANAGE_ROLES = (UserRole.ADMIN, UserRole.SAFETY_OFFICER, UserRole.FACTORY_MANAGER)


@router.get("", response_model=list[ParkingAreaRead])
def list_parking_areas(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list:
    return ParkingAreaRepository(db).list(skip=skip, limit=limit)


@router.post("", response_model=ParkingAreaRead, status_code=status.HTTP_201_CREATED)
def create_parking_area(
    payload: ParkingAreaCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    repo = ParkingAreaRepository(db)
    if repo.get_by_code(payload.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Code '{payload.code}' already in use")
    return repo.create(payload)


@router.get("/{area_id}", response_model=ParkingAreaRead)
def get_parking_area(
    area_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    area = ParkingAreaRepository(db).get(area_id)
    if not area:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parking area not found")
    return area


@router.get("/{area_id}/risk", response_model=RiskAssessmentRead)
def get_parking_area_risk(
    area_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Live risk assessment for a parking area, recomputed from its most recent
    gas reading. This is intentionally re-derived on every call (rather than
    just reading the cached current_risk_score on the area row) so the
    per-gas breakdown used for Explainable AI is always available and
    always fresh.
    """
    area = ParkingAreaRepository(db).get(area_id)
    if not area:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parking area not found")

    reading = GasReadingRepository(db).get_latest_for_area(area_id)
    if not reading:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No gas readings yet for this parking area")

    assessment = risk_engine.classify(reading)
    return RiskAssessmentRead(
        parking_area_id=area.id,
        parking_area_code=area.code,
        risk_score=assessment.risk_score,
        risk_level=assessment.risk_level,
        exposure_label=assessment.exposure_label,
        confidence_score=assessment.confidence_score,
        air_quality_score=assessment.air_quality_score,
        dominant_gas=assessment.dominant_gas,
        data_completeness=assessment.data_completeness,
        reading_age_seconds=assessment.reading_age_seconds,
        assessed_at=assessment.assessed_at,
        factors=[
            GasFactorRead(
                gas=f.gas, value=f.value, threshold=f.threshold,
                percent_of_threshold=f.percent_of_threshold, weight=f.weight,
            )
            for f in assessment.factors
        ],
        based_on_reading_id=reading.id,
    )


@router.patch("/{area_id}", response_model=ParkingAreaRead)
def update_parking_area(
    area_id: uuid.UUID,
    payload: ParkingAreaUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    repo = ParkingAreaRepository(db)
    area = repo.get(area_id)
    if not area:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parking area not found")
    return repo.update(area, payload)


@router.delete("/{area_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_parking_area(
    area_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> None:
    repo = ParkingAreaRepository(db)
    area = repo.get(area_id)
    if not area:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parking area not found")
    repo.delete(area)
