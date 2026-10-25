import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import (
    String,
    Integer,
    Boolean,
    DateTime,
    JSON,
    ForeignKey,
    Index,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.base import TimestampMixin


class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobType(str, enum.Enum):
    TIMETABLE_SOLVE = "TIMETABLE_SOLVE"
    SEATING_ALLOCATION = "SEATING_ALLOCATION"
    REPORT_GENERATION = "REPORT_GENERATION"
    GENERIC_TASK = "GENERIC_TASK"


class Job(Base, TimestampMixin):
    """
    Durable PostgreSQL-backed background job with leased execution,
    heartbeats, fencing tokens, and retry tracking.
    """
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    input_reference: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default=JobStatus.QUEUED.value, nullable=False, index=True)
    
    # Timing and scheduling
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Attempts and lease ownership
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    lease_owner: Mapped[str] = mapped_column(String(255), nullable=True)
    lease_token: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    lease_expiry: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # Progress and status details (strictly meaningful labels, no fake %)
    phase_label: Mapped[str] = mapped_column(String(100), default="Queued", nullable=False)
    cancellation_requested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Output and diagnostics
    result_reference: Mapped[dict] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str] = mapped_column(String(1000), nullable=True)

    __table_args__ = (
        Index("ix_jobs_claim", "status", "available_at"),
        Index("ix_jobs_tenant_status", "institution_id", "status"),
        Index("ix_jobs_lease_recovery", "status", "lease_expiry"),
    )
