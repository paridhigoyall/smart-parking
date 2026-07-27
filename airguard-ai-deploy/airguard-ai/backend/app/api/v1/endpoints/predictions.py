import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.gas_reading_repository import GasReadingRepository
from app.repositories.prediction_repository import PredictionRepository
from app.schemas.prediction import (
    AreaForecastRead,
    GasForecastRead,
    PredictionRead,
    TrendChartRead,
    TrendPoint,
)
from app.services.forecasting_service import DEFAULT_HORIZONS, LOOKBACK_MINUTES, ForecastingError, ForecastingService

router = APIRouter(prefix="/predictions", tags=["Predictions"])

_GAS_UNITS: dict[str, str] = {
    "co": "ppm", "co2": "ppm", "no2": "ppm", "so2": "ppm", "nh3": "ppm", "h2s": "ppm",
    "methane": "ppm", "lpg": "ppm", "smoke": "ppm", "pm25": "µg/m³", "pm10": "µg/m³",
}


@router.post("/generate", response_model=list[AreaForecastRead], status_code=status.HTTP_201_CREATED)
def generate_forecasts(
    parking_area_id: uuid.UUID = Query(...),
    horizons: str = Query(default="5,15,30,60", description="Comma-separated minute horizons"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Run the forecasting engine for a parking area across the requested
    horizons (default 5/15/30/60 minutes), persist the results, and return
    them with the full per-gas breakdown.
    """
    try:
        horizon_tuple = tuple(int(h.strip()) for h in horizons.split(",") if h.strip())
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="horizons must be comma-separated integers")

    service = ForecastingService(db)
    try:
        forecasts = service.generate_forecasts(parking_area_id, horizons=horizon_tuple)
    except ForecastingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return [
        AreaForecastRead(
            parking_area_id=parking_area_id,
            horizon_minutes=f.horizon_minutes,
            target_at=f.target_at,
            predicted_risk_level=f.predicted_risk_level,
            predicted_risk_score=f.predicted_risk_score,
            dominant_gas=f.dominant_gas,
            confidence=f.confidence,
            gas_forecasts=[
                GasForecastRead(
                    gas=gf.gas, current_value=gf.current_value, predicted_value=gf.predicted_value,
                    trend=gf.trend, slope_per_minute=gf.slope_per_minute, r_squared=gf.r_squared,
                    confidence=gf.confidence, data_points=gf.data_points,
                )
                for gf in f.gas_forecasts
            ],
        )
        for f in forecasts
    ]


@router.get("/latest", response_model=list[PredictionRead])
def get_latest_predictions(
    parking_area_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list:
    """Most recent persisted prediction for each horizon (5/15/30/60)."""
    return PredictionRepository(db).get_latest_per_horizon(parking_area_id)


@router.get("", response_model=list[PredictionRead])
def list_predictions(
    parking_area_id: uuid.UUID | None = Query(default=None),
    horizon_minutes: int | None = Query(default=None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list:
    return PredictionRepository(db).list(
        parking_area_id=parking_area_id, horizon_minutes=horizon_minutes, skip=skip, limit=limit
    )


@router.get("/trend", response_model=TrendChartRead)
def get_trend_chart(
    parking_area_id: uuid.UUID = Query(...),
    gas: str = Query(..., description="One of: co, co2, no2, so2, nh3, h2s, methane, lpg, smoke, pm25, pm10"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Chart-ready series for a single gas at a single parking area: recent
    actual readings followed by forecasted points at each horizon, so the
    frontend can render one continuous trend line that changes style at
    the "now" boundary.
    """
    if gas not in _GAS_UNITS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown gas '{gas}'")

    now = datetime.now(timezone.utc)
    readings = GasReadingRepository(db).list(
        parking_area_id=parking_area_id,
        start=now - timedelta(minutes=LOOKBACK_MINUTES),
        end=now,
        limit=500,
    )
    points: list[TrendPoint] = []
    for r in reversed(readings):  # oldest -> newest
        value = getattr(r, gas, None)
        if value is not None:
            points.append(TrendPoint(timestamp=r.recorded_at, value=value, kind="actual"))

    if not points:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No recent '{gas}' readings for this parking area",
        )

    service = ForecastingService(db)
    try:
        forecasts = service.generate_forecasts(parking_area_id, horizons=DEFAULT_HORIZONS, persist=False)
    except ForecastingError:
        forecasts = []

    for f in forecasts:
        for gf in f.gas_forecasts:
            if gf.gas == gas:
                points.append(TrendPoint(timestamp=f.target_at, value=gf.predicted_value, kind="forecast"))

    return TrendChartRead(parking_area_id=parking_area_id, gas=gas, unit=_GAS_UNITS[gas], points=points)
