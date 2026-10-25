import enum
import uuid
from datetime import time, date, datetime
from sqlalchemy import (
    String,
    Integer,
    Float,
    Boolean,
    Time,
    Date,
    DateTime,
    Enum,
    JSON,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin
from app.models.facility import RoomType


class SessionType(str, enum.Enum):
    LECTURE = "LECTURE"
    PRACTICAL = "PRACTICAL"
    TUTORIAL = "TUTORIAL"
    THEORY_EXAM = "THEORY_EXAM"
    PRACTICAL_EXAM = "PRACTICAL_EXAM"


class SessionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    CHECKED = "CHECKED"
    REVIEWED = "REVIEWED"
    PUBLISHED = "PUBLISHED"
    CANCELLED = "CANCELLED"


class TargetType(str, enum.Enum):
    TEACHER = "TEACHER"
    ROOM = "ROOM"
    SECTION = "SECTION"


class CalendarExceptionType(str, enum.Enum):
    HOLIDAY = "HOLIDAY"
    SPECIAL_SCHEDULE = "SPECIAL_SCHEDULE"
    BLACKOUT_PERIOD = "BLACKOUT_PERIOD"
    EXAM_DAY = "EXAM_DAY"
    CANCELLATION = "CANCELLATION"


class ConstraintType(str, enum.Enum):
    HARD = "HARD"
    SOFT = "SOFT"


class Session(Base, TimestampMixin):
    """Timetable class session or exam sitting.
    Distinguishes recurring weekly patterns from dated actual events.
    """
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_term_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    section_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
    session_type: Mapped[SessionType] = mapped_column(Enum(SessionType), nullable=False)
    room_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
    primary_teacher_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)

    # Recurring pattern fields (weekly academic timetable)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=True)  # 0=Monday ... 6=Sunday
    start_time: Mapped[time] = mapped_column(Time, nullable=True)
    end_time: Mapped[time] = mapped_column(Time, nullable=True)

    # Dated event fields (fixed exam dates / specific date occurrences)
    start_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    end_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    is_recurring: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[SessionStatus] = mapped_column(Enum(SessionStatus), default=SessionStatus.DRAFT, nullable=False)

    section = relationship("Section", back_populates="sessions", overlaps="primary_teacher,room,sessions")
    room = relationship("Room", back_populates="sessions", overlaps="primary_teacher,section,sessions")
    primary_teacher = relationship("Teacher", back_populates="assigned_sessions", overlaps="room,section,sessions")
    requirements = relationship("SessionRequirement", back_populates="session", cascade="all, delete-orphan", overlaps="session")

    __table_args__ = (
        UniqueConstraint("id", "institution_id", name="uq_sessions_id_tenant"),
        ForeignKeyConstraint(["academic_term_id", "institution_id"], ["academic_terms.id", "academic_terms.institution_id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["section_id", "institution_id"], ["sections.id", "sections.institution_id"], ondelete="SET NULL"),
        ForeignKeyConstraint(["room_id", "institution_id"], ["rooms.id", "rooms.institution_id"], ondelete="SET NULL"),
        ForeignKeyConstraint(["primary_teacher_id", "institution_id"], ["teachers.id", "teachers.institution_id"], ondelete="SET NULL"),
    )


class AvailabilityRule(Base, TimestampMixin):
    """Recurring weekly availability or unavailability rule for a teacher or room."""
    __tablename__ = "availability_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    target_type: Mapped[TargetType] = mapped_column(Enum(TargetType), nullable=False)
    teacher_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
    room_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Monday ... 6=Sunday
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # False = Unavailable
    reason: Mapped[str] = mapped_column(String(255), nullable=True)

    teacher = relationship("Teacher", back_populates="availability_rules", overlaps="teacher")

    __table_args__ = (
        ForeignKeyConstraint(["teacher_id", "institution_id"], ["teachers.id", "teachers.institution_id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["room_id", "institution_id"], ["rooms.id", "rooms.institution_id"], ondelete="CASCADE"),
    )


class CalendarException(Base, TimestampMixin):
    """Specific dated exception (e.g. holiday, weather closure, exam blackout)."""
    __tablename__ = "calendar_exceptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_term_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
    exception_date: Mapped[date] = mapped_column(Date, nullable=False)
    exception_type: Mapped[CalendarExceptionType] = mapped_column(Enum(CalendarExceptionType), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = (
        UniqueConstraint("institution_id", "exception_date", "exception_type", name="uq_cal_exc_tenant_date_type"),
        ForeignKeyConstraint(["academic_term_id", "institution_id"], ["academic_terms.id", "academic_terms.institution_id"], ondelete="CASCADE"),
    )


class SessionRequirement(Base, TimestampMixin):
    """Equipment, capacity, and facility constraints for a session."""
    __tablename__ = "session_requirements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
    section_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
    min_capacity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    room_type_required: Mapped[RoomType] = mapped_column(Enum(RoomType), nullable=True)
    requires_computers: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    required_workstation_features: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    special_accommodations: Mapped[str] = mapped_column(String(255), nullable=True)

    session = relationship("Session", back_populates="requirements", overlaps="requirements,session")

    __table_args__ = (
        ForeignKeyConstraint(["session_id", "institution_id"], ["sessions.id", "sessions.institution_id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["section_id", "institution_id"], ["sections.id", "sections.institution_id"], ondelete="CASCADE"),
    )


class ConstraintRule(Base, TimestampMixin):
    """Configurable solver rules (Hard constraints vs Soft penalties)."""
    __tablename__ = "constraint_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_code: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_type: Mapped[ConstraintType] = mapped_column(Enum(ConstraintType), default=ConstraintType.HARD, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    penalty_weight: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (
        UniqueConstraint("institution_id", "rule_code", name="uq_constraint_rules_tenant_code"),
    )

class TimetableDraft(Base, TimestampMixin):
    """
    Durable snapshot and solution record for academic timetable generation.
    Tracks input hashes, rule versions, solver output states, and independent validation reports.
    """
    __tablename__ = "timetable_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    academic_term_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("academic_terms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="DRAFT", nullable=False, index=True)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Immutable input snapshot and provenance
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    input_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Output solution
    output_assignments: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    solver_status: Mapped[str] = mapped_column(String(50), nullable=True)  # OPTIMAL, FEASIBLE, INFEASIBLE, UNKNOWN, MODEL_INVALID
    solver_runtime_seconds: Mapped[float] = mapped_column(Float, nullable=True)
    solver_objective: Mapped[float] = mapped_column(Float, nullable=True)
    solver_best_bound: Mapped[float] = mapped_column(Float, nullable=True)

    # Provenance versions
    model_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    rule_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    checker_version: Mapped[str] = mapped_column(String(50), default="1.0.0", nullable=False)
    solver_version: Mapped[str] = mapped_column(String(50), default="ortools-9.15", nullable=False)

    # Independent Checker Report
    validation_report: Mapped[dict] = mapped_column(JSON, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
