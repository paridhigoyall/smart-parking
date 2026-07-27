from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import RiskLevel
from app.models.prediction import Prediction


class PredictionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        parking_area_id: uuid.UUID,
        horizon_minutes: int,
        model_name: str,
        predicted_values: dict,
        gas_trends: dict,
        predicted_risk_level: RiskLevel,
        predicted_risk_score: float,
        dominant_gas: str | None,
        confidence: float,
        target_at: datetime,
    ) -> Prediction:
        pred = Prediction(
            parking_area_id=parking_area_id,
            horizon_minutes=horizon_minutes,
            model_name=model_name,
            predicted_values=predicted_values,
            gas_trends=gas_trends,
            predicted_risk_level=predicted_risk_level,
            predicted_risk_score=predicted_risk_score,
            dominant_gas=dominant_gas,
            confidence=confidence,
            target_at=target_at,
        )
        self.db.add(pred)
        self.db.commit()
        self.db.refresh(pred)
        return pred

    def list(
        self,
        *,
        parking_area_id: uuid.UUID | None = None,
        horizon_minutes: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Prediction]:
        stmt = select(Prediction)
        if parking_area_id is not None:
            stmt = stmt.where(Prediction.parking_area_id == parking_area_id)
        if horizon_minutes is not None:
            stmt = stmt.where(Prediction.horizon_minutes == horizon_minutes)
        stmt = stmt.order_by(Prediction.generated_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt))

    def get_latest_per_horizon(self, parking_area_id: uuid.UUID) -> list[Prediction]:
        """One most-recent prediction per horizon (5/15/30/60), newest generated_at wins."""
        latest: dict[int, Prediction] = {}
        stmt = (
            select(Prediction)
            .where(Prediction.parking_area_id == parking_area_id)
            .order_by(Prediction.generated_at.desc())
            .limit(200)
        )
        for pred in self.db.scalars(stmt):
            if pred.horizon_minutes not in latest:
                latest[pred.horizon_minutes] = pred
        return sorted(latest.values(), key=lambda p: p.horizon_minutes)
