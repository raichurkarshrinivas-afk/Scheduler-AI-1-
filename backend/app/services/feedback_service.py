import datetime
import hashlib
import logging
import random
import string
import time
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from app.models.feedback import (
    FeedbackSubmission,
    FeedbackInternalNote,
    FeedbackStatus,
    FeedbackCategory,
)
from app.models.user import User, UserRole, Membership
from app.models.audit import AuditEvent

logger = logging.getLogger("feedback_service")


class FeedbackRateLimiter:
    """In-memory sliding window rate limiter for public contact submissions"""
    def __init__(self, max_requests: int = 5, window_seconds: int = 600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._history: Dict[str, List[float]] = {}

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        ip_hash = hashlib.sha256(client_ip.encode("utf-8")).hexdigest()[:16]

        if ip_hash not in self._history:
            self._history[ip_hash] = []

        # Filter out timestamps outside window
        window_start = now - self.window_seconds
        self._history[ip_hash] = [t for t in self._history[ip_hash] if t > window_start]

        if len(self._history[ip_hash]) >= self.max_requests:
            return False

        self._history[ip_hash].append(now)
        return True

    def reset_for_testing(self):
        self._history.clear()


public_feedback_limiter = FeedbackRateLimiter(max_requests=5, window_seconds=600)


class FeedbackService:

    @staticmethod
    def generate_reference_code(db: Session) -> str:
        chars = string.ascii_uppercase + "23456789"
        for _ in range(10):
            suffix = "".join(random.choices(chars, k=8))
            code = f"FB-{suffix}"
            exists = db.query(FeedbackSubmission).filter(FeedbackSubmission.reference_code == code).first()
            if not exists:
                return code
        return f"FB-{uuid.uuid4().hex[:8].upper()}"

    @staticmethod
    def submit_public_feedback(
        db: Session,
        subject: str,
        message: str,
        category: str = "GENERAL_INQUIRY",
        contact_name: Optional[str] = None,
        contact_email: Optional[str] = None,
        honeypot: Optional[str] = None,
        client_ip: str = "127.0.0.1",
    ) -> Dict[str, Any]:
        """
        Public contact submission with honeypot bot trap, rate limits, and generic confirmation.
        """
        # 1. Bot mitigation: Honeypot check
        if honeypot and honeypot.strip():
            logger.warning(f"Bot trap triggered for IP {client_ip}")
            # Silently accept or return generic message without persisting spam
            return {
                "success": True,
                "reference_code": "FB-RECEIVED",
                "message": "Thank you for reaching out. Your message has been received.",
            }

        # 2. Rate limiting check
        if not public_feedback_limiter.is_allowed(client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded for contact submissions. Please wait before submitting again.",
            )

        # 3. Server-side validation
        subject = subject.strip()
        message = message.strip()
        if len(subject) < 3:
            raise HTTPException(status_code=400, detail="Subject must be at least 3 characters.")
        if len(subject) > 200:
            raise HTTPException(status_code=400, detail="Subject cannot exceed 200 characters.")
        if len(message) < 10:
            raise HTTPException(status_code=400, detail="Message must be at least 10 characters.")
        if len(message) > 5000:
            raise HTTPException(status_code=400, detail="Message exceeds maximum allowed length of 5000 characters.")

        if contact_email and contact_email.strip():
            contact_email = contact_email.strip()
            if "@" not in contact_email or "." not in contact_email or len(contact_email) > 255:
                raise HTTPException(status_code=400, detail="Invalid contact email format.")

        ref_code = FeedbackService.generate_reference_code(db)
        ip_hash = hashlib.sha256(client_ip.encode("utf-8")).hexdigest()

        submission = FeedbackSubmission(
            reference_code=ref_code,
            institution_id=None,
            submitting_user_id=None,
            contact_name=contact_name.strip() if contact_name else None,
            contact_email=contact_email.strip() if contact_email else None,
            category=category,
            subject=subject,
            message=message,
            status=FeedbackStatus.NEW.value,
            ip_address_hash=ip_hash,
        )
        db.add(submission)
        db.commit()

        # Optional email acknowledgement can be logged/skipped if unconfigured
        logger.info(f"Public feedback {ref_code} persisted successfully.")

        # Generic confirmation that does NOT expose internal records or UUIDs
        return {
            "success": True,
            "reference_code": ref_code,
            "message": "Thank you for contacting us. Your message has been received securely.",
        }

    @staticmethod
    def submit_authenticated_feedback(
        db: Session,
        current_user: User,
        membership: Membership,
        category: str,
        subject: str,
        message: str,
        page_reference: Optional[str] = None,
    ) -> FeedbackSubmission:
        """
        Authenticated feedback deriving user and institution strictly from the active session.
        """
        subject = subject.strip()
        message = message.strip()
        if len(subject) < 3:
            raise HTTPException(status_code=400, detail="Subject must be at least 3 characters.")
        if len(subject) > 200:
            raise HTTPException(status_code=400, detail="Subject cannot exceed 200 characters.")
        if len(message) < 10:
            raise HTTPException(status_code=400, detail="Message must be at least 10 characters.")
        if len(message) > 5000:
            raise HTTPException(status_code=400, detail="Message exceeds maximum allowed length of 5000 characters.")

        ref_code = FeedbackService.generate_reference_code(db)

        submission = FeedbackSubmission(
            reference_code=ref_code,
            institution_id=membership.institution_id,
            submitting_user_id=current_user.id,
            contact_name=current_user.full_name,
            contact_email=current_user.email,
            category=category,
            subject=subject,
            message=message,
            page_reference=page_reference.strip() if page_reference else None,
            status=FeedbackStatus.NEW.value,
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)
        return submission

    @staticmethod
    def get_user_submissions(
        db: Session,
        user_id: str,
        institution_id: str
    ) -> List[FeedbackSubmission]:
        """
        Returns submissions made by this user in this institution.
        Strictly excludes internal notes.
        """
        return db.query(FeedbackSubmission).filter(
            FeedbackSubmission.submitting_user_id == user_id,
            FeedbackSubmission.institution_id == institution_id
        ).order_by(FeedbackSubmission.created_at.desc()).all()

    @staticmethod
    def list_management_feedback(
        db: Session,
        reviewer: User,
        membership: Membership,
        status_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        search_query: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[FeedbackSubmission], int]:
        """
        Staff administrative listing.
        Strictly enforces institutional boundaries:
        - Institution staff can ONLY review feedback from their own institution.
        - Public submissions (institution_id is None) are only visible to platform admins.
        """
        q = db.query(FeedbackSubmission)

        # Scoped visibility
        if membership.role == UserRole.INSTITUTION_ADMINISTRATOR:
            # Can see submissions for their institution, plus public submissions if flagged/root
            q = q.filter(
                or_(
                    FeedbackSubmission.institution_id == membership.institution_id,
                    FeedbackSubmission.institution_id == None
                )
            )
        else:
            # Coordinator / Exam Controller: strictly their institution
            q = q.filter(FeedbackSubmission.institution_id == membership.institution_id)

        if status_filter and status_filter != "ALL":
            q = q.filter(FeedbackSubmission.status == status_filter)

        if category_filter and category_filter != "ALL":
            q = q.filter(FeedbackSubmission.category == category_filter)

        if search_query and search_query.strip():
            sq = f"%{search_query.strip()}%"
            q = q.filter(
                or_(
                    FeedbackSubmission.subject.ilike(sq),
                    FeedbackSubmission.reference_code.ilike(sq),
                    FeedbackSubmission.contact_name.ilike(sq),
                    FeedbackSubmission.contact_email.ilike(sq),
                )
            )

        total = q.count()
        items = q.order_by(FeedbackSubmission.created_at.desc()).offset(offset).limit(limit).all()
        return items, total

    @staticmethod
    def get_management_submission_by_id(
        db: Session,
        submission_id: str,
        reviewer_membership: Membership
    ) -> FeedbackSubmission:
        """
        Retrieves submission for administrative management.
        Authoritatively denies cross-institution review.
        """
        submission = db.query(FeedbackSubmission).filter(FeedbackSubmission.id == submission_id).first()
        if not submission:
            raise HTTPException(status_code=404, detail="Feedback submission not found.")

        # Cross-institution review check
        if submission.institution_id is not None:
            if submission.institution_id != reviewer_membership.institution_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Cross-institution feedback review is not permitted."
                )
        else:
            # Public submission
            if reviewer_membership.role != UserRole.INSTITUTION_ADMINISTRATOR:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Public contact submissions require platform administrator privileges."
                )

        return submission

    @staticmethod
    def update_submission_status(
        db: Session,
        submission_id: str,
        new_status: str,
        reviewer: User,
        membership: Membership,
        assigned_reviewer_id: Optional[str] = None
    ) -> FeedbackSubmission:
        submission = FeedbackService.get_management_submission_by_id(db, submission_id, membership)

        valid_statuses = [s.value for s in FeedbackStatus]
        if new_status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

        old_status = submission.status
        submission.status = new_status

        if assigned_reviewer_id is not None:
            if assigned_reviewer_id == "":
                submission.assigned_reviewer_id = None
            else:
                # Verify assigned reviewer belongs to same institution or is valid user
                assigned_user = db.query(User).filter(User.id == assigned_reviewer_id).first()
                if not assigned_user:
                    raise HTTPException(status_code=400, detail="Assigned reviewer user not found.")
                submission.assigned_reviewer_id = assigned_reviewer_id

        # Write audit log
        audit = AuditEvent(
            institution_id=membership.institution_id,
            user_id=reviewer.id,
            event_type="FEEDBACK_STATUS_UPDATED",
            action="UPDATE_STATUS",
            entity_type="feedback_submission",
            entity_id=submission.id,
            payload={
                "old_status": old_status,
                "new_status": new_status,
                "assigned_reviewer_id": submission.assigned_reviewer_id,
                "reference_code": submission.reference_code,
            }
        )
        db.add(audit)
        db.commit()
        db.refresh(submission)
        return submission

    @staticmethod
    def add_internal_note(
        db: Session,
        submission_id: str,
        note_text: str,
        author: User,
        membership: Membership
    ) -> FeedbackInternalNote:
        submission = FeedbackService.get_management_submission_by_id(db, submission_id, membership)

        note_text = note_text.strip()
        if not note_text:
            raise HTTPException(status_code=400, detail="Note text cannot be empty.")
        if len(note_text) > 3000:
            raise HTTPException(status_code=400, detail="Note text exceeds maximum length of 3000 characters.")

        note = FeedbackInternalNote(
            feedback_id=submission.id,
            author_user_id=author.id,
            note=note_text,
        )
        db.add(note)

        audit = AuditEvent(
            institution_id=membership.institution_id,
            user_id=author.id,
            event_type="FEEDBACK_INTERNAL_NOTE_ADDED",
            action="ADD_NOTE",
            entity_type="feedback_submission",
            entity_id=submission.id,
            payload={"reference_code": submission.reference_code}
        )
        db.add(audit)
        db.commit()
        db.refresh(note)
        return note
