"""
SMS delivery via Twilio's REST API, called directly over HTTP rather than
through the Twilio SDK — keeps the dependency footprint to just `httpx`
(already required elsewhere) and makes the base URL swappable, which is
what makes this provider actually testable against a local mock server
instead of only against production credentials we don't have in every
environment.
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings
from app.services.notifications.base import NotificationResult

logger = logging.getLogger(__name__)


class TwilioSMSProvider:
    channel = "sms"

    def is_configured(self) -> bool:
        return bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_FROM_NUMBER)

    def send(self, *, to: str, subject: str, message: str) -> NotificationResult:
        if not self.is_configured():
            return NotificationResult(success=False, status="skipped", detail="Twilio credentials not configured")

        url = (
            f"{settings.TWILIO_API_BASE_URL}/2010-04-01/Accounts/"
            f"{settings.TWILIO_ACCOUNT_SID}/Messages.json"
        )
        # SMS has no subject line — fold it into the body if present.
        body = f"{subject}: {message}" if subject else message

        try:
            response = httpx.post(
                url,
                data={"From": settings.TWILIO_FROM_NUMBER, "To": to, "Body": body},
                auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
                timeout=10,
            )
            if response.status_code in (200, 201):
                return NotificationResult(success=True, status="sent")
            return NotificationResult(
                success=False, status="failed", detail=f"HTTP {response.status_code}: {response.text[:200]}"
            )
        except httpx.HTTPError as exc:
            logger.warning("SMS delivery to %s failed: %s", to, exc)
            return NotificationResult(success=False, status="failed", detail=str(exc))


sms_provider = TwilioSMSProvider()
