import enum
import uuid
from datetime import date
from sqlalchemy import (
    String,
    Integer,
    Boolean,
    Date,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class SubjectType(str, enum.Enum):
    THEORY = "THEORY"
    PRACTICAL = "PRACTICAL"
    HYBRID = "HYBRID"


class EnrolmentStatus(str, enum.Enum):
    ENROLLED = "ENROLLED"
    DROPPED = "DROPPED"
    AUDIT = "AUDIT"
    COMPLETED = "COMPLETED"


class Department(Base, TimestampMixin):
    """Academic department within an institution."""
    __tablename__ = "departments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    institution = relationship("Institution", back_populates="departments")
    subjects = relationship("Subject", back_populates="department", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("institution_id", "code", name="uq_departments_tenant_code"),
        UniqueConstraint("id", "institution_id", name="uq_departments_id_tenant"),
    )


class AcademicTerm(Base, TimestampMixin):
    """Academic semester/term boundary with explicit IANA timezone."""
    __tablename__ = "academic_terms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    institution = relationship("Institution", back_populates="academic_terms")
    course_offerings = relationship("CourseOffering", back_populates="academic_term", cascade="all, delete-orphan", overlaps="course_offerings,subject")

    __table_args__ = (
        UniqueConstraint("institution_id", "code", name="uq_academic_terms_tenant_code"),
        UniqueConstraint("id", "institution_id", name="uq_academic_terms_id_tenant"),
    )


class Subject(Base, TimestampMixin):
    """Curriculum subject/course definition."""
    __tablename__ = "subjects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    department_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject_type: Mapped[SubjectType] = mapped_column(Enum(SubjectType), default=SubjectType.THEORY, nullable=False)
    weekly_lecture_hours: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    weekly_lab_hours: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    credits: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    department = relationship("Department", back_populates="subjects")
    course_offerings = relationship("CourseOffering", back_populates="subject", cascade="all, delete-orphan", overlaps="academic_term,course_offerings")

    __table_args__ = (
        UniqueConstraint("institution_id", "code", name="uq_subjects_tenant_code"),
        UniqueConstraint("id", "institution_id", name="uq_subjects_id_tenant"),
        ForeignKeyConstraint(["department_id", "institution_id"], ["departments.id", "departments.institution_id"], ondelete="CASCADE"),
    )


class CourseOffering(Base, TimestampMixin):
    """Subject offered during a specific academic term."""
    __tablename__ = "course_offerings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    academic_term_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    subject = relationship("Subject", back_populates="course_offerings", overlaps="academic_term,course_offerings")
    academic_term = relationship("AcademicTerm", back_populates="course_offerings", overlaps="course_offerings,subject")
    sections = relationship("Section", back_populates="course_offering", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("institution_id", "subject_id", "academic_term_id", name="uq_offerings_tenant_subj_term"),
        UniqueConstraint("id", "institution_id", name="uq_course_offerings_id_tenant"),
        ForeignKeyConstraint(["subject_id", "institution_id"], ["subjects.id", "subjects.institution_id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["academic_term_id", "institution_id"], ["academic_terms.id", "academic_terms.institution_id"], ondelete="CASCADE"),
    )


class Section(Base, TimestampMixin):
    """Student section/cohort container under a course offering.
    Distinguished from actual student enrolments.
    """
    __tablename__ = "sections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    course_offering_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=30)

    course_offering = relationship("CourseOffering", back_populates="sections")
    enrolments = relationship("Enrolment", back_populates="section", cascade="all, delete-orphan", overlaps="enrolments,student")
    sessions = relationship("Session", back_populates="section", overlaps="primary_teacher,room,sessions")

    __table_args__ = (
        UniqueConstraint("institution_id", "course_offering_id", "name", name="uq_sections_tenant_offering_name"),
        UniqueConstraint("id", "institution_id", name="uq_sections_id_tenant"),
        ForeignKeyConstraint(["course_offering_id", "institution_id"], ["course_offerings.id", "course_offerings.institution_id"], ondelete="CASCADE"),
    )


class Enrolment(Base, TimestampMixin):
    """Actual student enrolment in a specific section."""
    __tablename__ = "enrolments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    institution_id: Mapped[str] = mapped_column(String(36), ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    section_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[EnrolmentStatus] = mapped_column(Enum(EnrolmentStatus), default=EnrolmentStatus.ENROLLED, nullable=False)

    student = relationship("Student", back_populates="enrolments", overlaps="enrolments,section")
    section = relationship("Section", back_populates="enrolments", overlaps="enrolments,student")

    __table_args__ = (
        UniqueConstraint("institution_id", "student_id", "section_id", name="uq_enrolments_tenant_student_section"),
        ForeignKeyConstraint(["student_id", "institution_id"], ["students.id", "students.institution_id"], ondelete="CASCADE"),
        ForeignKeyConstraint(["section_id", "institution_id"], ["sections.id", "sections.institution_id"], ondelete="CASCADE"),
    )