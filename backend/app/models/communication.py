import enum
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    String,
    Integer,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    Enum,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class NotificationCategory(str, enum.Enum):
    ACADEMIC_CHANGE = "ACADEMIC_CHANGE"
    OPERATIONAL_ALERT = "OPERATIONAL_ALERT"
    SECURITY_EVENT = "SECURITY_EVENT"
    SCHEDULED_REMINDER = "SCHEDULED_REMINDER"


class NotificationPriority(str, enum.Enum):
    URGENT = "URGENT"    # Bypasses quiet hours
    NORMAL = "NORMAL"    # Subject to quiet hours
    LOW = "LOW"          # Subject to quiet hours


class Notification(Base, TimestampMixin):
    """
    In-app user notification with category, priority, and idempotency guarantees.
    """
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recipient_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[NotificationCategory] = mapped_column(
        Enum(NotificationCategory), nullable=False, index=True
    )
    priority: Mapped[NotificationPriority] = mapped_column(
        Enum(NotificationPriority), default=NotificationPriority.NORMAL, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_for: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    recipient = relationship("User", foreign_keys=[recipient_user_id])

    __table_args__ = (
        UniqueConstraint("recipient_user_id", "idempotency_key", name="uq_notification_recipient_idempotency"),
    )


class NotificationPreference(Base, TimestampMixin):
    """
    User notification delivery preferences including quiet hours configuration.
    """
    __tablename__ = "notification_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    institution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Quiet hours settings
    quiet_hours_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    quiet_hours_start: Mapped[str] = mapped_column(String(5), default="22:00", nullable=False)  # HH:MM
    quiet_hours_end: Mapped[str] = mapped_column(String(5), default="07:00", nullable=False)    # HH:MM

    # Category subscription toggles
    notify_academic_changes: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_operational_alerts: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_security_events: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # Security always on
    notify_scheduled_reminders: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Channel toggles
    email_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    calendar_sync_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        UniqueConstraint("user_id", "institution_id", name="uq_notification_preference_user_inst"),
    )


class CalendarCredential(Base, TimestampMixin):
    """
    Encrypted Google Calendar integration credentials and sync telemetry.
    Credentials stored strictly encrypted with configured key.
    """
    __tablename__ = "calendar_credentials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    institution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    encrypted_access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    encrypted_refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_expiry: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    calendar_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Dedicated app-created secondary calendar

    sync_status: Mapped[str] = mapped_column(String(50), default="DISCONNECTED", nullable=False, index=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sync_event_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    synced_events_map: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        UniqueConstraint("user_id", "institution_id", name="uq_calendar_credential_user_inst"),
    )
