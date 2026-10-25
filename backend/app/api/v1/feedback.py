import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_membership, require_roles
from app.models.user import User, UserRole, Membership
from app.models.feedback import FeedbackSubmission, FeedbackInternalNote
from app.schemas.feedback import (
    PublicContactCreate,
    PublicContactResponse,
    AuthenticatedFeedbackCreate,
    FeedbackSubmissionUserResponse,
    FeedbackSubmissionManageResponse,
    FeedbackManageListResponse,
    FeedbackStatusUpdate,
    FeedbackInternalNoteCreate,
    FeedbackInternalNoteResponse,
)
from app.services.feedback_service import FeedbackService

logger = logging.getLogger("api_feedback")
router = APIRouter()


# ==========================================
# Workflow A: Public Contact & Feedback
# ==========================================

@router.post("/public", response_model=PublicContactResponse)
def submit_public_contact(
    payload: PublicContactCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Public contact/feedback endpoint.
    - Optional name & email.
    - Honeypot bot protection.
    - Server-side field and size validation.
    - Rate limits per IP.
    - Generic confirmation that does not expose internal database structures.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()

    result = FeedbackService.submit_public_feedback(
        db=db,
        subject=payload.subject,
        message=payload.message,
        category=payload.category,
        contact_name=payload.contact_name,
        contact_email=payload.contact_email,
        honeypot=payload.honeypot,
        client_ip=client_ip,
    )
    return PublicContactResponse(
        success=result["success"],
        reference_code=result["reference_code"],
        message=result["message"],
    )


# ==========================================
# Workflow B: Authenticated Feedback
# ==========================================

@router.post("/submit", response_model=FeedbackSubmissionUserResponse)
def submit_authenticated_feedback(
    payload: AuthenticatedFeedbackCreate,
    current_user: User = Depends(get_current_user),
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    """
    Authenticated feedback deriving user and institution strictly from the active session.
    Never exposes internal reviewer notes.
    """
    submission = FeedbackService.submit_authenticated_feedback(
        db=db,
        current_user=current_user,
        membership=membership,
        category=payload.category,
        subject=payload.subject,
        message=payload.message,
        page_reference=payload.page_reference,
    )
    return FeedbackSubmissionUserResponse.model_validate(submission)


@router.get("/my-submissions", response_model=List[FeedbackSubmissionUserResponse])
def get_my_submissions(
    current_user: User = Depends(get_current_user),
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    """
    Returns submitted feedback for the logged-in user in their current institution.
    Strictly excludes internal reviewer notes.
    """
    submissions = FeedbackService.get_user_submissions(
        db=db,
        user_id=current_user.id,
        institution_id=membership.institution_id,
    )
    return [FeedbackSubmissionUserResponse.model_validate(s) for s in submissions]


# ==========================================
# Administrative Review & Governance (Staff Only)
# ==========================================

@router.get("/manage", response_model=FeedbackManageListResponse)
def list_management_feedback(
    status_filter: Optional[str] = Query(None, alias="status"),
    category_filter: Optional[str] = Query(None, alias="category"),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    membership: Membership = Depends(
        require_roles(
            UserRole.INSTITUTION_ADMINISTRATOR,
            UserRole.TIMETABLE_COORDINATOR,
            UserRole.EXAM_CONTROLLER,
        )
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Staff review listing. Scoped to authorized institution reviewers.
    Cross-institution review is denied.
    """
    items, total = FeedbackService.list_management_feedback(
        db=db,
        reviewer=current_user,
        membership=membership,
        status_filter=status_filter,
        category_filter=category_filter,
        search_query=search,
        limit=limit,
        offset=offset,
    )

    result_items = []
    for it in items:
        notes_responses = [
            FeedbackInternalNoteResponse(
                id=n.id,
                author_user_id=n.author_user_id,
                author_name=n.author.full_name if n.author else None,
                note=n.note,
                created_at=n.created_at,
            )
            for n in (it.internal_notes or [])
        ]
        result_items.append(
            FeedbackSubmissionManageResponse(
                id=it.id,
                reference_code=it.reference_code,
                institution_id=it.institution_id,
                submitting_user_id=it.submitting_user_id,
                contact_name=it.contact_name,
                contact_email=it.contact_email,
                category=it.category,
                subject=it.subject,
                message=it.message,
                page_reference=it.page_reference,
                status=it.status,
                assigned_reviewer_id=it.assigned_reviewer_id,
                assigned_reviewer_name=it.assigned_reviewer.full_name if it.assigned_reviewer else None,
                created_at=it.created_at,
                updated_at=it.updated_at,
                internal_notes=notes_responses,
            )
        )

    return FeedbackManageListResponse(items=result_items, total=total)


@router.get("/manage/{submission_id}", response_model=FeedbackSubmissionManageResponse)
def get_management_feedback_detail(
    submission_id: str,
    membership: Membership = Depends(
        require_roles(
            UserRole.INSTITUTION_ADMINISTRATOR,
            UserRole.TIMETABLE_COORDINATOR,
            UserRole.EXAM_CONTROLLER,
        )
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Detail endpoint for review.
    Authoritatively denies cross-institution review.
    """
    it = FeedbackService.get_management_submission_by_id(db, submission_id, membership)
    notes_responses = [
        FeedbackInternalNoteResponse(
            id=n.id,
            author_user_id=n.author_user_id,
            author_name=n.author.full_name if n.author else None,
            note=n.note,
            created_at=n.created_at,
        )
        for n in (it.internal_notes or [])
    ]
    return FeedbackSubmissionManageResponse(
        id=it.id,
        reference_code=it.reference_code,
        institution_id=it.institution_id,
        submitting_user_id=it.submitting_user_id,
        contact_name=it.contact_name,
        contact_email=it.contact_email,
        category=it.category,
        subject=it.subject,
        message=it.message,
        page_reference=it.page_reference,
        status=it.status,
        assigned_reviewer_id=it.assigned_reviewer_id,
        assigned_reviewer_name=it.assigned_reviewer.full_name if it.assigned_reviewer else None,
        created_at=it.created_at,
        updated_at=it.updated_at,
        internal_notes=notes_responses,
    )


@router.patch("/manage/{submission_id}/status", response_model=FeedbackSubmissionManageResponse)
def update_feedback_status(
    submission_id: str,
    payload: FeedbackStatusUpdate,
    membership: Membership = Depends(
        require_roles(
            UserRole.INSTITUTION_ADMINISTRATOR,
            UserRole.TIMETABLE_COORDINATOR,
            UserRole.EXAM_CONTROLLER,
        )
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Updates status and assigned reviewer. Creates audit trail event.
    """
    it = FeedbackService.update_submission_status(
        db=db,
        submission_id=submission_id,
        new_status=payload.status,
        reviewer=current_user,
        membership=membership,
        assigned_reviewer_id=payload.assigned_reviewer_id,
    )
    notes_responses = [
        FeedbackInternalNoteResponse(
            id=n.id,
            author_user_id=n.author_user_id,
            author_name=n.author.full_name if n.author else None,
            note=n.note,
            created_at=n.created_at,
        )
        for n in (it.internal_notes or [])
    ]
    return FeedbackSubmissionManageResponse(
        id=it.id,
        reference_code=it.reference_code,
        institution_id=it.institution_id,
        submitting_user_id=it.submitting_user_id,
        contact_name=it.contact_name,
        contact_email=it.contact_email,
        category=it.category,
        subject=it.subject,
        message=it.message,
        page_reference=it.page_reference,
        status=it.status,
        assigned_reviewer_id=it.assigned_reviewer_id,
        assigned_reviewer_name=it.assigned_reviewer.full_name if it.assigned_reviewer else None,
        created_at=it.created_at,
        updated_at=it.updated_at,
        internal_notes=notes_responses,
    )


@router.post("/manage/{submission_id}/notes", response_model=FeedbackInternalNoteResponse)
def add_feedback_internal_note(
    submission_id: str,
    payload: FeedbackInternalNoteCreate,
    membership: Membership = Depends(
        require_roles(
            UserRole.INSTITUTION_ADMINISTRATOR,
            UserRole.TIMETABLE_COORDINATOR,
            UserRole.EXAM_CONTROLLER,
        )
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Adds a protected internal note to a submission.
    """
    note = FeedbackService.add_internal_note(
        db=db,
        submission_id=submission_id,
        note_text=payload.note,
        author=current_user,
        membership=membership,
    )
    return FeedbackInternalNoteResponse(
        id=note.id,
        author_user_id=note.author_user_id,
        author_name=current_user.full_name,
        note=note.note,
        created_at=note.created_at,
    )
