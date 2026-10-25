from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import (
    get_current_membership,
    get_current_user,
    require_roles,
    verify_csrf_token,
    verify_institution_ownership,
)
from app.models.user import UserRole, Membership, User
from app.models.schedule import TimetableDraft
from app.models.exam import ExamSitting
from app.models.publication import Publication, PublicationType
from app.schemas.publication import (
    PublishRequest,
    PrePublishReviewOut,
    PublicationOut,
    PublicationSummaryOut,
    PublicationDiffOut,
)
from app.schemas.timetable_draft import TimetableDraftOut
from app.services.publication_service import PublicationService

router = APIRouter(prefix="/publications", tags=["Controlled Publication"])


@router.get("/pre-publish-review/{draft_id}", response_model=PrePublishReviewOut)
def get_pre_publish_review(
    draft_id: str,
    membership: Membership = Depends(
        require_roles(
            UserRole.INSTITUTION_ADMINISTRATOR,
            UserRole.TIMETABLE_COORDINATOR,
            UserRole.EXAM_CONTROLLER,
        )
    ),
    db: Session = Depends(get_db),
):
    """
    Analyzes draft readiness for publication:
    Computes validator status, diff against active publication, affected users, and reservation conflicts.
    """
    draft = db.query(TimetableDraft).filter(TimetableDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timetable draft not found.")
    verify_institution_ownership(draft.institution_id, membership)

    return PublicationService.pre_publish_review(db, draft)


@router.post("/publish", response_model=PublicationOut, status_code=status.HTTP_201_CREATED)
def publish_schedule(
    payload: PublishRequest,
    membership: Membership = Depends(
        require_roles(
            UserRole.INSTITUTION_ADMINISTRATOR,
            UserRole.TIMETABLE_COORDINATOR,
            UserRole.EXAM_CONTROLLER,
        )
    ),
    user: User = Depends(get_current_user),
    _csrf: None = Depends(verify_csrf_token),
    db: Session = Depends(get_db),
):
    """
    Executes transactionally safe 9-step atomic publication:
    Locks scope, verifies revision, validates reservations, verifies rules, writes immutable publication,
    updates reservations, writes outbox events, and commits.
    """
    if payload.publication_type == "TIMETABLE":
        draft = db.query(TimetableDraft).filter(TimetableDraft.id == payload.draft_id).first()
        if not draft:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timetable draft not found.")
        verify_institution_ownership(draft.institution_id, membership)

        pub = PublicationService.publish_timetable(
            db=db,
            draft=draft,
            user_id=user.id,
            expected_revision=payload.expected_revision,
            publication_note=payload.publication_note,
        )
        return pub

    elif payload.publication_type in ("EXAM_THEORY", "EXAM_PRACTICAL"):
        sitting = db.query(ExamSitting).filter(ExamSitting.id == payload.draft_id).first()
        if not sitting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam sitting not found.")
        verify_institution_ownership(sitting.institution_id, membership)

        pub = PublicationService.publish_exam_sitting(
            db=db,
            sitting=sitting,
            user_id=user.id,
            expected_revision=payload.expected_revision,
            publication_note=payload.publication_note,
        )
        return pub

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported publication_type '{payload.publication_type}'.",
        )


@router.get("", response_model=List[PublicationSummaryOut])
def list_publications(
    publication_type: Optional[str] = Query(None),
    academic_term_id: Optional[str] = Query(None),
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    """Lists publication history for the institution."""
    query = db.query(Publication).filter(Publication.institution_id == membership.institution_id)
    if publication_type:
        query = query.filter(Publication.publication_type == publication_type)
    if academic_term_id:
        query = query.filter(Publication.academic_term_id == academic_term_id)

    pubs = query.order_by(Publication.version_number.desc()).all()
    out = []
    for p in pubs:
        diff = p.diff_summary or {}
        out.append(
            PublicationSummaryOut(
                id=p.id,
                publication_type=p.publication_type.value,
                version_number=p.version_number,
                published_at=p.published_at,
                publication_note=p.publication_note,
                is_active=p.is_active,
                change_count=diff.get("changed_count", 0),
            )
        )
    return out


@router.get("/{id}", response_model=PublicationOut)
def get_publication(
    id: str,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    """Retrieves full details of a specific publication snapshot."""
    pub = db.query(Publication).filter(Publication.id == id).first()
    if not pub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publication record not found.")
    verify_institution_ownership(pub.institution_id, membership)
    return pub


@router.get("/{id}/diff/{compare_id}", response_model=PublicationDiffOut)
def get_publication_diff(
    id: str,
    compare_id: str,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    """Computes full detailed diff between two publication versions."""
    pub_source = db.query(Publication).filter(Publication.id == id).first()
    pub_target = db.query(Publication).filter(Publication.id == compare_id).first()
    if not pub_source or not pub_target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or both publications not found.")
    verify_institution_ownership(pub_source.institution_id, membership)
    verify_institution_ownership(pub_target.institution_id, membership)

    diff = PublicationService.calculate_timetable_diff(
        old_assignments=pub_source.snapshot.get("output_assignments", []),
        new_assignments=pub_target.snapshot.get("output_assignments", []),
        input_snapshot=pub_target.snapshot.get("input_snapshot", {}),
    )

    return PublicationDiffOut(
        source_version=pub_source.version_number,
        target_version=pub_target.version_number,
        changed_sessions=diff.get("changed_sessions", []),
        added_sessions=diff.get("added_sessions", []),
        removed_sessions=diff.get("removed_sessions", []),
        affected_teachers=diff.get("affected_teachers", []),
        affected_sections=diff.get("affected_sections", []),
    )


@router.post("/{id}/restore", response_model=TimetableDraftOut, status_code=status.HTTP_201_CREATED)
def restore_publication_as_draft(
    id: str,
    membership: Membership = Depends(
        require_roles(
            UserRole.INSTITUTION_ADMINISTRATOR,
            UserRole.TIMETABLE_COORDINATOR,
        )
    ),
    user: User = Depends(get_current_user),
    _csrf: None = Depends(verify_csrf_token),
    db: Session = Depends(get_db),
):
    """
    Restores an old publication version as a NEW draft.
    Does NOT delete publication history.
    Enforces independent re-validation before restored content can be published.
    """
    pub = db.query(Publication).filter(Publication.id == id).first()
    if not pub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Publication record not found.")
    verify_institution_ownership(pub.institution_id, membership)

    new_draft = PublicationService.restore_publication_as_draft(db, id, user.id)
    return new_draft
