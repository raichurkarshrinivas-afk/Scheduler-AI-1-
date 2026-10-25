import enum
import uuid
from typing import Optional
from datetime import datetime, date
from sqlalchemy import (
    String,
    Integer,
    Boolean,
    DateTime,
    Text,
    Date,
    Enum,
    JSON,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class PublicationType(str, enum.Enum):
    TIMETABLE = "TIMETABLE"
    EXAM_THEORY = "EXAM_THEORY"
    EXAM_PRACTICAL = "EXAM_PRACTICAL"


class OutboxEventStatus(str, enum.Enum):
    PENDING = "PENDING"
    DISPATCHED = "DISPATCHED"
    FAILED = "FAILED"


class Publication(Base, TimestampMixin):
    """
    Immutable publication record for an academic timetable or examination sitting.
    Represents an officially released version accessible to students and staff.
    """
    __tablename__ = "publications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    academic_term_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("academic_terms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    publication_type: Mapped[PublicationType] = mapped_column(
        Enum(PublicationType), default=PublicationType.TIMETABLE, nullable=False, index=True
    )
    source_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    published_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    publication_note: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    diff_summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    checker_report: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("institution_id", "academic_term_id", "publication_type", "version_number", name="uq_publication_version"),
    )


class SharedResourceReservation(Base, TimestampMixin):
    """
    Active shared-resource reservation locked by an active published schedule.
    Prevents competing publications from double-booking physical rooms or laboratories.
    """
    __tablename__ = "shared_resource_reservations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    academic_term_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("academic_terms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    publication_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("publications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "ROOM", "LAB"
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0 = Monday ... 6 = Sunday
    period: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[str] = mapped_column(String(10), nullable=True)
    end_time: Mapped[str] = mapped_column(String(10), nullable=True)
    session_title: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)


class CommunicationOutbox(Base, TimestampMixin):
    """
    Durable transactional outbox for publication events.
    Written atomically inside the publication transaction without external I/O.
    """
    __tablename__ = "communication_outbox"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    publication_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("publications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    recipient_role: Mapped[str] = mapped_column(String(50), nullable=False)  # STUDENT, TEACHER, ALL
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[OutboxEventStatus] = mapped_column(
        Enum(OutboxEventStatus), default=OutboxEventStatus.PENDING, nullable=False, index=True
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
