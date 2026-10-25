import uuid
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class Institution(Base, TimestampMixin):
    """Primary tenant boundary. Every tenant-scoped entity isolates by institution_id."""
    __tablename__ = "institutions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    memberships = relationship("Membership", back_populates="institution", cascade="all, delete-orphan")
    departments = relationship("Department", back_populates="institution", cascade="all, delete-orphan")
    academic_terms = relationship("AcademicTerm", back_populates="institution", cascade="all, delete-orphan")
    buildings = relationship("Building", back_populates="institution", cascade="all, delete-orphan")
    rooms = relationship("Room", back_populates="institution", cascade="all, delete-orphan")