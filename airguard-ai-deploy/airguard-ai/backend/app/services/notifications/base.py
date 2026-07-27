"""
Base interface every notification provider (email/SMS/push) implements.

Kept deliberately small: one method, one result type. Providers are free to
be as real (SMTP, a REST API) or as inert (a no-op that reports itself as
unconfigured) as their environment allows — callers only ever see
NotificationResult and don't need to know which.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class NotificationResult:
    success: bool
    status: str  # "sent" | "failed" | "skipped"
    detail: str | None = None


class NotificationProvider(Protocol):
    channel: str

    def is_configured(self) -> bool:
        """Whether this provider has the credentials/config it needs to actually send."""
        ...

    def send(self, *, to: str, subject: str, message: str) -> NotificationResult:
        ...
