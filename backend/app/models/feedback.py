import enum
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    String,
    Text,
    DateTime,
    ForeignKey,
    Enum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class FeedbackStatus(str, enum.Enum):
    NEW = "new"
    REVIEWING = "reviewing"
    AWAITING_INFORMATION = "awaiting_information"
    RESOLVED = "resolved"
    CLOSED = "closed"


class FeedbackCategory(str, enum.Enum):
    BUG_REPORT = "BUG_REPORT"
    SUGGESTION = "SUGGESTION"
    ACCESS_ISSUE = "ACCESS_ISSUE"
    SCHEDULING_ISSUE = "SCHEDULING_ISSUE"
    GENERAL_INQUIRY = "GENERAL_INQUIRY"
    PLATFORM_SUPPORT = "PLATFORM_SUPPORT"
    OTHER = "OTHER"


class FeedbackSubmission(Base, TimestampMixin):
    """
    Public and authenticated contact & feedback submissions.
    Separates user-facing submissions from internally protected reviewer notes.
    """
    __tablename__ = "feedback_submissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reference_code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)

    # Optional institutional scoping (None for public submissions)
    institution_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("institutions.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Optional submitter scoping (None for public/anonymous submissions)
    submitting_user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Optional contact details for public submissions
    contact_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    page_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    status: Mapped[str] = mapped_column(String(50), default=FeedbackStatus.NEW.value, nullable=False, index=True)

    # Assigned staff reviewer
    assigned_reviewer_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    ip_address_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Relationships
    institution = relationship("Institution", backref="feedback_submissions")
    submitting_user = relationship("User", foreign_keys=[submitting_user_id], backref="submitted_feedback")
    assigned_reviewer = relationship("User", foreign_keys=[assigned_reviewer_id], backref="assigned_feedback")
    internal_notes = relationship(
        "FeedbackInternalNote",
        back_populates="feedback",
        cascade="all, delete-orphan",
        order_by="FeedbackInternalNote.created_at.asc()"
    )


class FeedbackInternalNote(Base):
    """
    Separately protected internal notes visible only to authorised reviewers.
    Never returned to students or submitters.
    """
    __tablename__ = "feedback_internal_notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    feedback_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("feedback_submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    author_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    note: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    feedback = relationship("FeedbackSubmission", back_populates="internal_notes")
    author = relationship("User", foreign_keys=[author_user_id])
