"""
Inference wrapper for the trained RandomForest risk classifier
(app/ml/train_risk_classifier.py). Loads the model lazily so the rest of
the API isn't slowed down when this isn't being used, and degrades
cleanly (is_available() == False) if the model hasn't been trained yet
rather than crashing the app.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.services.risk_engine import _TRACKED_GASES

MODEL_PATH = Path(__file__).resolve().parents[2] / "ml_models" / "risk_classifier.joblib"


@dataclass
class MLPrediction:
    predicted_label: str
    probabilities: dict[str, float]
    model_confidence: float  # probability of the predicted class


@lru_cache(maxsize=1)
def _load_model():
    import joblib

    if not MODEL_PATH.exists():
        return None
    return joblib.load(MODEL_PATH)


class MLRiskClassifier:
    def is_available(self) -> bool:
        return _load_model() is not None

    def predict(self, gas_values: dict[str, float | None]) -> MLPrediction | None:
        bundle = _load_model()
        if bundle is None:
            return None

        model = bundle["model"]
        feature_order = bundle["feature_order"]
        labels = bundle["labels"]

        # Missing gases are imputed as 0 (same convention used when
        # training on partially-populated synthetic readings) rather than
        # dropping the sample — a real sensor node rarely reports all 11
        # parameters at once.
        features = [[gas_values.get(g) or 0.0 for g in feature_order]]

        predicted = model.predict(features)[0]
        proba = model.predict_proba(features)[0]
        prob_map = {label: round(float(p), 4) for label, p in zip(model.classes_, proba)}

        return MLPrediction(
            predicted_label=predicted,
            probabilities=prob_map,
            model_confidence=round(float(max(proba)), 4),
        )


ml_risk_classifier = MLRiskClassifier()
