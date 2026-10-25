import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class AuditEvent(Base):
    """Immutable audit trail for all governance and operational actions."""
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )