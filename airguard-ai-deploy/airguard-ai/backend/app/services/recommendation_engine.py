"""
Recommendation Engine.

Two related jobs live here:

1. Parking recommendation — rank every open parking area by its current
   risk assessment (from the Gas Risk Engine) and recommend the safest one,
   with a human-readable explanation of *why* it beat the alternatives.

2. AI decision support — beyond "park here", suggest the appropriate safety
   action for each area given its current condition (ventilate, delay
   entry, close the area, activate exhaust, evacuate).

Like the risk engine, this is deliberately rule-based and fully traceable:
every explanation sentence is built directly from the same GasFactor numbers
the risk engine already computed, so nothing here is a black box.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import RecommendationAction, RiskLevel
from app.models.parking_area import ParkingArea
from app.services.risk_engine import GasFactor, RiskAssessment

GAS_DISPLAY_NAMES: dict[str, str] = {
    "co": "Carbon Monoxide",
    "co2": "Carbon Dioxide",
    "no2": "Nitrogen Dioxide",
    "so2": "Sulfur Dioxide",
    "nh3": "Ammonia",
    "h2s": "Hydrogen Sulfide",
    "methane": "Methane",
    "lpg": "LPG",
    "smoke": "Smoke",
    "pm25": "PM2.5 particulate matter",
    "pm10": "PM10 particulate matter",
}

# Gases associated with fire/explosion risk — a breach here calls for
# evacuation rather than just ventilation.
_FLAMMABLE_GASES = {"methane", "lpg", "smoke"}
# Gases that are primarily toxic/asphyxiant rather than flammable.
_TOXIC_GASES = {"co", "h2s", "so2", "no2", "nh3"}


@dataclass
class RankedArea:
    area: ParkingArea
    assessment: RiskAssessment
    rank: int = 0


@dataclass
class ActionSuggestion:
    action: RecommendationAction
    reason: str


@dataclass
class ParkingRecommendation:
    ranked_areas: list[RankedArea]
    top_choice: RankedArea | None
    explanation: str


class RecommendationEngine:
    # ------------------------------------------------------------------
    # 1. Parking recommendation across areas
    # ------------------------------------------------------------------
    def recommend(self, ranked: list[RankedArea]) -> ParkingRecommendation:
        """
        `ranked` should contain one RankedArea per candidate parking area
        (already excluding closed areas / areas with no data, which the
        caller decides). This method sorts them by risk_score ascending,
        assigns rank numbers, and builds the explanation for the winner.
        """
        ordered = sorted(ranked, key=lambda r: r.assessment.risk_score)
        for i, r in enumerate(ordered, start=1):
            r.rank = i

        if not ordered:
            return ParkingRecommendation(ranked_areas=[], top_choice=None, explanation="No parking areas with current sensor data are available.")

        top = ordered[0]
        runner_up = ordered[1] if len(ordered) > 1 else None
        explanation = self._explain(top, runner_up)
        return ParkingRecommendation(ranked_areas=ordered, top_choice=top, explanation=explanation)

    def _explain(self, top: RankedArea, runner_up: RankedArea | None) -> str:
        if runner_up is None:
            return (
                f"{top.area.name} is the only parking area currently reporting sensor data. "
                f"Its overall risk score is {top.assessment.risk_score:.0f}/100 "
                f"({top.assessment.risk_level.value}), with an air quality score of "
                f"{top.assessment.air_quality_score:.0f}/100."
            )

        # Find the gas with the largest absolute value gap between the two
        # areas, among gases both areas actually reported — that's the most
        # concrete, checkable justification for the recommendation.
        top_factors = {f.gas: f for f in top.assessment.factors}
        runner_factors = {f.gas: f for f in runner_up.assessment.factors}
        shared_gases = set(top_factors) & set(runner_factors)

        best_gas = None
        best_relative_drop = -1.0
        for gas in shared_gases:
            runner_val = runner_factors[gas].value
            top_val = top_factors[gas].value
            if runner_val <= 0:
                continue
            relative_drop = (runner_val - top_val) / runner_val
            if relative_drop > best_relative_drop:
                best_relative_drop = relative_drop
                best_gas = gas

        score_gap = runner_up.assessment.risk_score - top.assessment.risk_score

        if best_gas and best_relative_drop > 0.01:
            gas_label = GAS_DISPLAY_NAMES.get(best_gas, best_gas.upper())
            pct = best_relative_drop * 100
            sentence = (
                f"{top.area.name} is recommended because {gas_label} levels are "
                f"{pct:.0f}% lower than {runner_up.area.name} "
                f"({top_factors[best_gas].value:g} vs {runner_factors[best_gas].value:g})"
            )
        else:
            sentence = (
                f"{top.area.name} is recommended over {runner_up.area.name} "
                f"based on its lower overall risk profile"
            )

        sentence += (
            f", giving it an overall risk score of {top.assessment.risk_score:.0f}/100 versus "
            f"{runner_up.assessment.risk_score:.0f}/100 for {runner_up.area.name} "
            f"(a {score_gap:.0f}-point gap), and an air quality score of "
            f"{top.assessment.air_quality_score:.0f}/100."
        )
        return sentence

    # ------------------------------------------------------------------
    # 2. AI decision support — safety actions beyond "park here"
    # ------------------------------------------------------------------
    def suggest_actions(self, assessment: RiskAssessment, area_name: str) -> list[ActionSuggestion]:
        if assessment.risk_level == RiskLevel.SAFE:
            return [ActionSuggestion(RecommendationAction.PARK_HERE, "Conditions are within safe limits.")]

        if assessment.risk_level == RiskLevel.MODERATE:
            suggestions = [
                ActionSuggestion(
                    RecommendationAction.OPEN_VENTILATION,
                    f"Conditions at {area_name} are trending toward unsafe "
                    f"({assessment.risk_score:.0f}/100); increasing ventilation now can prevent escalation.",
                )
            ]
            if assessment.dominant_gas:
                gas_label = GAS_DISPLAY_NAMES.get(assessment.dominant_gas, assessment.dominant_gas.upper())
                suggestions.append(
                    ActionSuggestion(
                        RecommendationAction.DELAY_ENTRY,
                        f"{gas_label} is elevated; delaying non-essential vehicle entry reduces exposure "
                        f"while levels stabilize.",
                    )
                )
            return suggestions

        # UNSAFE
        dominant = assessment.dominant_gas
        suggestions: list[ActionSuggestion] = []

        if dominant in _FLAMMABLE_GASES:
            gas_label = GAS_DISPLAY_NAMES.get(dominant, dominant.upper())
            suggestions.append(
                ActionSuggestion(
                    RecommendationAction.EVACUATE,
                    f"{gas_label} has reached an unsafe concentration at {area_name}, indicating fire/explosion "
                    f"risk; evacuate personnel and vehicles immediately.",
                )
            )
            suggestions.append(
                ActionSuggestion(
                    RecommendationAction.CLOSE_PARKING,
                    f"Close {area_name} to new vehicle entry until levels return to safe range.",
                )
            )
        elif dominant in _TOXIC_GASES:
            gas_label = GAS_DISPLAY_NAMES.get(dominant, dominant.upper())
            suggestions.append(
                ActionSuggestion(
                    RecommendationAction.ACTIVATE_EXHAUST,
                    f"{gas_label} has exceeded safe exposure limits at {area_name}; activate exhaust fans "
                    f"to accelerate dispersion.",
                )
            )
            suggestions.append(
                ActionSuggestion(
                    RecommendationAction.CLOSE_PARKING,
                    f"Close {area_name} to new entry until {gas_label} drops back below the safety threshold.",
                )
            )
        else:
            suggestions.append(
                ActionSuggestion(
                    RecommendationAction.CLOSE_PARKING,
                    f"Overall risk score at {area_name} is {assessment.risk_score:.0f}/100 (unsafe); "
                    f"close the area to new entry pending a follow-up reading.",
                )
            )

        return suggestions


recommendation_engine = RecommendationEngine()
