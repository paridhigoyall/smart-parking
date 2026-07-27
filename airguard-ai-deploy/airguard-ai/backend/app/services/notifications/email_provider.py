"""
Email delivery via plain SMTP (stdlib smtplib) — no third-party email API
dependency required. Works against any SMTP server: a real provider
(SendGrid/SES/Postmark's SMTP relay, your company's mail server) or a local
test server during development.
"""
from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText

from app.core.config import settings
from app.services.notifications.base import NotificationResult

logger = logging.getLogger(__name__)


class SMTPEmailProvider:
    channel = "email"

    def is_configured(self) -> bool:
        return bool(settings.SMTP_HOST)

    def send(self, *, to: str, subject: str, message: str) -> NotificationResult:
        if not self.is_configured():
            return NotificationResult(success=False, status="skipped", detail="SMTP_HOST not configured")

        msg = MIMEText(message, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = to

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as client:
                if settings.SMTP_USE_TLS:
                    client.starttls()
                if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                    client.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                client.sendmail(settings.SMTP_FROM_EMAIL, [to], msg.as_string())
            return NotificationResult(success=True, status="sent")
        except (smtplib.SMTPException, OSError) as exc:
            logger.warning("Email delivery to %s failed: %s", to, exc)
            return NotificationResult(success=False, status="failed", detail=str(exc))


email_provider = SMTPEmailProvider()
