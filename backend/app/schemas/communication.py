import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    institution_id: str
    recipient_user_id: str
    category: str
    priority: str
    title: str
    message: str
    data: Dict[str, Any] = {}
    is_read: bool
    read_at: Optional[datetime.datetime] = None
    scheduled_for: Optional[datetime.datetime] = None
    delivered_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int


class NotificationPreferencesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    quiet_hours_enabled: bool
    quiet_hours_start: str
    quiet_hours_end: str
    notify_academic_changes: bool
    notify_operational_alerts: bool
    notify_security_events: bool
    notify_scheduled_reminders: bool
    email_notifications_enabled: bool
    calendar_sync_enabled: bool


class NotificationPreferencesUpdate(BaseModel):
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    notify_academic_changes: Optional[bool] = None
    notify_operational_alerts: Optional[bool] = None
    notify_security_events: Optional[bool] = None
    notify_scheduled_reminders: Optional[bool] = None
    email_notifications_enabled: Optional[bool] = None
    calendar_sync_enabled: Optional[bool] = None


class OutboxEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    institution_id: str
    publication_id: Optional[str] = None
    event_type: str
    recipient_role: str
    payload: Dict[str, Any] = {}
    status: str
    retry_count: int
    max_retries: int
    last_error: Optional[str] = None
    next_retry_at: Optional[datetime.datetime] = None
    processed_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime


class CalendarStatusResponse(BaseModel):
    configured: bool
    status: str
    is_connected: bool
    calendar_id: Optional[str] = None
    sync_event_count: int = 0
    last_synced_at: Optional[str] = None
    last_error: Optional[str] = None
    guidance: Optional[str] = None
