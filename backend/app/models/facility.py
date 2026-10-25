import enum
import uuid
from sqlalchemy import (
    String,
    Integer,
    Boolean,
    Enum,
    JSON,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class RoomType(str, enum.Enum):
    LECTURE_HALL = "LECTURE_HALL"
    CLASSROOM = "CLASSROOM"
    COMPUTER_LAB = "COMPUTER_LAB"
    SCIENCE_LAB = "SCIENCE_LAB"
    SEMINAR_ROOM = "SEMINAR_ROOM"


class Building(Base, TimestampMixin):
    """Campus building entity."""
    __tablename__ = "buildings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    institution = relationship("Institution", back_populates="buildings")
    rooms = relationship("Room", back_populates="building", cascade="all, delete-orphan", overlaps="institution,rooms")

    __table_args__ = (
        UniqueConstraint("institution_id", "code", name="uq_buildings_tenant_code"),
        UniqueConstraint("id", "institution_id", name="uq_buildings_id_tenant"),
    )


class Room(Base, TimestampMixin):
    """Room physical facility.
    Crucially distinguishes overall physical capacity from usable examination benches.
    """
    __tablename__ = "rooms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    building_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    room_number: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    room_type: Mapped[RoomType] = mapped_column(Enum(RoomType), default=RoomType.CLASSROOM, nullable=False)
    physical_capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    usable_exam_benches: Mapped[int] = mapped_column(Integer, nullable=False)
    grid_rows: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    grid_cols: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    building = relationship("Building", back_populates="rooms", overlaps="institution,rooms")
    institution = relationship("Institution", back_populates="rooms", overlaps="building,rooms")
    seats = relationship("Seat", back_populates="room", cascade="all, delete-orphan", overlaps="room")
    workstations = relationship("Workstation", back_populates="room", cascade="all, delete-orphan", overlaps="room")
    sessions = relationship("Session", back_populates="room", overlaps="primary_teacher,section,sessions")

    __table_args__ = (
        UniqueConstraint("institution_id", "building_id", "room_number", name="uq_rooms_tenant_bldg_room"),
        UniqueConstraint("id", "institution_id", name="uq_rooms_id_tenant"),
        ForeignKeyConstraint(["building_id", "institution_id"], ["buildings.id", "buildings.institution_id"], ondelete="CASCADE"),
    )


class Seat(Base, TimestampMixin):
    """Physical theory examination bench / desk.
    Distinguished from practical workstations. Supports usable, blocked, and accessible states.
    """
    __tablename__ = "seats"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    room_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    row_num: Mapped[int] = mapped_column(Integer, nullable=False)
    col_num: Mapped[int] = mapped_column(Integer, nullable=False)
    bench_label: Mapped[str] = mapped_column(String(50), nullable=False)
    is_usable_for_exam: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_accessible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    room = relationship("Room", back_populates="seats", overlaps="room")

    __table_args__ = (
        UniqueConstraint("institution_id", "room_id", "row_num", "col_num", name="uq_seats_tenant_room_row_col"),
        UniqueConstraint("institution_id", "room_id", "bench_label", name="uq_seats_tenant_room_bench_label"),
        UniqueConstraint("id", "institution_id", name="uq_seats_id_tenant"),
        ForeignKeyConstraint(["room_id", "institution_id"], ["rooms.id", "rooms.institution_id"], ondelete="CASCADE"),
    )


class Workstation(Base, TimestampMixin):
    """Practical laboratory terminal / bench with specialized hardware and software features."""
    __tablename__ = "workstations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    room_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    workstation_number: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(50), nullable=False)
    has_computer: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    operating_system: Mapped[str] = mapped_column(String(100), nullable=True)
    features: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_accessible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    room = relationship("Room", back_populates="workstations", overlaps="room")

    __table_args__ = (
        UniqueConstraint("institution_id", "room_id", "workstation_number", name="uq_workstations_tenant_room_wsnum"),
        UniqueConstraint("institution_id", "room_id", "label", name="uq_workstations_tenant_room_label"),
        UniqueConstraint("id", "institution_id", name="uq_workstations_id_tenant"),
        ForeignKeyConstraint(["room_id", "institution_id"], ["rooms.id", "rooms.institution_id"], ondelete="CASCADE"),
    )