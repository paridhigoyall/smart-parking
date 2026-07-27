"""
Gas Risk Engine.

Turns a raw multi-gas sensor reading into a full risk assessment:
  - Risk Score       (0-100, higher = more dangerous)
  - Risk Level       (SAFE / MODERATE / UNSAFE)
  - Exposure Score   (human-readable category)
  - Confidence Score (0-100, how much we trust this assessment)
  - Air Quality Score(0-100, higher = cleaner air)
  - Per-gas breakdown (which gases are driving the score, and by how much)

This is a transparent, rule-based/statistical engine on purpose: every number
it produces can be traced back to a specific gas value and threshold, which
is exactly what the Explainable AI module (Module 3) needs to generate
human-readable justifications. It is designed to be swappable later for a
learned model (e.g. a gradient-boosted classifier) behind the same
`RiskAssessment` interface without touching any caller.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.core.config import settings
from app.models.enums import RiskLevel
from app.models.gas_reading import GasReading

# ----------------------------------------------------------------------
# Gas importance weights.
#
# These are *relative toxicity/hazard weights* used when combining multiple
# simultaneously elevated gases into a single score — they do not replace
# the individual regulatory-style thresholds in Settings, they just decide
# how much each gas's threshold-ratio counts toward the blended average.
# H2S and CO are weighted highest because they are acutely lethal at
# relatively low concentrations and are the most common causes of
# industrial gas fatalities.
# ----------------------------------------------------------------------
GAS_WEIGHTS: dict[str, float] = {
    "co": 1.3,
    "h2s": 1.4,
    "so2": 1.1,
    "no2": 1.1,
    "nh3": 0.9,
    "methane": 1.2,
    "lpg": 1.2,
    "smoke": 1.3,
    "co2": 0.6,
    "pm25": 1.0,
    "pm10": 0.8,
}

# Gases that most directly represent breathable air quality (as opposed to
# explosion/asphyxiation risk like methane/LPG) — used for the separate
# Air Quality Score.
AIR_QUALITY_GASES: tuple[str, ...] = ("pm25", "pm10", "smoke", "co", "no2", "so2")

# A ratio (value / unsafe_threshold) at or above this is treated as an
# outright breach, regardless of what the blended average says.
UNSAFE_RATIO_CUTOFF = 1.0
# A ratio at or above this on any single gas is enough to push the overall
# level to at least MODERATE, even if the blended average is still low.
MODERATE_RATIO_CUTOFF = 0.5

# Ratios are clamped here before being averaged, so one extreme outlier
# reading (e.g. a sensor spike) doesn't single-handedly dominate the blend.
MAX_CLAMPED_RATIO = 2.0


@dataclass
class GasFactor:
    """The contribution of a single gas measurement to the overall assessment."""
    gas: str
    value: float
    threshold: float
    ratio: float          # value / threshold, clamped to MAX_CLAMPED_RATIO
    weight: float
    percent_of_threshold: float  # unclamped, for human-readable explanations


@dataclass
class RiskAssessment:
    risk_score: float               # 0-100
    risk_level: RiskLevel
    exposure_label: str             # "Very Low" | "Low" | "Moderate" | "High" | "Very High"
    confidence_score: float         # 0-100
    air_quality_score: float        # 0-100, higher = cleaner
    factors: list[GasFactor] = field(default_factory=list)
    dominant_gas: str | None = None  # the single gas driving the risk level, if any
    assessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data_completeness: float = 0.0  # fraction (0-1) of tracked gas params present in the reading
    reading_age_seconds: float | None = None


_THRESHOLD_MAP: dict[str, float] = {
    "co": settings.THRESHOLD_CO_UNSAFE,
    "co2": settings.THRESHOLD_CO2_UNSAFE,
    "no2": settings.THRESHOLD_NO2_UNSAFE,
    "so2": settings.THRESHOLD_SO2_UNSAFE,
    "nh3": settings.THRESHOLD_NH3_UNSAFE,
    "h2s": settings.THRESHOLD_H2S_UNSAFE,
    "methane": settings.THRESHOLD_METHANE_UNSAFE,
    "lpg": settings.THRESHOLD_LPG_UNSAFE,
    "smoke": settings.THRESHOLD_SMOKE_UNSAFE,
    "pm25": settings.THRESHOLD_PM25_UNSAFE,
    "pm10": settings.THRESHOLD_PM10_UNSAFE,
}

_TRACKED_GASES = tuple(_THRESHOLD_MAP.keys())


class GasRiskEngine:
    """Stateless classifier — safe to use as a singleton / module-level instance."""

    def __init__(self, thresholds: dict[str, float] | None = None, weights: dict[str, float] | None = None):
        self.thresholds = thresholds or _THRESHOLD_MAP
        self.weights = weights or GAS_WEIGHTS

    # ------------------------------------------------------------------
    def classify(self, reading: GasReading, *, now: datetime | None = None) -> RiskAssessment:
        now = now or datetime.now(timezone.utc)

        factors: list[GasFactor] = []
        for gas in _TRACKED_GASES:
            value = getattr(reading, gas, None)
            if value is None:
                continue
            threshold = self.thresholds[gas]
            weight = self.weights.get(gas, 1.0)
            raw_ratio = value / threshold if threshold else 0.0
            factors.append(
                GasFactor(
                    gas=gas,
                    value=value,
                    threshold=threshold,
                    ratio=min(raw_ratio, MAX_CLAMPED_RATIO),
                    weight=weight,
                    percent_of_threshold=raw_ratio * 100.0,
                )
            )

        data_completeness = len(factors) / len(_TRACKED_GASES)

        if not factors:
            # No gas data at all — cannot assess. Report maximum uncertainty
            # rather than pretending the area is safe.
            return RiskAssessment(
                risk_score=0.0,
                risk_level=RiskLevel.MODERATE,
                exposure_label="Unknown",
                confidence_score=0.0,
                air_quality_score=50.0,
                factors=[],
                dominant_gas=None,
                assessed_at=now,
                data_completeness=0.0,
                reading_age_seconds=self._age_seconds(reading, now),
            )

        weighted_sum = sum(f.ratio * f.weight for f in factors)
        total_weight = sum(f.weight for f in factors)
        blended_ratio = weighted_sum / total_weight if total_weight else 0.0
        risk_score = min(100.0, blended_ratio * 100.0)

        worst_factor = max(factors, key=lambda f: f.ratio)
        level = self._level_from_score(risk_score)
        if worst_factor.ratio >= UNSAFE_RATIO_CUTOFF:
            level = RiskLevel.UNSAFE
        elif worst_factor.ratio >= MODERATE_RATIO_CUTOFF and level == RiskLevel.SAFE:
            level = RiskLevel.MODERATE

        dominant_gas = worst_factor.gas if worst_factor.ratio >= MODERATE_RATIO_CUTOFF else None

        confidence = self._confidence(data_completeness, reading, now)
        air_quality_score = self._air_quality_score(factors)

        return RiskAssessment(
            risk_score=round(risk_score, 2),
            risk_level=level,
            exposure_label=self._exposure_label(risk_score),
            confidence_score=round(confidence, 2),
            air_quality_score=round(air_quality_score, 2),
            factors=sorted(factors, key=lambda f: f.ratio, reverse=True),
            dominant_gas=dominant_gas,
            assessed_at=now,
            data_completeness=round(data_completeness, 2),
            reading_age_seconds=self._age_seconds(reading, now),
        )

    # ------------------------------------------------------------------
    @staticmethod
    def _level_from_score(score: float) -> RiskLevel:
        if score < 40:
            return RiskLevel.SAFE
        if score < 70:
            return RiskLevel.MODERATE
        return RiskLevel.UNSAFE

    @staticmethod
    def _exposure_label(score: float) -> str:
        if score < 20:
            return "Very Low"
        if score < 40:
            return "Low"
        if score < 60:
            return "Moderate"
        if score < 80:
            return "High"
        return "Very High"

    def _air_quality_score(self, factors: list[GasFactor]) -> float:
        relevant = [f for f in factors if f.gas in AIR_QUALITY_GASES]
        if not relevant:
            return 50.0
        weighted_sum = sum(f.ratio * f.weight for f in relevant)
        total_weight = sum(f.weight for f in relevant)
        pollution_fraction = min(1.0, weighted_sum / total_weight) if total_weight else 0.0
        return max(0.0, 100.0 * (1.0 - pollution_fraction))

    def _confidence(self, data_completeness: float, reading: GasReading, now: datetime) -> float:
        # Base confidence from how many of the tracked gas parameters this
        # reading actually populated.
        base = data_completeness * 100.0

        # Penalize stale readings — a 20-minute-old reading shouldn't be
        # reported with the same confidence as one from 10 seconds ago.
        age = self._age_seconds(reading, now)
        if age is None:
            freshness_factor = 1.0
        elif age <= 60:
            freshness_factor = 1.0
        elif age <= 300:
            freshness_factor = 0.9
        elif age <= 900:
            freshness_factor = 0.7
        else:
            freshness_factor = 0.5

        return max(0.0, min(100.0, base * freshness_factor))

    @staticmethod
    def _age_seconds(reading: GasReading, now: datetime) -> float | None:
        if reading.recorded_at is None:
            return None
        recorded = reading.recorded_at
        if recorded.tzinfo is None:
            recorded = recorded.replace(tzinfo=timezone.utc)
        return max(0.0, (now - recorded).total_seconds())


risk_engine = GasRiskEngine()
