"""
Fans an Alert out to every configured channel it's flagged for, across
every recipient user, and returns one NotificationResult per (channel,
recipient) pair so the caller can persist a full audit trail.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.models.alert import Alert
from app.models.user import User
from app.services.notifications.base import NotificationProvider, NotificationResult
from app.services.notifications.email_provider import email_provider
from app.services.notifications.push_provider import push_provider
from app.services.notifications.sms_provider import sms_provider


@dataclass
class DeliveryAttempt:
    channel: str
    user: User | None
    recipient_target: str
    result: NotificationResult


class NotificationDispatcher:
    def __init__(self, providers: dict[str, NotificationProvider] | None = None):
        self.providers: dict[str, NotificationProvider] = providers or {
            "email": email_provider,
            "sms": sms_provider,
            "push": push_provider,
        }

    def _target_for(self, channel: str, user: User) -> str | None:
        if channel == "email":
            return user.email
        if channel == "sms":
            return user.phone_number
        if channel == "push":
            return user.push_token
        return None

    def dispatch(self, alert: Alert, recipients: list[User]) -> list[DeliveryAttempt]:
        subject = alert.title
        message = alert.message
        attempts: list[DeliveryAttempt] = []

        for channel in alert.channels:
            if channel == "dashboard":
                continue  # dashboard "delivery" is just the alert existing in the DB — nothing to send
            provider = self.providers.get(channel)
            if provider is None:
                continue

            for user in recipients:
                target = self._target_for(channel, user)
                if not target:
                    attempts.append(
                        DeliveryAttempt(
                            channel=channel, user=user, recipient_target="",
                            result=NotificationResult(success=False, status="skipped", detail=f"No {channel} target on file"),
                        )
                    )
                    continue

                result = provider.send(to=target, subject=subject, message=message)
                attempts.append(DeliveryAttempt(channel=channel, user=user, recipient_target=target, result=result))

        return attempts


dispatcher = NotificationDispatcher()
