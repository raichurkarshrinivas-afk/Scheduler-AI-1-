import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Boolean, Enum, ForeignKey, UniqueConstraint, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class UserRole(str, enum.Enum):
    """The five governed roles within an educational institution."""
    INSTITUTION_ADMINISTRATOR = "INSTITUTION_ADMINISTRATOR"
    TIMETABLE_COORDINATOR = "TIMETABLE_COORDINATOR"
    EXAM_CONTROLLER = "EXAM_CONTROLLER"
    TEACHER = "TEACHER"
    STUDENT = "STUDENT"

    # Compatibility aliases for legacy references
    ADMIN = "INSTITUTION_ADMINISTRATOR"
    SUPERADMIN = "INSTITUTION_ADMINISTRATOR"
    INSTRUCTOR = "TEACHER"


class User(Base, TimestampMixin):
    """Global user identity, decoupled from any single institutional boundary."""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    memberships = relationship("Membership", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    teacher_profiles = relationship("Teacher", back_populates="user", cascade="all, delete-orphan")
    student_profiles = relationship("Student", back_populates="user", cascade="all, delete-orphan")


class Membership(Base, TimestampMixin):
    """Binds global user identity to an institution with specific role permissions."""
    __tablename__ = "memberships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    institution = relationship("Institution", back_populates="memberships")
    user = relationship("User", back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("institution_id", "user_id", "role", name="uq_memberships_tenant_user_role"),
    )


class UserSession(Base, TimestampMixin):
    """Server-side browser session tracking with cryptographic token digests."""
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    institution_id: Mapped[str] = mapped_column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    csrf_token: Mapped[str] = mapped_column(String(64), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="sessions")
    institution = relationship("Institution")

    __table_args__ = (
        Index("ix_user_sessions_user_active", "user_id", "revoked_at", "expires_at"),
    )
