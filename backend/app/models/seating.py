import uuid
import enum
from sqlalchemy import Column, String, Date, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class ExamStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SEATS_ALLOCATED = "SEATS_ALLOCATED"
    COMPLETED = "COMPLETED"


class ExamSession(Base):
    __tablename__ = "exam_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_term_id = Column(String(36), ForeignKey("academic_terms.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    exam_date = Column(Date, nullable=False)
    time_slot_id = Column(String(36), ForeignKey("time_slots.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), default=ExamStatus.DRAFT.value, nullable=False)

    institution = relationship("Institution", back_populates="exam_sessions")
    academic_term = relationship("AcademicTerm", back_populates="exam_sessions")
    time_slot = relationship("TimeSlot", back_populates="exam_sessions")
    enrollments = relationship("ExamEnrollment", back_populates="exam_session", cascade="all, delete-orphan")
    seat_assignments = relationship("SeatAssignment", back_populates="exam_session", cascade="all, delete-orphan")


class ExamEnrollment(Base):
    __tablename__ = "exam_enrollments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    exam_session_id = Column(String(36), ForeignKey("exam_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(String(36), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)

    exam_session = relationship("ExamSession", back_populates="enrollments")
    student = relationship("User", back_populates="exam_enrollments")
    course = relationship("Course", back_populates="exam_enrollments")


class SeatAssignment(Base):
    __tablename__ = "seat_assignments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    exam_session_id = Column(String(36), ForeignKey("exam_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    classroom_id = Column(String(36), ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(String(36), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    seat_row = Column(Integer, nullable=False)  # 0-indexed row
    seat_col = Column(Integer, nullable=False)  # 0-indexed column
    desk_label = Column(String(50), nullable=False)  # e.g. "Hall-101-R1-C2"

    exam_session = relationship("ExamSession", back_populates="seat_assignments")
    classroom = relationship("Classroom", back_populates="seat_assignments")
    student = relationship("User", back_populates="seat_assignments")
    course = relationship("Course", back_populates="seat_assignments")
