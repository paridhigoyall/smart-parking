import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import AlertSeverity, AlertStatus


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    parking_area_id: uuid.UUID
    title: str
    message: str
    severity: AlertSeverity
    status: AlertStatus
    channels: list[str]
    gas_type: str | None
    measured_value: float | None
    threshold_value: float | None
    created_at: datetime


class AlertNotificationLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alert_id: uuid.UUID
    user_id: uuid.UUID | None
    channel: str
    recipient_target: str
    status: str
    error_message: str | None
    created_at: datetime
