"""
Background task: given an alert ID, load the alert and its recipients,
fan the notification out across every channel the alert requested, and
persist a delivery-attempt log for each (channel, recipient) pair.

Celery tasks don't get FastAPI's request-scoped DB session, so this opens
and closes its own — same pattern as the `_ensure_first_superuser` startup
routine in app.main.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.alert import Alert
from app.models.enums import UserRole
from app.models.user import User
from app.core.config import settings
from app.repositories.notification_log_repository import NotificationLogRepository
from app.services.notifications.dispatcher import dispatcher
from app.worker import celery_app

logger = logging.getLogger(__name__)


def _recipients(db) -> list[User]:
    roles = [UserRole(r) for r in settings.ALERT_RECIPIENT_ROLES]
    stmt = select(User).where(User.role.in_(roles), User.is_active.is_(True))
    return list(db.scalars(stmt))


@celery_app.task(name="dispatch_alert_notifications", bind=True, max_retries=3, default_retry_delay=30)
def dispatch_alert_notifications(self, alert_id: str) -> dict:
    db = SessionLocal()
    try:
        alert = db.get(Alert, uuid.UUID(alert_id))
        if alert is None:
            logger.warning("dispatch_alert_notifications: alert %s no longer exists", alert_id)
            return {"alert_id": alert_id, "attempts": 0}

        recipients = _recipients(db)
        attempts = dispatcher.dispatch(alert, recipients)

        log_repo = NotificationLogRepository(db)
        for attempt in attempts:
            log_repo.create(
                alert_id=alert.id,
                user_id=attempt.user.id if attempt.user else None,
                channel=attempt.channel,
                recipient_target=attempt.recipient_target,
                status=attempt.result.status,
                error_message=attempt.result.detail,
            )

        sent = sum(1 for a in attempts if a.result.success)
        logger.info("Alert %s: %d/%d notifications sent", alert_id, sent, len(attempts))
        return {"alert_id": alert_id, "attempts": len(attempts), "sent": sent}
    finally:
        db.close()
