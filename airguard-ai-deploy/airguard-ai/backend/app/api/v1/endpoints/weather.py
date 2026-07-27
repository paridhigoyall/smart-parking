from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.weather_repository import WeatherRepository
from app.schemas.weather import WeatherRecordCreate, WeatherRecordRead
from app.services.weather_provider import weather_provider

router = APIRouter(prefix="/weather", tags=["Weather"])

_MANAGE_ROLES = (UserRole.ADMIN, UserRole.SAFETY_OFFICER, UserRole.ENVIRONMENTAL_OFFICER)


@router.post("/ingest", response_model=WeatherRecordRead, status_code=status.HTTP_201_CREATED)
def ingest_manual_weather(
    payload: WeatherRecordCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    """Record a reading from an on-site weather station."""
    return WeatherRepository(db).create(source="site_station", **payload.model_dump())


@router.post("/fetch", response_model=WeatherRecordRead, status_code=status.HTTP_201_CREATED)
def fetch_external_weather(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    """Pull current conditions from the configured external weather API and store them."""
    if not weather_provider.is_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Weather provider not configured (set WEATHER_API_KEY, WEATHER_SITE_LAT, WEATHER_SITE_LON)",
        )
    data = weather_provider.fetch_current()
    if data is None:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Weather provider request failed")

    return WeatherRepository(db).create(
        source="external_api",
        temperature=data.temperature,
        humidity=data.humidity,
        wind_speed=data.wind_speed,
        wind_direction=data.wind_direction,
        rain_mm=data.rain_mm,
        pressure_hpa=data.pressure_hpa,
        forecast_summary=data.forecast_summary,
    )


@router.get("/latest", response_model=WeatherRecordRead)
def get_latest_weather(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    record = WeatherRepository(db).get_latest()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No weather records yet")
    return record


@router.get("", response_model=list[WeatherRecordRead])
def list_weather(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list:
    return WeatherRepository(db).list(limit=limit)
