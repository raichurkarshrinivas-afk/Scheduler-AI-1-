from datetime import datetime, timezone
from typing import Callable, List, Optional
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import hash_session_token
from app.models.user import User, Membership, UserRole, UserSession
from app.models.people import Student


def get_current_session(
    request: Request,
    db: Session = Depends(get_db),
) -> UserSession:
    """
    Extracts raw session token from HttpOnly cookie (or Authorization header fallback),
    hashes it via SHA-256, and retrieves the active UserSession.
    """
    raw_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    
    # Fallback to Authorization: Session <token> or Bearer <token>
    if not raw_token:
        auth_header = request.headers.get("Authorization")
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() in ("session", "bearer"):
                raw_token = parts[1]

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication session required.",
            headers={"WWW-Authenticate": "Cookie"},
        )

    token_hash = hash_session_token(raw_token)
    now = datetime.now(timezone.utc)

    db_session = (
        db.query(UserSession)
        .filter(
            UserSession.session_token_hash == token_hash,
            UserSession.revoked_at.is_(None),
        )
        .first()
    )

    if not db_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked session.",
        )

    # Check expiration
    expires_at = db_session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please log in again.",
        )

    # Update activity timestamp
    db_session.last_activity_at = now
    db.commit()

    return db_session


def get_current_user(
    session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> User:
    """Retrieves the global User associated with the active session."""
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated or unavailable.",
        )
    return user


def get_current_membership(
    session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> Membership:
    """Retrieves the active institutional membership for the current session."""
    membership = (
        db.query(Membership)
        .filter(
            Membership.user_id == session.user_id,
            Membership.institution_id == session.institution_id,
            Membership.is_active.is_(True),
        )
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have an active membership in the current institution.",
        )
    return membership


def require_roles(*allowed_roles: UserRole) -> Callable:
    """
    Dependency factory enforcing role-based permissions and checking
    that forced password change is completed.
    """
    def role_dependency(
        user: User = Depends(get_current_user),
        membership: Membership = Depends(get_current_membership),
    ) -> Membership:
        if user.must_change_password:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Password change required before accessing system resources.",
                headers={"X-Error-Code": "PASSWORD_CHANGE_REQUIRED"},
            )
        if membership.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of the following roles: {[r.value for r in allowed_roles]}",
            )
        return membership

    return role_dependency


def verify_csrf_token(
    request: Request,
    session: UserSession = Depends(get_current_session),
) -> None:
    """
    Enforces Double-Submit / Header CSRF token validation on state-changing requests.
    Validates X-CSRF-Token header against the cryptographically generated token
    bound to the session.
    """
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        csrf_header = request.headers.get("X-CSRF-Token") or request.headers.get("x-csrf-token")
        if not csrf_header or csrf_header != session.csrf_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF validation failed or token missing.",
            )


def verify_institution_ownership(
    target_institution_id: str,
    membership: Membership,
) -> None:
    """Ensures an entity belongs to the user's active institutional tenant."""
    if target_institution_id != membership.institution_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found.",
        )


def verify_student_ownership(
    student_id: str,
    membership: Membership,
    current_user: User,
    db: Session,
) -> Student:
    """
    Ensures that if the requester is a Student, they can only view or modify
    their own student record. Rejects cross-student access with 403 Forbidden.
    """
    student = (
        db.query(Student)
        .filter(
            Student.id == student_id,
            Student.institution_id == membership.institution_id,
        )
        .first()
    )
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student record not found.",
        )

    if membership.role == UserRole.STUDENT and student.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Students may only access their own educational records.",
        )

    return student
