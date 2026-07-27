"""
Forecasting Engine.

Predicts gas concentrations at a parking area N minutes into the future.

Design: for each gas, fit a simple linear trend (least-squares) over recent
history and extrapolate to the target time. This is intentionally a
transparent statistical baseline — every prediction can be explained as
"X was rising/falling by Y per minute over the last Z readings" — rather
than a black box. It's built so a learned model (LSTM / Transformer) can
be swapped in later behind the same `ForecastingEngine.forecast(...)`
interface without any caller needing to change: same input (a list of
historical GasReadings), same output (`AreaForecast`).

Confidence combines three things:
  - goodness of fit (R²) of the linear trend
  - how many historical points support that trend
  - how far the target horizon extrapolates beyond the observed window
    (predicting 5 minutes past 30 minutes of history is safer than
    predicting 60 minutes past 10 minutes of history)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import numpy as np

from app.models.gas_reading import GasReading
from app.services.risk_engine import _TRACKED_GASES, risk_engine

MIN_CONFIDENCE = 10.0
MAX_CONFIDENCE = 95.0  # a statistical baseline should never claim certainty
FLAT_FORECAST_CONFIDENCE_CAP = 45.0  # when we can't establish a trend at all


@dataclass
class GasForecast:
    gas: str
    current_value: float
    predicted_value: float
    trend: str              # "rising" | "falling" | "stable" | "insufficient_data"
    slope_per_minute: float
    r_squared: float
    confidence: float
    data_points: int


@dataclass
class AreaForecast:
    horizon_minutes: int
    target_at: datetime
    gas_forecasts: list[GasForecast] = field(default_factory=list)
    predicted_risk_level: "RiskLevel | None" = None  # populated by the orchestration service
    predicted_risk_score: float = 0.0
    dominant_gas: str | None = None
    confidence: float = 0.0


class ForecastingEngine:
    def forecast_gas(
        self, gas: str, history: list[tuple[datetime, float]], target_time: datetime
    ) -> GasForecast:
        """
        `history` is a list of (timestamp, value) pairs for a single gas,
        assumed already sorted oldest -> newest, with at least 1 point.
        """
        current_value = history[-1][1]

        if len(history) < 2:
            return GasForecast(
                gas=gas,
                current_value=current_value,
                predicted_value=current_value,
                trend="insufficient_data",
                slope_per_minute=0.0,
                r_squared=0.0,
                confidence=min(FLAT_FORECAST_CONFIDENCE_CAP, 30.0),
                data_points=len(history),
            )

        t0 = history[0][0]
        xs = np.array([(t - t0).total_seconds() for t, _ in history], dtype=float)
        ys = np.array([v for _, v in history], dtype=float)

        # Guard against a degenerate all-same-timestamp case.
        if np.ptp(xs) == 0:
            return GasForecast(
                gas=gas, current_value=current_value, predicted_value=current_value,
                trend="insufficient_data", slope_per_minute=0.0, r_squared=0.0,
                confidence=FLAT_FORECAST_CONFIDENCE_CAP, data_points=len(history),
            )

        slope, intercept = np.polyfit(xs, ys, 1)
        y_pred = slope * xs + intercept
        ss_res = float(np.sum((ys - y_pred) ** 2))
        ss_tot = float(np.sum((ys - ys.mean()) ** 2))
        r_squared = 1.0 if ss_tot == 0 else max(0.0, 1.0 - ss_res / ss_tot)

        target_x = (target_time - t0).total_seconds()
        predicted_value = max(0.0, float(slope * target_x + intercept))

        slope_per_minute = slope * 60.0
        # A slope smaller than ~2% of the current value per minute reads as
        # "stable" rather than a fake-precise rising/falling label.
        noise_floor = max(abs(current_value) * 0.02, 1e-6)
        if abs(slope_per_minute) < noise_floor:
            trend = "stable"
        else:
            trend = "rising" if slope_per_minute > 0 else "falling"

        observed_span = xs[-1] - xs[0]
        extrapolation_distance = max(0.0, target_x - xs[-1])
        extrapolation_ratio = extrapolation_distance / observed_span if observed_span > 0 else 1.0
        extrapolation_factor = max(0.3, 1.0 - min(1.0, extrapolation_ratio) * 0.7)

        data_sufficiency_factor = min(1.0, len(history) / 6.0)  # full confidence at >=6 points

        base_confidence = MIN_CONFIDENCE + (MAX_CONFIDENCE - MIN_CONFIDENCE) * r_squared
        confidence = base_confidence * extrapolation_factor * (0.5 + 0.5 * data_sufficiency_factor)
        confidence = max(MIN_CONFIDENCE, min(MAX_CONFIDENCE, confidence))

        return GasForecast(
            gas=gas,
            current_value=current_value,
            predicted_value=round(predicted_value, 3),
            trend=trend,
            slope_per_minute=round(slope_per_minute, 4),
            r_squared=round(r_squared, 3),
            confidence=round(confidence, 2),
            data_points=len(history),
        )

    def forecast_area(
        self,
        readings: list[GasReading],
        horizon_minutes: int,
        *,
        now: datetime | None = None,
    ) -> AreaForecast:
        """
        `readings` should be sorted oldest -> newest, all belonging to one
        parking area, spanning whatever lookback window the caller chose.
        """
        now = now or datetime.now(timezone.utc)
        target_at = now + timedelta(minutes=horizon_minutes)

        gas_forecasts: list[GasForecast] = []
        for gas in _TRACKED_GASES:
            history = [
                (r.recorded_at, getattr(r, gas))
                for r in readings
                if getattr(r, gas, None) is not None
            ]
            if not history:
                continue
            gas_forecasts.append(self.forecast_gas(gas, history, target_at))

        area_forecast = AreaForecast(horizon_minutes=horizon_minutes, target_at=target_at, gas_forecasts=gas_forecasts)

        if not gas_forecasts:
            area_forecast.confidence = 0.0
            return area_forecast

        # Build a synthetic "future reading" so the same risk engine used
        # for live classification also classifies the forecast — one
        # consistent definition of Safe/Moderate/Unsafe everywhere.
        synthetic = SimpleNamespace(recorded_at=target_at)
        for gf in gas_forecasts:
            setattr(synthetic, gf.gas, gf.predicted_value)

        assessment = risk_engine.classify(synthetic, now=target_at)
        area_forecast.predicted_risk_level = assessment.risk_level
        area_forecast.predicted_risk_score = assessment.risk_score
        area_forecast.dominant_gas = assessment.dominant_gas

        # Overall forecast confidence: weighted average of per-gas
        # confidence (same toxicity weights the risk engine uses), further
        # scaled down as the horizon grows — a 5-minute forecast is
        # inherently more trustworthy than a 60-minute one even with
        # identical historical data.
        from app.services.risk_engine import GAS_WEIGHTS
        weighted_sum = sum(gf.confidence * GAS_WEIGHTS.get(gf.gas, 1.0) for gf in gas_forecasts)
        total_weight = sum(GAS_WEIGHTS.get(gf.gas, 1.0) for gf in gas_forecasts)
        blended_confidence = weighted_sum / total_weight if total_weight else 0.0

        horizon_penalty = {5: 1.0, 15: 0.92, 30: 0.82, 60: 0.68}.get(horizon_minutes, 0.75)
        area_forecast.confidence = round(max(MIN_CONFIDENCE, blended_confidence * horizon_penalty), 2)

        return area_forecast


forecasting_engine = ForecastingEngine()
