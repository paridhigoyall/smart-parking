from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.enums import AlertChannel, AlertSeverity, AlertStatus


class AlertRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        parking_area_id: uuid.UUID,
        title: str,
        message: str,
        severity: AlertSeverity,
        triggered_by_reading_id: uuid.UUID | None = None,
        gas_type: str | None = None,
        measured_value: float | None = None,
        threshold_value: float | None = None,
        channels: list[str] | None = None,
    ) -> Alert:
        alert = Alert(
            parking_area_id=parking_area_id,
            title=title,
            message=message,
            severity=severity,
            status=AlertStatus.OPEN,
            channels=channels or [AlertChannel.DASHBOARD.value],
            triggered_by_reading_id=triggered_by_reading_id,
            gas_type=gas_type,
            measured_value=measured_value,
            threshold_value=threshold_value,
        )
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def get(self, alert_id: uuid.UUID) -> Alert | None:
        return self.db.get(Alert, alert_id)

    def acknowledge(self, alert: Alert, user_id: uuid.UUID) -> Alert:
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_by_id = user_id
        alert.acknowledged_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def resolve(self, alert: Alert) -> Alert:
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(alert)
        return alert

    def has_open_alert_for_gas(self, parking_area_id: uuid.UUID, gas_type: str) -> bool:
        stmt = select(Alert).where(
            Alert.parking_area_id == parking_area_id,
            Alert.gas_type == gas_type,
            Alert.status == AlertStatus.OPEN,
        )
        return self.db.scalar(stmt) is not None

    def list(
        self, *, parking_area_id: uuid.UUID | None = None, status: AlertStatus | None = None,
        skip: int = 0, limit: int = 100,
    ) -> list[Alert]:
        stmt = select(Alert)
        if parking_area_id is not None:
            stmt = stmt.where(Alert.parking_area_id == parking_area_id)
        if status is not None:
            stmt = stmt.where(Alert.status == status)
        stmt = stmt.order_by(Alert.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt))
