import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.ml import ClassificationComparison, GasValuesInput, MLModelResult, ModelInfo, RuleEngineResult
from app.services.ml_risk_classifier import ml_risk_classifier
from app.services.risk_engine import risk_engine

router = APIRouter(prefix="/ml", tags=["Machine Learning"])

_TRAINING_REPORT_PATH = Path(__file__).resolve().parents[4] / "ml_models" / "training_report.json"


@router.post("/classify", response_model=ClassificationComparison)
def classify_gas_values(
    payload: GasValuesInput,
    _: User = Depends(get_current_user),
):
    """
    Classify a hypothetical set of gas readings with BOTH the rule-based
    risk engine and the trained ML classifier side by side — useful for
    demonstrating (or stress-testing) where the two approaches agree and
    where they diverge.
    """
    gas_values = payload.model_dump(exclude_none=True)
    if not gas_values:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide at least one gas value")

    synthetic_reading = SimpleNamespace(recorded_at=datetime.now(timezone.utc), **gas_values)
    assessment = risk_engine.classify(synthetic_reading)
    rule_result = RuleEngineResult(
        risk_level=assessment.risk_level.value,
        risk_score=assessment.risk_score,
        exposure_label=assessment.exposure_label,
        dominant_gas=assessment.dominant_gas,
    )

    ml_result = None
    agree = None
    prediction = ml_risk_classifier.predict(gas_values)
    if prediction is not None:
        ml_result = MLModelResult(
            predicted_label=prediction.predicted_label,
            probabilities=prediction.probabilities,
            model_confidence=prediction.model_confidence,
        )
        agree = prediction.predicted_label == assessment.risk_level.value

    return ClassificationComparison(rule_engine=rule_result, ml_model=ml_result, agree=agree)


@router.get("/model-info", response_model=ModelInfo)
def get_model_info(_: User = Depends(get_current_user)):
    """
    Real training metrics from the last time the ML classifier was
    trained (app/ml/train_risk_classifier.py) — accuracy, per-class
    precision/recall, confusion matrix, and feature importances. Not
    fabricated for display; this is what actually got written out after
    the last training run.
    """
    if not _TRAINING_REPORT_PATH.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No training report found — run `python -m app.ml.train_risk_classifier` first",
        )
    with open(_TRAINING_REPORT_PATH) as f:
        return ModelInfo(**json.load(f))
