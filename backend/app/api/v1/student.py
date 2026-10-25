from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import (
    get_current_membership,
    get_current_user,
    get_current_session,
    require_roles,
    verify_csrf_token,
)
from app.models.user import UserRole, Membership, User, UserSession
from app.models.people import Student
from app.schemas.auth import ChangePasswordRequest
from app.schemas.student import (
    StudentProfileOut,
    StudentTimetableResponse,
    StudentExamSeatOut,
    StudentPracticalOut,
    StudentChangeNoticeOut,
    StudentHomeOut,
)
from app.services.student_service import StudentService
from app.core.security import verify_password, get_password_hash

router = APIRouter(prefix="/student", tags=["Student Portal"])


@router.get("/me", response_model=StudentProfileOut)
def get_student_profile(
    membership: Membership = Depends(require_roles(UserRole.STUDENT)),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns student profile information.
    Identity is strictly derived from the authenticated session.
    """
    student, _ = StudentService.get_student_for_user(db, user.id, membership.institution_id)
    return StudentService.get_profile(student, user)


@router.get("/home", response_model=StudentHomeOut)
def get_student_home(
    membership: Membership = Depends(require_roles(UserRole.STUDENT)),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Assembles home view for the authenticated student:
    - Next-up session (current timezone calculated)
    - Today's occurrences
    - Upcoming exams with exact seat details
    - Practical workstations and batches
    - Recent publication notices
    """
    student, _ = StudentService.get_student_for_user(db, user.id, membership.institution_id)
    return StudentService.get_home(db, student, user)


@router.get("/timetable", response_model=StudentTimetableResponse)
def get_student_timetable(
    week_start_date: Optional[str] = Query(None),
    membership: Membership = Depends(require_roles(UserRole.STUDENT)),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns server-derived dated occurrences for the student's enrolled sections.
    ONLY reads from active published timetables (never from drafts!).
    Consistently handles term timezone and calendar exceptions.
    """
    student, _ = StudentService.get_student_for_user(db, user.id, membership.institution_id)
    return StudentService.get_timetable(db, student, week_start_str=week_start_date)


@router.get("/exams", response_model=List[StudentExamSeatOut])
def get_student_exams(
    membership: Membership = Depends(require_roles(UserRole.STUDENT)),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns upcoming published theory examinations with EXACT SEAT DETAILS
    (hall name, bench label, row, column, accessibility accommodation).
    Identity is strictly session-derived; never reveals other candidates' seats.
    """
    student, _ = StudentService.get_student_for_user(db, user.id, membership.institution_id)
    return StudentService.get_exams(db, student)


@router.get("/practicals", response_model=List[StudentPracticalOut])
def get_student_practicals(
    membership: Membership = Depends(require_roles(UserRole.STUDENT)),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns published practical lab workstations, batch schedule, and turnaround buffers.
    """
    student, _ = StudentService.get_student_for_user(db, user.id, membership.institution_id)
    return StudentService.get_practicals(db, student)


@router.get("/recent-changes", response_model=List[StudentChangeNoticeOut])
def get_student_recent_changes(
    membership: Membership = Depends(require_roles(UserRole.STUDENT)),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns official release notes and change logs from recent publications.
    """
    student, _ = StudentService.get_student_for_user(db, user.id, membership.institution_id)
    return StudentService.get_recent_changes(db, student)


@router.post("/change-password")
def student_change_password(
    req: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    session: UserSession = Depends(get_current_session),
    _csrf: None = Depends(verify_csrf_token),
    db: Session = Depends(get_db),
):
    """
    Changes student password using Phase 3 authentication security:
    Validates current password with Argon2id, updates hash, and revokes other sessions.
    """
    if not verify_password(req.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password verification failed.",
        )

    user.hashed_password = get_password_hash(req.new_password)
    user.must_change_password = False

    # Invalidate other active sessions
    db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.id != session.id,
        UserSession.is_revoked == False,
    ).update({"is_revoked": True})

    db.commit()
    return {"message": "Password changed successfully."}
