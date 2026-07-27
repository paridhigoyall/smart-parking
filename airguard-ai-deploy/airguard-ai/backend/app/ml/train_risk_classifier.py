"""
Trains a supplementary ML risk classifier alongside the rule-based risk
engine — not a replacement for it.

Why both exist: the rule-based engine (app/services/risk_engine.py) is
deliberately transparent — every score traces back to a specific gas
value and threshold, which matters for a safety system where someone
needs to be able to ask "why did it say unsafe" and get a real answer.
This script adds a trained classifier on top as a second, independent
opinion: RandomForest can pick up non-linear interactions between
simultaneously-elevated gases that a linear weighted blend might
under-weight at the margins, and in production the two disagreeing would
itself be a useful signal ("the rule engine and the model disagree on
this reading — worth a second look").

Training data is synthetic (no real sensor deployment exists yet), but
generated to look like real sensor data, not a trivial lookup:
  - Ground-truth labels come from the SAME thresholds risk_engine.py uses
    (the closest thing to expert-labeled ground truth this project has),
    not invented independently.
  - Gaussian sensor noise is added to every feature.
  - ~7% label noise is injected (random reassignment to an adjacent risk
    band) to simulate real inter-rater/measurement disagreement — this is
    also why the model does NOT hit ~100% accuracy below; a model that
    perfectly reproduces its own noisy labels would indicate overfitting,
    not real generalization.

Run: python -m app.ml.train_risk_classifier
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # allow `python -m app.ml.train_risk_classifier`

from app.services.risk_engine import GAS_WEIGHTS, _TRACKED_GASES, _THRESHOLD_MAP, risk_engine  # noqa: E402

MODEL_DIR = Path(__file__).resolve().parents[2] / "ml_models"
N_SAMPLES = 12000
LABEL_NOISE_RATE = 0.07
RANDOM_STATE = 42

RISK_LABELS = ["safe", "moderate", "unsafe"]


def _generate_sample(rng: np.random.Generator) -> dict[str, float]:
    """One synthetic multi-gas reading, biased toward a randomly chosen
    target severity band but with enough spread and noise that the bands
    overlap — real sensor data doesn't come in clean, separable clusters."""
    band = rng.choice(["safe", "moderate", "unsafe"], p=[0.45, 0.30, 0.25])
    values: dict[str, float] = {}
    for gas in _TRACKED_GASES:
        threshold = _THRESHOLD_MAP[gas]
        if band == "safe":
            base_ratio = rng.uniform(0.0, 0.45)
        elif band == "moderate":
            base_ratio = rng.uniform(0.35, 0.95)
        else:
            base_ratio = rng.uniform(0.85, 1.9)

        # Sensor noise, and each gas independently has a chance to be
        # "quiet" (near zero) even in a scenario dominated by other
        # gases — real multi-gas events rarely light up every channel.
        if rng.random() < 0.3:
            base_ratio *= rng.uniform(0.05, 0.4)

        noisy_ratio = max(0.0, base_ratio + rng.normal(0, 0.06))
        values[gas] = round(noisy_ratio * threshold, 3)
    return values


def _ground_truth_label(values: dict[str, float]) -> str:
    reading = SimpleNamespace(recorded_at=datetime.now(timezone.utc), **values)
    assessment = risk_engine.classify(reading)
    return assessment.risk_level.value


def generate_dataset(n_samples: int, rng: np.random.Generator):
    rows = []
    labels = []
    for _ in range(n_samples):
        values = _generate_sample(rng)
        label = _ground_truth_label(values)
        rows.append([values[g] for g in _TRACKED_GASES])
        labels.append(label)

    X = np.array(rows)
    y = np.array(labels)

    # Inject label noise: reassign a random subset to a different band.
    noise_mask = rng.random(len(y)) < LABEL_NOISE_RATE
    for idx in np.where(noise_mask)[0]:
        choices = [l for l in RISK_LABELS if l != y[idx]]
        y[idx] = rng.choice(choices)

    return X, y


def main():
    rng = np.random.default_rng(RANDOM_STATE)
    print(f"Generating {N_SAMPLES} synthetic labeled readings...")
    X, y = generate_dataset(N_SAMPLES, rng)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )

    print(f"Train: {len(X_train)}  Test: {len(X_test)}")
    print("Training RandomForestClassifier...")
    model = RandomForestClassifier(
        n_estimators=200, max_depth=12, min_samples_leaf=5, random_state=RANDOM_STATE, n_jobs=-1
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, labels=RISK_LABELS, output_dict=True)
    cm = confusion_matrix(y_test, y_pred, labels=RISK_LABELS)

    print(f"\nTest accuracy: {accuracy:.4f}")
    print(classification_report(y_test, y_pred, labels=RISK_LABELS))
    print("Confusion matrix (rows=true, cols=predicted), order = safe, moderate, unsafe:")
    print(cm)

    importances = dict(zip(_TRACKED_GASES, model.feature_importances_.tolist()))
    importances_sorted = dict(sorted(importances.items(), key=lambda kv: kv[1], reverse=True))
    print("\nFeature importances (should roughly track the rule engine's GAS_WEIGHTS):")
    for gas, imp in importances_sorted.items():
        print(f"  {gas:10s} importance={imp:.4f}  rule_engine_weight={GAS_WEIGHTS.get(gas, 1.0)}")

    MODEL_DIR.mkdir(exist_ok=True)
    model_path = MODEL_DIR / "risk_classifier.joblib"
    joblib.dump({"model": model, "feature_order": list(_TRACKED_GASES), "labels": RISK_LABELS}, model_path)
    print(f"\nSaved model to {model_path}")

    report_path = MODEL_DIR / "training_report.json"
    report_data = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_samples": N_SAMPLES,
        "label_noise_rate": LABEL_NOISE_RATE,
        "test_accuracy": accuracy,
        "classification_report": report,
        "confusion_matrix": cm.tolist(),
        "confusion_matrix_labels": RISK_LABELS,
        "feature_importances": importances_sorted,
        "model_params": {"n_estimators": 200, "max_depth": 12, "min_samples_leaf": 5},
    }
    with open(report_path, "w") as f:
        json.dump(report_data, f, indent=2)
    print(f"Saved training report to {report_path}")


if __name__ == "__main__":
    main()
