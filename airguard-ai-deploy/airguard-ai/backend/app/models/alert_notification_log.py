import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, UUIDPrimaryKeyMixin


class AlertNotificationLog(Base, UUIDPrimaryKeyMixin):
    """
    An audit record of one delivery attempt for one alert, to one
    recipient, over one channel. Exists so "did the on-call safety officer
    actually get paged" is an answerable, queryable question rather than a
    best-effort assumption.
    """
    __tablename__ = "alert_notification_logs"

    alert_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("alerts.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    channel: Mapped[str] = mapped_column(String(20), nullable=False)  # email | sms | push | dashboard
    recipient_target: Mapped[str] = mapped_column(String(255), nullable=False)  # email addr / phone / device token
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # sent | failed | skipped
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    alert: Mapped["Alert"] = relationship()
    user: Mapped["User"] = relationship()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AlertNotificationLog alert={self.alert_id} channel={self.channel} status={self.status}>"
