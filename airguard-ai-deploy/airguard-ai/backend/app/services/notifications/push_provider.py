"""
Push delivery via Firebase Cloud Messaging's HTTP v1 API.

This expects a pre-obtained OAuth2 bearer token for a service account with
the "Firebase Cloud Messaging API" role (FCM_ACCESS_TOKEN). FCM v1 tokens
expire hourly, so a real production deployment should refresh this on a
schedule (e.g. via `google-auth`'s service-account credential flow, run as
a small periodic task) rather than hardcode one — that refresh job is a
natural, self-contained follow-up rather than something to fake here.
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings
from app.services.notifications.base import NotificationResult

logger = logging.getLogger(__name__)


class FCMPushProvider:
    channel = "push"

    def is_configured(self) -> bool:
        return bool(settings.FCM_ACCESS_TOKEN and settings.FCM_PROJECT_ID)

    def send(self, *, to: str, subject: str, message: str) -> NotificationResult:
        if not self.is_configured():
            return NotificationResult(success=False, status="skipped", detail="FCM credentials not configured")
        if not to:
            return NotificationResult(success=False, status="skipped", detail="Recipient has no registered device token")

        url = f"{settings.FCM_API_BASE_URL}/v1/projects/{settings.FCM_PROJECT_ID}/messages:send"
        payload = {"message": {"token": to, "notification": {"title": subject, "body": message}}}

        try:
            response = httpx.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {settings.FCM_ACCESS_TOKEN}"},
                timeout=10,
            )
            if response.status_code == 200:
                return NotificationResult(success=True, status="sent")
            return NotificationResult(
                success=False, status="failed", detail=f"HTTP {response.status_code}: {response.text[:200]}"
            )
        except httpx.HTTPError as exc:
            logger.warning("Push delivery to %s failed: %s", to, exc)
            return NotificationResult(success=False, status="failed", detail=str(exc))


push_provider = FCMPushProvider()
