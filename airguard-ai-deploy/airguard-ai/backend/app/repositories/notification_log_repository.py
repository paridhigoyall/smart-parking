from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert_notification_log import AlertNotificationLog


class NotificationLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        alert_id: uuid.UUID,
        user_id: uuid.UUID | None,
        channel: str,
        recipient_target: str,
        status: str,
        error_message: str | None = None,
    ) -> AlertNotificationLog:
        log = AlertNotificationLog(
            alert_id=alert_id,
            user_id=user_id,
            channel=channel,
            recipient_target=recipient_target,
            status=status,
            error_message=error_message,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def list_for_alert(self, alert_id: uuid.UUID) -> list[AlertNotificationLog]:
        stmt = (
            select(AlertNotificationLog)
            .where(AlertNotificationLog.alert_id == alert_id)
            .order_by(AlertNotificationLog.created_at.desc())
        )
        return list(self.db.scalars(stmt))
