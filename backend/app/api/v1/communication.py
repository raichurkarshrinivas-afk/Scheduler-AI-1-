import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user, require_roles
from app.models.user import User, UserRole, Membership
from app.models.publication import CommunicationOutbox
from app.models.communication import NotificationCategory
from app.schemas.communication import (
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    OutboxEventResponse,
    CalendarStatusResponse,
)
from app.services.notification_service import NotificationService
from app.services.google_calendar_service import GoogleCalendarService
from app.services.outbox_processor import OutboxProcessor
from app.services.sse_manager import sse_manager

logger = logging.getLogger("api_communication")
router = APIRouter()


# ==========================================
# In-App Notifications
# ==========================================

@router.get("/notifications", response_model=NotificationListResponse)
def list_notifications(
    category: Optional[str] = Query(None, description="Optional category filter"),
    unread_only: bool = Query(False, description="Filter unread only"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    institution_id = current_user.memberships[0].institution_id if current_user.memberships else None
    if not institution_id:
        raise HTTPException(status_code=400, detail="No active institution membership found.")

    items, total = NotificationService.list_notifications(
        db=db,
        user_id=current_user.id,
        institution_id=institution_id,
        category=category,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )
    unread_count = NotificationService.get_unread_count(db, current_user.id, institution_id)

    response_items = []
    for it in items:
        response_items.append(
            NotificationResponse(
                id=it.id,
                institution_id=it.institution_id,
                recipient_user_id=it.recipient_user_id,
                category=it.category.value if hasattr(it.category, "value") else str(it.category),
                priority=it.priority.value if hasattr(it.priority, "value") else str(it.priority),
                title=it.title,
                message=it.message,
                data=it.data or {},
                is_read=it.is_read,
                read_at=it.read_at,
                scheduled_for=it.scheduled_for,
                delivered_at=it.delivered_at,
                created_at=it.created_at,
            )
        )

    return NotificationListResponse(items=response_items, total=total, unread_count=unread_count)


@router.get("/notifications/unread-count", response_model=UnreadCountResponse)
def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    institution_id = current_user.memberships[0].institution_id if current_user.memberships else None
    if not institution_id:
        return UnreadCountResponse(unread_count=0)
    count = NotificationService.get_unread_count(db, current_user.id, institution_id)
    return UnreadCountResponse(unread_count=count)


@router.post("/notifications/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notif = NotificationService.mark_as_read(db, notification_id, current_user.id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found.")
    return NotificationResponse(
        id=notif.id,
        institution_id=notif.institution_id,
        recipient_user_id=notif.recipient_user_id,
        category=notif.category.value if hasattr(notif.category, "value") else str(notif.category),
        priority=notif.priority.value if hasattr(notif.priority, "value") else str(notif.priority),
        title=notif.title,
        message=notif.message,
        data=notif.data or {},
        is_read=notif.is_read,
        read_at=notif.read_at,
        scheduled_for=notif.scheduled_for,
        delivered_at=notif.delivered_at,
        created_at=notif.created_at,
    )


@router.post("/notifications/mark-all-read")
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    institution_id = current_user.memberships[0].institution_id if current_user.memberships else None
    if not institution_id:
        return {"marked_count": 0}
    count = NotificationService.mark_all_as_read(db, current_user.id, institution_id)
    return {"marked_count": count}


# ==========================================
# Preferences & Quiet Hours
# ==========================================

@router.get("/preferences", response_model=NotificationPreferencesResponse)
def get_notification_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    institution_id = current_user.memberships[0].institution_id if current_user.memberships else None
    if not institution_id:
        raise HTTPException(status_code=400, detail="No active institution membership found.")
    pref = NotificationService.get_or_create_preferences(db, current_user.id, institution_id)
    return NotificationPreferencesResponse.model_validate(pref)


@router.put("/preferences", response_model=NotificationPreferencesResponse)
def update_notification_preferences(
    payload: NotificationPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    institution_id = current_user.memberships[0].institution_id if current_user.memberships else None
    if not institution_id:
        raise HTTPException(status_code=400, detail="No active institution membership found.")
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    pref = NotificationService.update_preferences(db, current_user.id, institution_id, updates)
    return NotificationPreferencesResponse.model_validate(pref)


# ==========================================
# Server-Sent Events (SSE) & Polling
# ==========================================

@router.get("/events/stream")
async def sse_event_stream(
    request: Request,
    last_event_id: Optional[str] = Header(None, alias="Last-Event-ID"),
    current_user: User = Depends(get_current_user),
):
    """
    Authenticated same-origin SSE connection.
    ZERO session tokens in URLs (uses session cookie or Authorization header).
    User- and institution-scoped. Replays missed events on reconnect.
    """
    institution_id = current_user.memberships[0].institution_id if current_user.memberships else None
    if not institution_id:
        raise HTTPException(status_code=400, detail="No active institution membership found.")

    last_id_int = 0
    if last_event_id:
        try:
            last_id_int = int(last_event_id)
        except ValueError:
            pass

    async def event_generator():
        # 1. Yield initial connected event
        yield f": connected\n\n"

        # 2. Replay missed events from ring buffer if reconnecting
        if last_id_int > 0:
            missed = sse_manager.get_missed_sse_messages(institution_id, current_user.id, last_id_int)
            for msg in missed:
                yield msg

        # 3. Register subscriber queue
        q = await sse_manager.register_subscriber(institution_id, current_user.id)
        try:
            while True:
                # Disconnect check
                if await request.is_disconnected():
                    break
                try:
                    # Wait for next event or 15s keepalive ping
                    event = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield event.to_sse_message()
                except asyncio.TimeoutError:
                    # Keepalive comment
                    yield f": ping\n\n"
        finally:
            await sse_manager.unregister_subscriber(institution_id, current_user.id, q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/events/poll")
def poll_events(
    since: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
):
    """Graceful polling fallback when SSE connection is unavailable."""
    institution_id = current_user.memberships[0].institution_id if current_user.memberships else None
    if not institution_id:
        return {"events": []}
    events = sse_manager.get_events_since(institution_id, current_user.id, since)
    return {"events": events}


# ==========================================
# Outbox & Retry Visibility (Staff Only)
# ==========================================

@router.get("/outbox", response_model=List[OutboxEventResponse])
def list_outbox_events(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    membership: Membership = Depends(require_roles(UserRole.INSTITUTION_ADMINISTRATOR, UserRole.TIMETABLE_COORDINATOR, UserRole.EXAM_CONTROLLER)),
    db: Session = Depends(get_db),
):
    institution_id = membership.institution_id
    q = db.query(CommunicationOutbox).filter(CommunicationOutbox.institution_id == institution_id)
    if status_filter:
        q = q.filter(CommunicationOutbox.status == status_filter)
    events = q.order_by(CommunicationOutbox.created_at.desc()).limit(limit).all()
    return events


@router.post("/outbox/{outbox_id}/retry", response_model=OutboxEventResponse)
def retry_outbox_event(
    outbox_id: str,
    membership: Membership = Depends(require_roles(UserRole.INSTITUTION_ADMINISTRATOR, UserRole.TIMETABLE_COORDINATOR, UserRole.EXAM_CONTROLLER)),
    db: Session = Depends(get_db),
):
    ev = OutboxProcessor.retry_event(db, outbox_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Outbox event not found.")
    return ev


# ==========================================
# Google Calendar Integration (Optional)
# ==========================================

@router.get("/calendar/status", response_model=CalendarStatusResponse)
def get_calendar_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    institution_id = current_user.memberships[0].institution_id if current_user.memberships else None
    if not institution_id:
        raise HTTPException(status_code=400, detail="No active institution membership found.")
    status_dict = GoogleCalendarService.get_credential_status(db, current_user.id, institution_id)
    return CalendarStatusResponse.model_validate(status_dict)


@router.get("/calendar/auth-url")
def get_calendar_auth_url(
    current_user: User = Depends(get_current_user),
):
    institution_id = current_user.memberships[0].institution_id if current_user.memberships else None
    if not institution_id:
        raise HTTPException(status_code=400, detail="No active institution membership found.")
    result = GoogleCalendarService.get_auth_url(current_user.id, institution_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result)
    return result


@router.get("/calendar/callback")
def handle_calendar_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db),
):
    success, message, _ = GoogleCalendarService.handle_oauth_callback(db, code, state)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"success": True, "message": message}


@router.post("/calendar/sync")
def trigger_calendar_sync(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    institution_id = current_user.memberships[0].institution_id if current_user.memberships else None
    if not institution_id:
        raise HTTPException(status_code=400, detail="No active institution membership found.")
    res = GoogleCalendarService.sync_user_calendar_safe(db, current_user.id, institution_id)
    return res


@router.post("/calendar/disconnect")
def disconnect_calendar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    institution_id = current_user.memberships[0].institution_id if current_user.memberships else None
    if not institution_id:
        raise HTTPException(status_code=400, detail="No active institution membership found.")
    disconnected = GoogleCalendarService.disconnect(db, current_user.id, institution_id)
    return {"disconnected": disconnected}
