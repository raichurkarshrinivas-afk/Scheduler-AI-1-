import datetime
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.publication import (
    CommunicationOutbox,
    OutboxEventStatus,
    Publication,
)
from app.models.communication import (
    NotificationCategory,
    NotificationPriority,
)
from app.services.notification_service import NotificationService
from app.services.google_calendar_service import GoogleCalendarService
from app.services.sse_manager import sse_manager

logger = logging.getLogger("outbox_processor")


class OutboxProcessor:

    @staticmethod
    def process_pending_events(db: Session, max_batch: int = 50) -> int:
        now = datetime.datetime.now(datetime.timezone.utc)
        events = db.query(CommunicationOutbox).filter(
            (CommunicationOutbox.status == OutboxEventStatus.PENDING) |
            (
                (CommunicationOutbox.status == OutboxEventStatus.FAILED) &
                (CommunicationOutbox.retry_count < CommunicationOutbox.max_retries) &
                ((CommunicationOutbox.next_retry_at == None) | (CommunicationOutbox.next_retry_at <= now))
            )
        ).order_by(CommunicationOutbox.created_at.asc()).limit(max_batch).all()

        processed_count = 0
        for ev in events:
            success = OutboxProcessor.process_single_event(db, ev)
            if success:
                processed_count += 1
        return processed_count

    @staticmethod
    def process_single_event(db: Session, ev: CommunicationOutbox) -> bool:
        now = datetime.datetime.now(datetime.timezone.utc)
        # In progress
        pass

        try:
            if ev.event_type == "TIMETABLE_PUBLISHED":
                pub = db.query(Publication).filter(Publication.id == ev.publication_id).first()
                if not pub:
                    raise ValueError(f"Publication {ev.publication_id} not found.")

                target_teachers, target_students = NotificationService.get_affected_users_for_publication(db, pub)
                version_num = ev.payload.get("version_number", pub.version_number) if ev.payload else pub.version_number
                note = ev.payload.get("publication_note", pub.publication_note or "") if ev.payload else (pub.publication_note or "")

                title = f"Timetable Published (v{version_num})"
                msg = f"A new timetable version has been published. {note}".strip()

                # Idempotently notify teachers
                for uid in target_teachers:
                    idempotency_key = f"outbox_{ev.id}_user_{uid}"
                    NotificationService.create_notification(
                        db=db,
                        institution_id=ev.institution_id,
                        recipient_user_id=uid,
                        category=NotificationCategory.ACADEMIC_CHANGE,
                        title=title,
                        message=msg,
                        idempotency_key=idempotency_key,
                        priority=NotificationPriority.NORMAL,
                        data={"publication_id": pub.id, "version_number": version_num},
                    )
                    # Trigger calendar sync safely without undoing publication
                    GoogleCalendarService.sync_user_calendar_safe(db, uid, ev.institution_id, pub)

                # Idempotently notify students
                for uid in target_students:
                    idempotency_key = f"outbox_{ev.id}_user_{uid}"
                    NotificationService.create_notification(
                        db=db,
                        institution_id=ev.institution_id,
                        recipient_user_id=uid,
                        category=NotificationCategory.ACADEMIC_CHANGE,
                        title=title,
                        message=msg,
                        idempotency_key=idempotency_key,
                        priority=NotificationPriority.NORMAL,
                        data={"publication_id": pub.id, "version_number": version_num},
                    )
                    GoogleCalendarService.sync_user_calendar_safe(db, uid, ev.institution_id, pub)

                # Broadcast publication event over SSE
                sse_manager.publish_event_sync(
                    institution_id=ev.institution_id,
                    event_type="PUBLICATION_UPDATED",
                    payload={
                        "publication_id": pub.id,
                        "publication_type": pub.publication_type,
                        "version_number": version_num,
                        "affected_teachers_count": len(target_teachers),
                        "affected_students_count": len(target_students),
                    }
                )

            elif ev.event_type == "EXAM_PUBLISHED":
                pub = db.query(Publication).filter(Publication.id == ev.publication_id).first()
                if not pub:
                    raise ValueError(f"Publication {ev.publication_id} not found.")

                _, target_students = NotificationService.get_affected_users_for_publication(db, pub)
                title = "Exam Seating Published"
                msg = f"Exam seating allocations have been published for {ev.payload.get('sitting_name', 'your examination')}."

                for uid in target_students:
                    idempotency_key = f"outbox_{ev.id}_user_{uid}"
                    NotificationService.create_notification(
                        db=db,
                        institution_id=ev.institution_id,
                        recipient_user_id=uid,
                        category=NotificationCategory.ACADEMIC_CHANGE,
                        title=title,
                        message=msg,
                        idempotency_key=idempotency_key,
                        priority=NotificationPriority.NORMAL,
                        data={"publication_id": pub.id},
                    )
                    GoogleCalendarService.sync_user_calendar_safe(db, uid, ev.institution_id, pub)

                sse_manager.publish_event_sync(
                    institution_id=ev.institution_id,
                    event_type="PUBLICATION_UPDATED",
                    payload={
                        "publication_id": pub.id,
                        "publication_type": pub.publication_type,
                        "version_number": pub.version_number,
                    }
                )

            # Mark processed
            ev.status = OutboxEventStatus.DISPATCHED
            ev.processed_at = now
            ev.last_error = None
            db.commit()
            return True

        except Exception as ex:
            logger.error(f"Failed to process outbox event {ev.id}: {ex}")
            ev.retry_count += 1
            ev.last_error = str(ex)
            ev.status = OutboxEventStatus.FAILED
            backoff_secs = min(3600, (2 ** ev.retry_count) * 10)
            ev.next_retry_at = now + datetime.timedelta(seconds=backoff_secs)
            db.commit()
            return False

    @staticmethod
    def retry_event(db: Session, outbox_id: str) -> Optional[CommunicationOutbox]:
        ev = db.query(CommunicationOutbox).filter(CommunicationOutbox.id == outbox_id).first()
        if not ev:
            return None
        ev.status = OutboxEventStatus.PENDING
        ev.next_retry_at = None
        ev.last_error = None
        db.commit()
        # Immediately attempt processing
        OutboxProcessor.process_single_event(db, ev)
        db.refresh(ev)
        return ev
