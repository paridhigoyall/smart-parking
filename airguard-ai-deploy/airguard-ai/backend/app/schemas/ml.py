from pydantic import BaseModel, ConfigDict, Field


class GasValuesInput(BaseModel):
    """Raw gas concentrations for direct rule-engine vs. ML-model comparison —
    no sensor/parking-area required, useful for testing/demoing the models
    directly against hypothetical readings."""
    co: float | None = Field(default=None, ge=0)
    co2: float | None = Field(default=None, ge=0)
    no2: float | None = Field(default=None, ge=0)
    so2: float | None = Field(default=None, ge=0)
    nh3: float | None = Field(default=None, ge=0)
    h2s: float | None = Field(default=None, ge=0)
    methane: float | None = Field(default=None, ge=0)
    lpg: float | None = Field(default=None, ge=0)
    smoke: float | None = Field(default=None, ge=0)
    pm25: float | None = Field(default=None, ge=0)
    pm10: float | None = Field(default=None, ge=0)


class RuleEngineResult(BaseModel):
    risk_level: str
    risk_score: float
    exposure_label: str
    dominant_gas: str | None


class MLModelResult(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    predicted_label: str
    probabilities: dict[str, float]
    model_confidence: float


class ClassificationComparison(BaseModel):
    rule_engine: RuleEngineResult
    ml_model: MLModelResult | None
    agree: bool | None  # None if the ML model isn't available


class ModelInfo(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    trained_at: str
    n_samples: int
    label_noise_rate: float
    test_accuracy: float
    classification_report: dict
    confusion_matrix: list[list[int]]
    confusion_matrix_labels: list[str]
    feature_importances: dict[str, float]
    model_params: dict
