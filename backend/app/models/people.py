import uuid
from sqlalchemy import (
    String,
    Integer,
    Boolean,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class Teacher(Base, TimestampMixin):
    """Institutional faculty member profile."""
    __tablename__ = "teachers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    department_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
    employee_id: Mapped[str] = mapped_column(String(50), nullable=False)
    designation: Mapped[str] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="teacher_profiles")
    qualifications = relationship("TeacherQualification", back_populates="teacher", cascade="all, delete-orphan", overlaps="qualifications,subject")
    assigned_sessions = relationship("Session", back_populates="primary_teacher", overlaps="assigned_sessions,room,section,sessions")
    availability_rules = relationship("AvailabilityRule", back_populates="teacher", cascade="all, delete-orphan", overlaps="teacher")

    __table_args__ = (
        UniqueConstraint("institution_id", "user_id", name="uq_teachers_tenant_user"),
        UniqueConstraint("institution_id", "employee_id", name="uq_teachers_tenant_emp_id"),
        UniqueConstraint("id", "institution_id", name="uq_teachers_id_tenant"),
        ForeignKeyConstraint(["department_id", "institution_id"], ["departments.id", "departments.institution_id"], ondelete="SET NULL"),
    )


class Student(Base, TimestampMixin):
    """Institutional student profile."""
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    department_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)
    student_id_number: Mapped[str] = mapped_column(String(50), nullable=False)
    admission_year: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="student_profiles")
    enrolments = relationship("Enrolment", back_populates="student", cascade="all, delete-orphan", overlaps="enrolments,section")

    @hybrid_property
    def roll_number(self) -> str:
        return self.student_id_number

    @roll_number.setter
    def roll_number(self, val: str) -> None:
        self.student_id_number = val

    @hybrid_property
    def batch_year(self) -> int:
        return self.admission_year

    @batch_year.setter
    def batch_year(self, val: int) -> None:
        self.admission_year = val

    __table_args__ = (
        UniqueConstraint("institution_id", "user_id", name="uq_students_tenant_user"),
        UniqueConstraint("institution_id", "student_id_number", name="uq_students_tenant_sid"),
        UniqueConstraint("id", "institution_id", name="uq_students_id_tenant"),
        ForeignKeyConstraint(["department_id", "institution_id"], ["departments.id", "departments.institution_id"], ondelete="SET NULL"),
    )


class TeacherQualification(Base, TimestampMixin):
    """Explicit model of instructor eligibility to teach subjects,
    strictly decoupled from actual operational session assignments.
    """
    __tablename__ = "teacher_qualifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    teacher_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    subject_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    teacher = relationship("Teacher", back_populates="qualifications", overlaps="qualifications,subject")
    subject = relationship("Subject", overlaps="qualifications,teacher")

    __table_args__ = (
        UniqueConstraint("institution_id", "teacher_id", "subject_id", name="uq_tqual_tenant_teacher_subject"),
        ForeignKeyConstraint(["teacher_id", "institution_id"], ["teachers.id", "teachers.institution_id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["subject_id", "institution_id"], ["subjects.id", "subjects.institution_id"], ondelete="CASCADE"),
    )
