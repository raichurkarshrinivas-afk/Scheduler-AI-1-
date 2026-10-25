import datetime
import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.communication import (
    Notification,
    NotificationPreference,
    NotificationCategory,
    NotificationPriority,
)
from app.models.publication import Publication
from app.models.user import User
from app.services.sse_manager import sse_manager

logger = logging.getLogger("notification_service")


class NotificationService:

    @staticmethod
    def get_or_create_preferences(
        db: Session,
        user_id: str,
        institution_id: str
    ) -> NotificationPreference:
        pref = db.query(NotificationPreference).filter(
            NotificationPreference.user_id == user_id,
            NotificationPreference.institution_id == institution_id
        ).first()

        if not pref:
            pref = NotificationPreference(
                user_id=user_id,
                institution_id=institution_id,
                quiet_hours_enabled=False,
                quiet_hours_start="22:00",
                quiet_hours_end="07:00",
                notify_academic_changes=True,
                notify_operational_alerts=True,
                notify_security_events=True,
                notify_scheduled_reminders=True,
                email_notifications_enabled=True,
                calendar_sync_enabled=True,
            )
            db.add(pref)
            db.commit()
            db.refresh(pref)
        return pref

    @staticmethod
    def update_preferences(
        db: Session,
        user_id: str,
        institution_id: str,
        updates: Dict[str, Any]
    ) -> NotificationPreference:
        pref = NotificationService.get_or_create_preferences(db, user_id, institution_id)
        for key, val in updates.items():
            if hasattr(pref, key) and key not in ["id", "user_id", "institution_id", "created_at"]:
                setattr(pref, key, val)
        db.commit()
        db.refresh(pref)
        return pref

    @staticmethod
    def is_in_quiet_hours(
        pref: NotificationPreference,
        check_time: Optional[datetime.time] = None
    ) -> bool:
        if not pref.quiet_hours_enabled:
            return False

        if check_time is None:
            check_time = datetime.datetime.now(datetime.timezone.utc).time()

        try:
            start_parts = [int(p) for p in (pref.quiet_hours_start or "22:00").split(":")]
            end_parts = [int(p) for p in (pref.quiet_hours_end or "07:00").split(":")]
            start_t = datetime.time(start_parts[0], start_parts[1])
            end_t = datetime.time(end_parts[0], end_parts[1])

            if start_t <= end_t:
                # Same day range, e.g. 13:00 to 14:00
                return start_t <= check_time <= end_t
            else:
                # Spans midnight, e.g. 22:00 to 07:00
                return check_time >= start_t or check_time <= end_t
        except Exception:
            return False

    @staticmethod
    def calculate_quiet_hours_end_dt(pref: NotificationPreference, now: Optional[datetime.datetime] = None) -> datetime.datetime:
        if now is None:
            now = datetime.datetime.now(datetime.timezone.utc)
        try:
            end_parts = [int(p) for p in (pref.quiet_hours_end or "07:00").split(":")]
            end_t = datetime.time(end_parts[0], end_parts[1])
            end_dt = datetime.datetime.combine(now.date(), end_t, tzinfo=datetime.timezone.utc)
            if end_dt <= now:
                end_dt += datetime.timedelta(days=1)
            return end_dt
        except Exception:
            return now + datetime.timedelta(hours=8)

    @staticmethod
    def create_notification(
        db: Session,
        institution_id: str,
        recipient_user_id: str,
        category: NotificationCategory,
        title: str,
        message: str,
        idempotency_key: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        data: Optional[Dict[str, Any]] = None,
        now: Optional[datetime.datetime] = None,
    ) -> Optional[Notification]:
        """
        Creates a notification with strict idempotency and quiet hours handling.
        Returns existing notification if duplicate idempotency key is presented.
        """
        if now is None:
            now = datetime.datetime.now(datetime.timezone.utc)

        # 1. Check idempotency first
        existing = db.query(Notification).filter(
            Notification.recipient_user_id == recipient_user_id,
            Notification.idempotency_key == idempotency_key
        ).first()
        if existing:
            return existing

        # 2. Check user preferences
        pref = NotificationService.get_or_create_preferences(db, recipient_user_id, institution_id)
        if category == NotificationCategory.ACADEMIC_CHANGE and not pref.notify_academic_changes:
            return None
        if category == NotificationCategory.OPERATIONAL_ALERT and not pref.notify_operational_alerts:
            return None
        if category == NotificationCategory.SECURITY_EVENT and not pref.notify_security_events:
            return None
        if category == NotificationCategory.SCHEDULED_REMINDER and not pref.notify_scheduled_reminders:
            return None

        # 3. Check quiet hours
        scheduled_for: Optional[datetime.datetime] = None
        delivered_at: Optional[datetime.datetime] = now

        if priority == NotificationPriority.URGENT:
            # Urgent notifications ALWAYS bypass quiet hours immediately
            delivered_at = now
            scheduled_for = None
        else:
            # Non-urgent: check quiet hours
            if NotificationService.is_in_quiet_hours(pref, now.time()):
                scheduled_for = NotificationService.calculate_quiet_hours_end_dt(pref, now)
                delivered_at = None

        notif = Notification(
            institution_id=institution_id,
            recipient_user_id=recipient_user_id,
            category=category,
            priority=priority,
            title=title,
            message=message,
            data=data or {},
            idempotency_key=idempotency_key,
            is_read=False,
            scheduled_for=scheduled_for,
            delivered_at=delivered_at,
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)

        # 4. SSE real-time broadcast if delivered immediately
        if delivered_at is not None:
            sse_manager.publish_event_sync(
                institution_id=institution_id,
                event_type="NOTIFICATION_NEW",
                payload={
                    "notification_id": notif.id,
                    "category": notif.category.value if hasattr(notif.category, 'value') else notif.category,
                    "priority": notif.priority.value if hasattr(notif.priority, 'value') else notif.priority,
                    "title": notif.title,
                    "message": notif.message,
                    "is_read": False,
                    "created_at": notif.created_at.isoformat() if notif.created_at else None,
                },
                target_user_id=recipient_user_id
            )

        return notif

    @staticmethod
    def get_unread_count(db: Session, user_id: str, institution_id: str) -> int:
        now = datetime.datetime.now(datetime.timezone.utc)
        return db.query(Notification).filter(
            Notification.recipient_user_id == user_id,
            Notification.institution_id == institution_id,
            Notification.is_read == False,
            # Either delivered_at is set, or scheduled_for has arrived
            (Notification.delivered_at != None) | (Notification.scheduled_for <= now)
        ).count()

    @staticmethod
    def list_notifications(
        db: Session,
        user_id: str,
        institution_id: str,
        category: Optional[str] = None,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Notification], int]:
        now = datetime.datetime.now(datetime.timezone.utc)
        q = db.query(Notification).filter(
            Notification.recipient_user_id == user_id,
            Notification.institution_id == institution_id,
            (Notification.delivered_at != None) | (Notification.scheduled_for <= now)
        )
        if category:
            q = q.filter(Notification.category == category)
        if unread_only:
            q = q.filter(Notification.is_read == False)

        total = q.count()
        items = q.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
        return items, total

    @staticmethod
    def mark_as_read(db: Session, notification_id: str, user_id: str) -> Optional[Notification]:
        notif = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.recipient_user_id == user_id
        ).first()
        if notif:
            notif.is_read = True
            notif.read_at = datetime.datetime.now(datetime.timezone.utc)
            db.commit()
            db.refresh(notif)
        return notif

    @staticmethod
    def mark_all_as_read(db: Session, user_id: str, institution_id: str) -> int:
        now = datetime.datetime.now(datetime.timezone.utc)
        count = db.query(Notification).filter(
            Notification.recipient_user_id == user_id,
            Notification.institution_id == institution_id,
            Notification.is_read == False
        ).update(
            {"is_read": True, "read_at": now},
            synchronize_session="fetch"
        )
        db.commit()
        return count

    @staticmethod
    def create_operational_alert(
        db: Session,
        institution_id: str,
        recipient_user_id: str,
        title: str,
        message: str,
        idempotency_key: str,
        data: Optional[Dict[str, Any]] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL
    ) -> Optional[Notification]:
        return NotificationService.create_notification(
            db=db,
            institution_id=institution_id,
            recipient_user_id=recipient_user_id,
            category=NotificationCategory.OPERATIONAL_ALERT,
            title=title,
            message=message,
            idempotency_key=idempotency_key,
            priority=priority,
            data=data,
        )

    @staticmethod
    def create_security_event(
        db: Session,
        institution_id: str,
        recipient_user_id: str,
        title: str,
        message: str,
        idempotency_key: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Optional[Notification]:
        # Security events are URGENT: always bypass quiet hours!
        return NotificationService.create_notification(
            db=db,
            institution_id=institution_id,
            recipient_user_id=recipient_user_id,
            category=NotificationCategory.SECURITY_EVENT,
            title=title,
            message=message,
            idempotency_key=idempotency_key,
            priority=NotificationPriority.URGENT,
            data=data,
        )

    @staticmethod
    def get_affected_users_for_publication(
        db: Session,
        publication: Publication
    ) -> Tuple[Set[str], Set[str]]:
        """
        Determines targeted teachers and students affected by this publication.
        Never notifies unaffected users!
        """
        target_teacher_user_ids: Set[str] = set()
        target_student_user_ids: Set[str] = set()

        snapshot = publication.snapshot or {}

        if publication.publication_type == "TIMETABLE":
            assignments = snapshot.get("assignments", [])
            # If publication diff is stored in outbox or payload, check changed
            # Otherwise for v1 all participants are affected
            teacher_ids = {a.get("teacher_id") for a in assignments if a.get("teacher_id")}
            section_ids = {a.get("section_id") for a in assignments if a.get("section_id")}

            if teacher_ids:
                # Find user_id for teachers
                teacher_users = db.execute(
                    text("SELECT user_id FROM teachers WHERE id IN :tids AND user_id IS NOT NULL"),
                    {"tids": tuple(teacher_ids)}
                ).fetchall()
                target_teacher_user_ids.update(r[0] for r in teacher_users)

            if section_ids:
                # Find user_id for enrolled students
                student_users = db.execute(
                    text(
                        "SELECT s.user_id FROM enrolments e "
                        "JOIN students s ON e.student_id = s.id "
                        "WHERE e.section_id IN :sids AND s.user_id IS NOT NULL"
                    ),
                    {"sids": tuple(section_ids)}
                ).fetchall()
                target_student_user_ids.update(r[0] for r in student_users)

        elif publication.publication_type == "EXAM_SEATING":
            allocations = snapshot.get("allocations", [])
            student_users = {a.get("student_user_id") for a in allocations if a.get("student_user_id")}
            target_student_user_ids.update(student_users)

        return target_teacher_user_ids, target_student_user_ids
