import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.gas_reading_repository import GasReadingRepository
from app.schemas.gas_reading import GasReadingIngest, GasReadingRead
from app.schemas.risk import GasFactorRead, RiskAssessmentRead
from app.services.ingestion_service import IngestionError, IngestionService

router = APIRouter(prefix="/gas-readings", tags=["Gas Readings"])

# In production this endpoint would sit behind per-device API keys issued to
# sensor gateways rather than end-user JWTs. We reuse the JWT+RBAC scheme
# here for consistency with the rest of the platform; ADMIN / SAFETY_OFFICER
# / ENVIRONMENTAL_OFFICER accounts represent the sensor gateway service in
# the meantime.
_INGEST_ROLES = (UserRole.ADMIN, UserRole.SAFETY_OFFICER, UserRole.ENVIRONMENTAL_OFFICER)


@router.post("", response_model=RiskAssessmentRead, status_code=status.HTTP_201_CREATED)
def ingest_gas_reading(
    payload: GasReadingIngest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_INGEST_ROLES)),
):
    service = IngestionService(db)
    try:
        result = service.ingest(payload)
    except IngestionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    area = service.areas.get(result.reading.parking_area_id)
    return RiskAssessmentRead(
        parking_area_id=area.id,
        parking_area_code=area.code,
        risk_score=result.assessment.risk_score,
        risk_level=result.assessment.risk_level,
        exposure_label=result.assessment.exposure_label,
        confidence_score=result.assessment.confidence_score,
        air_quality_score=result.assessment.air_quality_score,
        dominant_gas=result.assessment.dominant_gas,
        data_completeness=result.assessment.data_completeness,
        reading_age_seconds=result.assessment.reading_age_seconds,
        assessed_at=result.assessment.assessed_at,
        factors=[
            GasFactorRead(
                gas=f.gas, value=f.value, threshold=f.threshold,
                percent_of_threshold=f.percent_of_threshold, weight=f.weight,
            )
            for f in result.assessment.factors
        ],
        based_on_reading_id=result.reading.id,
    )


@router.get("", response_model=list[GasReadingRead])
def list_gas_readings(
    parking_area_id: uuid.UUID | None = Query(default=None),
    sensor_id: uuid.UUID | None = Query(default=None),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list:
    return GasReadingRepository(db).list(
        parking_area_id=parking_area_id, sensor_id=sensor_id, start=start, end=end, skip=skip, limit=limit
    )


@router.get("/latest", response_model=GasReadingRead)
def get_latest_reading(
    parking_area_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    reading = GasReadingRepository(db).get_latest_for_area(parking_area_id)
    if not reading:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No readings yet for this parking area")
    return reading
