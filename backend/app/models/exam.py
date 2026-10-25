import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    String,
    Integer,
    Boolean,
    DateTime,
    Enum,
    JSON,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.base import TimestampMixin


class ExamType(str, enum.Enum):
    THEORY = "THEORY"
    PRACTICAL = "PRACTICAL"


class ExamSittingStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    CHECKED = "CHECKED"
    INVALID = "INVALID"
    REVIEWED = "REVIEWED"
    PUBLISHED = "PUBLISHED"


class ExamSitting(Base, TimestampMixin):
    """
    Durable snapshot and allocation plan for an examination sitting
    (Theory seating plan or Practical workstation batches).
    """
    __tablename__ = "exam_sittings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    academic_term_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("academic_terms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    exam_type: Mapped[ExamType] = mapped_column(Enum(ExamType), default=ExamType.THEORY, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="DRAFT", nullable=False, index=True)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    start_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=180, nullable=False)
    buffer_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)

    input_snapshot: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    output_allocations: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    validation_report: Mapped[dict] = mapped_column(JSON, nullable=True)

    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
