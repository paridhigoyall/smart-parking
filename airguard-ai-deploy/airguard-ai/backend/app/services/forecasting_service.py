"""
Orchestration layer for Module 4: pulls each parking area's recent gas
reading history, runs it through the ForecastingEngine for every requested
horizon, and persists the results.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.prediction import Prediction
from app.repositories.gas_reading_repository import GasReadingRepository
from app.repositories.parking_area_repository import ParkingAreaRepository
from app.repositories.prediction_repository import PredictionRepository
from app.services.forecasting_engine import AreaForecast, forecasting_engine

DEFAULT_HORIZONS = (5, 15, 30, 60)
# How far back to look for historical readings when fitting the trend.
# Wide enough to capture a real trend, narrow enough that very old data
# doesn't drag down a fast-moving current situation.
LOOKBACK_MINUTES = 60
MODEL_NAME = "linear_trend_baseline_v1"


class ForecastingError(Exception):
    pass


class ForecastingService:
    def __init__(self, db: Session):
        self.db = db
        self.areas = ParkingAreaRepository(db)
        self.readings = GasReadingRepository(db)
        self.predictions = PredictionRepository(db)

    def generate_forecasts(
        self,
        parking_area_id: uuid.UUID,
        *,
        horizons: tuple[int, ...] = DEFAULT_HORIZONS,
        persist: bool = True,
    ) -> list[AreaForecast]:
        area = self.areas.get(parking_area_id)
        if area is None:
            raise ForecastingError(f"Parking area {parking_area_id} not found")

        now = datetime.now(timezone.utc)
        history = self.readings.list(
            parking_area_id=parking_area_id,
            start=now - timedelta(minutes=LOOKBACK_MINUTES),
            end=now,
            limit=500,
        )
        if not history:
            raise ForecastingError(f"No recent gas readings for {area.name}; nothing to forecast from")

        history = list(reversed(history))  # repository returns newest-first; engine wants oldest-first

        forecasts: list[AreaForecast] = []
        for horizon in horizons:
            forecast = forecasting_engine.forecast_area(history, horizon, now=now)
            forecasts.append(forecast)
            if persist and forecast.gas_forecasts:
                self._persist(area.id, forecast)

        return forecasts

    def _persist(self, area_id: uuid.UUID, forecast: AreaForecast) -> Prediction:
        predicted_values = {gf.gas: gf.predicted_value for gf in forecast.gas_forecasts}
        gas_trends = {gf.gas: gf.trend for gf in forecast.gas_forecasts}
        return self.predictions.create(
            parking_area_id=area_id,
            horizon_minutes=forecast.horizon_minutes,
            model_name=MODEL_NAME,
            predicted_values=predicted_values,
            gas_trends=gas_trends,
            predicted_risk_level=forecast.predicted_risk_level,
            predicted_risk_score=forecast.predicted_risk_score,
            dominant_gas=forecast.dominant_gas,
            confidence=forecast.confidence,
            target_at=forecast.target_at,
        )
