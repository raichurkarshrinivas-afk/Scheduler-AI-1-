import uuid
import enum
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class CourseType(str, enum.Enum):
    LECTURE = "LECTURE"
    LAB = "LAB"


class Course(Base):
    __tablename__ = "courses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id = Column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    department_id = Column(String(36), ForeignKey("departments.id", ondelete="CASCADE"), nullable=False, index=True)
    code = Column(String(50), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    weekly_hours = Column(Integer, default=3, nullable=False)
    course_type = Column(String(50), default=CourseType.LECTURE.value, nullable=False)

    institution = relationship("Institution", back_populates="courses")
    department = relationship("Department", back_populates="courses")
    schedule_sessions = relationship("ScheduleSession", back_populates="course", cascade="all, delete-orphan")
    exam_enrollments = relationship("ExamEnrollment", back_populates="course", cascade="all, delete-orphan")
    seat_assignments = relationship("SeatAssignment", back_populates="course")
