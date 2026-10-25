from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_institution, require_role, get_current_user
from app.models.course import Course
from app.models.academic import Department
from app.models.user import User, UserRole
from app.models.instructor import InstructorAvailability
from app.schemas.course import (
    CourseCreate,
    CourseOut,
    InstructorAvailabilityCreate,
    InstructorAvailabilityOut,
)
from app.schemas.auth import UserOut

router = APIRouter(prefix="/courses", tags=["Courses & Instructors"])


@router.get("", response_model=List[CourseOut])
def list_courses(inst_id: str = Depends(require_institution), db: Session = Depends(get_db)):
    return db.query(Course).filter(Course.institution_id == inst_id).all()


@router.post("", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
def create_course(
    payload: CourseCreate,
    inst_id: str = Depends(require_institution),
    current_user: User = Depends(require_role([UserRole.ADMIN.value, UserRole.SUPERADMIN.value])),
    db: Session = Depends(get_db)
):
    dept = db.query(Department).filter(
        Department.id == payload.department_id,
        Department.institution_id == inst_id
    ).first()
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    course = Course(
        institution_id=inst_id,
        department_id=payload.department_id,
        code=payload.code.upper(),
        name=payload.name,
        weekly_hours=payload.weekly_hours,
        course_type=payload.course_type
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.get("/instructors", response_model=List[UserOut])
def list_instructors(inst_id: str = Depends(require_institution), db: Session = Depends(get_db)):
    users = db.query(User).filter(
        User.institution_id == inst_id,
        User.role.in_([UserRole.INSTRUCTOR.value, UserRole.ADMIN.value]),
        User.is_active == True
    ).all()
    return [
        UserOut(
            id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            institution_id=u.institution_id,
            institution_name=None,
            is_active=u.is_active
        )
        for u in users
    ]


@router.get("/instructors/{instructor_id}/unavailability", response_model=List[InstructorAvailabilityOut])
def list_instructor_unavailability(
    instructor_id: str,
    inst_id: str = Depends(require_institution),
    db: Session = Depends(get_db)
):
    return db.query(InstructorAvailability).filter(
        InstructorAvailability.institution_id == inst_id,
        InstructorAvailability.instructor_id == instructor_id
    ).all()


@router.post("/instructors/unavailability", response_model=InstructorAvailabilityOut, status_code=status.HTTP_201_CREATED)
def set_instructor_unavailability(
    payload: InstructorAvailabilityCreate,
    inst_id: str = Depends(require_institution),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Instructors can configure their own availability; Admins can configure for anyone
    if current_user.role not in [UserRole.ADMIN.value, UserRole.SUPERADMIN.value]:
        if current_user.id != payload.instructor_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot alter another instructor's availability")

    avail = InstructorAvailability(
        institution_id=inst_id,
        instructor_id=payload.instructor_id,
        day_of_week=payload.day_of_week,
        time_slot_id=payload.time_slot_id,
        is_available=payload.is_available,
        reason=payload.reason
    )
    db.add(avail)
    db.commit()
    db.refresh(avail)
    return avail
