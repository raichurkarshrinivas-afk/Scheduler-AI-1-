from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import login_rate_limiter
from app.core.security import (
    dummy_verify_password,
    generate_csrf_token,
    generate_session_token,
    generate_temporary_password,
    hash_password,
    hash_session_token,
    validate_password_strength,
    verify_password,
)
from app.api.deps import (
    get_current_membership,
    get_current_session,
    get_current_user,
    require_roles,
    verify_csrf_token,
    verify_student_ownership,
)
from app.models.institution import Institution
from app.models.user import User, Membership, UserRole, UserSession
from app.models.people import Teacher, Student
from app.models.audit import AuditEvent
from app.schemas.auth import (
    AdminResetPasswordRequest,
    AdminResetPasswordResponse,
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    SessionItem,
    UserProfile,
)

router = APIRouter(prefix="", tags=["Authentication & Authorisation"])


@router.post("/auth/login", response_model=LoginResponse)
def login(
    req: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """
    Authenticates a user against an institution code and identifier (Email, Teacher ID, or Student PRN).
    Enforces rate limiting, generic timing-resistant failure messages, session rotation,
    and returns HttpOnly session + CSRF cookies.
    """
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"login:{client_ip}:{req.institution_code.strip().upper()}:{req.identifier.strip().lower()}"

    # Rate limiting enforcement
    allowed, remaining, retry_after = login_rate_limiter.is_allowed(
        rate_key,
        settings.RATE_LIMIT_LOGIN_MAX_ATTEMPTS,
        settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Please retry after {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )

    # 1. Lookup institution by code
    inst = (
        db.query(Institution)
        .filter(
            Institution.code == req.institution_code.strip().upper(),
            Institution.is_active.is_(True),
        )
        .first()
    )
    if not inst:
        dummy_verify_password(req.password)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    # 2. Resolve user within this institution
    identifier_clean = req.identifier.strip()
    user = None

    # Try direct email lookup
    candidate_user = db.query(User).filter(User.email == identifier_clean.lower()).first()
    if candidate_user:
        membership_check = (
            db.query(Membership)
            .filter(
                Membership.user_id == candidate_user.id,
                Membership.institution_id == inst.id,
                Membership.is_active.is_(True),
            )
            .first()
        )
        if membership_check:
            user = candidate_user

    # If not found by email, try Teacher Employee ID
    if not user:
        teacher = (
            db.query(Teacher)
            .filter(
                Teacher.institution_id == inst.id,
                Teacher.employee_id == identifier_clean,
            )
            .first()
        )
        if teacher:
            user = db.query(User).filter(User.id == teacher.user_id).first()

    # If not found, try Student Roll Number / ID Number (PRN)
    if not user:
        student = (
            db.query(Student)
            .filter(
                Student.institution_id == inst.id,
                Student.student_id_number == identifier_clean,
            )
            .first()
        )
        if student:
            user = db.query(User).filter(User.id == student.user_id).first()

    if not user or not user.is_active:
        dummy_verify_password(req.password)
        db.add(AuditEvent(
            institution_id=inst.id,
            user_id=None,
            event_type="AUTH",
            entity_type="user",
            entity_id=None,
            action="LOGIN_FAILED",
            ip_address=client_ip,
            payload={"identifier": req.identifier, "reason": "user_not_found"},
        ))
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    # 3. Verify institution membership
    membership = (
        db.query(Membership)
        .filter(
            Membership.user_id == user.id,
            Membership.institution_id == inst.id,
            Membership.is_active.is_(True),
        )
        .first()
    )
    if not membership:
        dummy_verify_password(req.password)
        db.add(AuditEvent(
            institution_id=inst.id,
            user_id=user.id,
            event_type="AUTH",
            entity_type="membership",
            entity_id=None,
            action="LOGIN_FAILED",
            ip_address=client_ip,
            payload={"identifier": req.identifier, "reason": "no_active_membership"},
        ))
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    # 4. Verify password with Argon2id
    if not verify_password(req.password, user.hashed_password):
        db.add(AuditEvent(
            institution_id=inst.id,
            user_id=user.id,
            event_type="AUTH",
            entity_type="user",
            entity_id=user.id,
            action="LOGIN_FAILED",
            ip_address=client_ip,
            payload={"identifier": req.identifier, "reason": "password_mismatch"},
        ))
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    # Success: reset rate limit attempts
    login_rate_limiter.reset(rate_key)

    # 5. Session Rotation: invalidate existing session if present
    existing_cookie = request.cookies.get(settings.SESSION_COOKIE_NAME)
    now = datetime.now(timezone.utc)
    if existing_cookie:
        old_hash = hash_session_token(existing_cookie)
        db.query(UserSession).filter(
            UserSession.session_token_hash == old_hash,
            UserSession.revoked_at.is_(None),
        ).update({"revoked_at": now})

    # 6. Issue fresh session token and CSRF token
    raw_token, token_hash = generate_session_token()
    csrf_token = generate_csrf_token()
    expires_at = now + timedelta(seconds=settings.SESSION_EXPIRE_SECONDS)

    user_agent = request.headers.get("user-agent")
    user_agent_clean = user_agent[:500] if user_agent else None

    session_rec = UserSession(
        session_token_hash=token_hash,
        user_id=user.id,
        institution_id=inst.id,
        csrf_token=csrf_token,
        ip_address=client_ip,
        user_agent=user_agent_clean,
        expires_at=expires_at,
        last_activity_at=now,
    )
    db.add(session_rec)

    # 7. Audit successful login
    db.add(AuditEvent(
        institution_id=inst.id,
        user_id=user.id,
        event_type="AUTH",
        entity_type="user_session",
        entity_id=session_rec.id,
        action="LOGIN_SUCCESS",
        ip_address=client_ip,
        payload={"identifier": req.identifier, "role": membership.role.value},
    ))
    db.commit()

    # 8. Set HttpOnly session cookie and readable CSRF cookie
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.SESSION_EXPIRE_SECONDS,
        path="/",
    )
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.SESSION_EXPIRE_SECONDS,
        path="/",
    )

    # Resolve optional teacher or student profile IDs
    teacher_prof = db.query(Teacher).filter(Teacher.user_id == user.id, Teacher.institution_id == inst.id).first()
    student_prof = db.query(Student).filter(Student.user_id == user.id, Student.institution_id == inst.id).first()

    profile = UserProfile(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        must_change_password=user.must_change_password,
        role=membership.role,
        institution_id=inst.id,
        institution_name=inst.name,
        institution_code=inst.code,
        teacher_id=teacher_prof.id if teacher_prof else None,
        student_id=student_prof.id if student_prof else None,
        employee_id=teacher_prof.employee_id if teacher_prof else None,
        roll_number=student_prof.roll_number if student_prof else None,
    )

    return LoginResponse(
        user=profile,
        csrf_token=csrf_token,
        must_change_password=user.must_change_password,
        message="Login successful.",
    )


@router.post("/auth/logout")
def logout(
    request: Request,
    response: Response,
    session: UserSession = Depends(get_current_session),
    _csrf: None = Depends(verify_csrf_token),
    db: Session = Depends(get_db),
) -> dict:
    """Invalidates the current session and clears browser cookies."""
    now = datetime.now(timezone.utc)
    session.revoked_at = now

    client_ip = request.client.host if request.client else None
    db.add(AuditEvent(
        institution_id=session.institution_id,
        user_id=session.user_id,
        event_type="AUTH",
        entity_type="user_session",
        entity_id=session.id,
        action="LOGOUT",
        ip_address=client_ip,
        payload={},
    ))
    db.commit()

    response.delete_cookie(key=settings.SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(key=settings.CSRF_COOKIE_NAME, path="/")
    return {"detail": "Successfully logged out."}


@router.post("/auth/change-password")
def change_password(
    req: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    session: UserSession = Depends(get_current_session),
    _csrf: None = Depends(verify_csrf_token),
    db: Session = Depends(get_db),
) -> dict:
    """
    Changes password for the currently logged-in user.
    Validates current password, enforces password complexity, sets must_change_password=False,
    and invalidates all OTHER active sessions for the user.
    """
    if not verify_password(req.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    ok, err_msg = validate_password_strength(req.new_password)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg,
        )

    now = datetime.now(timezone.utc)
    user.hashed_password = hash_password(req.new_password)
    user.must_change_password = False

    # Invalidate all other sessions for this user (session rotation / security reset)
    db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.id != session.id,
        UserSession.revoked_at.is_(None),
    ).update({"revoked_at": now})

    db.add(AuditEvent(
        institution_id=session.institution_id,
        user_id=user.id,
        event_type="AUTH",
        entity_type="user",
        entity_id=user.id,
        action="PASSWORD_CHANGE",
        ip_address=session.ip_address,
        payload={"self_initiated": True},
    ))
    db.commit()

    return {"detail": "Password successfully changed."}


@router.get("/me", response_model=UserProfile)
def get_current_profile(
    user: User = Depends(get_current_user),
    membership: Membership = Depends(get_current_membership),
    session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> UserProfile:
    """Returns the authenticated user's profile and institutional scope."""
    inst = db.query(Institution).filter(Institution.id == session.institution_id).first()
    teacher_prof = db.query(Teacher).filter(Teacher.user_id == user.id, Teacher.institution_id == session.institution_id).first()
    student_prof = db.query(Student).filter(Student.user_id == user.id, Student.institution_id == session.institution_id).first()

    return UserProfile(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        must_change_password=user.must_change_password,
        role=membership.role,
        institution_id=inst.id if inst else session.institution_id,
        institution_name=inst.name if inst else "",
        institution_code=inst.code if inst else "",
        teacher_id=teacher_prof.id if teacher_prof else None,
        student_id=student_prof.id if student_prof else None,
        employee_id=teacher_prof.employee_id if teacher_prof else None,
        roll_number=student_prof.roll_number if student_prof else None,
    )


@router.get("/me/sessions", response_model=List[SessionItem])
def list_my_sessions(
    user: User = Depends(get_current_user),
    session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> List[SessionItem]:
    """Lists all active browser sessions for the current user."""
    now = datetime.now(timezone.utc)
    active_sessions = (
        db.query(UserSession)
        .filter(
            UserSession.user_id == user.id,
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
        )
        .order_by(UserSession.last_activity_at.desc())
        .all()
    )

    result = []
    for s in active_sessions:
        result.append(
            SessionItem(
                id=s.id,
                ip_address=s.ip_address,
                user_agent=s.user_agent,
                created_at=s.created_at,
                last_activity_at=s.last_activity_at,
                expires_at=s.expires_at,
                is_current=(s.id == session.id),
            )
        )
    return result


@router.delete("/me/sessions/{id}")
def revoke_my_session(
    id: str,
    response: Response,
    user: User = Depends(get_current_user),
    session: UserSession = Depends(get_current_session),
    _csrf: None = Depends(verify_csrf_token),
    db: Session = Depends(get_db),
) -> dict:
    """Revokes a specific session belonging to the current user."""
    target_session = (
        db.query(UserSession)
        .filter(
            UserSession.id == id,
            UserSession.user_id == user.id,
            UserSession.revoked_at.is_(None),
        )
        .first()
    )
    if not target_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or already revoked.",
        )

    now = datetime.now(timezone.utc)
    target_session.revoked_at = now

    db.add(AuditEvent(
        institution_id=session.institution_id,
        user_id=user.id,
        event_type="AUTH",
        entity_type="user_session",
        entity_id=id,
        action="SESSION_REVOKED",
        ip_address=session.ip_address,
        payload={"revoked_by": "self"},
    ))
    db.commit()

    if id == session.id:
        response.delete_cookie(key=settings.SESSION_COOKIE_NAME, path="/")
        response.delete_cookie(key=settings.CSRF_COOKIE_NAME, path="/")

    return {"detail": "Session revoked."}


@router.post("/admin/users/{id}/reset-password", response_model=AdminResetPasswordResponse)
def admin_reset_password(
    id: str,
    req: AdminResetPasswordRequest,
    admin_user: User = Depends(get_current_user),
    admin_membership: Membership = Depends(require_roles(UserRole.INSTITUTION_ADMINISTRATOR)),
    session: UserSession = Depends(get_current_session),
    _csrf: None = Depends(verify_csrf_token),
    db: Session = Depends(get_db),
) -> AdminResetPasswordResponse:
    """
    Administrative reset workflow for institution administrators.
    - Verified against admin's institution boundary (cross-tenant reset rejected).
    - Cannot grant or modify platform-wide superuser privileges.
    - Generates or applies temporary password.
    - Forces user to change password on next login (must_change_password = True).
    - Immediately revokes all active sessions for that user.
    """
    # 1. Verify target user has membership in THIS administrator's institution
    target_membership = (
        db.query(Membership)
        .filter(
            Membership.user_id == id,
            Membership.institution_id == admin_membership.institution_id,
        )
        .first()
    )
    if not target_membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in your institution.",
        )

    target_user = db.query(User).filter(User.id == id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    # Safeguard: institution administrators cannot manage superusers
    if target_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Institution administrators cannot reset credentials for platform administrators.",
        )

    # 2. Determine temporary password
    temp_pwd = req.temporary_password.strip() if req.temporary_password else generate_temporary_password()
    ok, err_msg = validate_password_strength(temp_pwd)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_msg,
        )

    # 3. Update user and mark must_change_password = True
    now = datetime.now(timezone.utc)
    target_user.hashed_password = hash_password(temp_pwd)
    target_user.must_change_password = True

    # 4. Revoke all active sessions for the target user immediately
    db.query(UserSession).filter(
        UserSession.user_id == target_user.id,
        UserSession.revoked_at.is_(None),
    ).update({"revoked_at": now})

    # 5. Audited without recording the plaintext temporary password
    db.add(AuditEvent(
        institution_id=admin_membership.institution_id,
        user_id=admin_user.id,
        event_type="AUTH",
        entity_type="user",
        entity_id=target_user.id,
        action="PASSWORD_RESET_ADMIN",
        ip_address=session.ip_address,
        payload={"target_email": target_user.email, "forced_change": True},
    ))
    db.commit()

    return AdminResetPasswordResponse(
        user_id=target_user.id,
        temporary_password=temp_pwd,
        must_change_password=True,
        message="Password successfully reset. Temporary credentials generated.",
    )


@router.get("/students/{id}")
def get_student_record(
    id: str,
    membership: Membership = Depends(require_roles(
        UserRole.STUDENT,
        UserRole.TEACHER,
        UserRole.TIMETABLE_COORDINATOR,
        UserRole.EXAM_CONTROLLER,
        UserRole.INSTITUTION_ADMINISTRATOR,
    )),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """
    Student record access endpoint used to test student-level ownership isolation,
    forced password change enforcement, and cross-tenant rejection.
    """
    student = verify_student_ownership(id, membership, user, db)
    return {
        "id": student.id,
        "roll_number": student.roll_number,
        "batch_year": student.batch_year,
        "department_id": student.department_id,
        "institution_id": student.institution_id,
    }
