from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import (
    get_current_session,
    get_current_membership,
    require_roles,
    verify_csrf_token,
    verify_institution_ownership,
)
from app.models.user import UserRole, Membership, UserSession
from app.models.job import Job
from app.schemas.job import JobCreate, JobOut, JobCancelResponse
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["Background Jobs"])


@router.post("", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def enqueue_job(
    payload: JobCreate,
    membership: Membership = Depends(
        require_roles(
            UserRole.INSTITUTION_ADMINISTRATOR,
            UserRole.TIMETABLE_COORDINATOR,
            UserRole.EXAM_CONTROLLER,
        )
    ),
    _csrf: None = Depends(verify_csrf_token),
    db: Session = Depends(get_db),
):
    """Enqueues a durable background job for the authenticated institution."""
    job = JobService.create_job(
        db=db,
        institution_id=membership.institution_id,
        job_type=payload.job_type,
        input_reference=payload.input_reference,
        max_attempts=payload.max_attempts,
    )
    return job


@router.get("", response_model=List[JobOut])
def list_jobs(
    limit: int = 50,
    status_filter: Optional[str] = None,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    """Lists recent jobs scoped to the caller's institution."""
    query = db.query(Job).filter(Job.institution_id == membership.institution_id)
    if status_filter:
        query = query.filter(Job.status == status_filter.upper())
    jobs = query.order_by(Job.created_at.desc()).limit(min(limit, 100)).all()
    return jobs


@router.get("/{id}", response_model=JobOut)
def get_job(
    id: str,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    """
    Retrieves status, phase progress, and results for a job.
    Enforces multi-tenant boundary: returns 404 for cross-tenant access.
    """
    job = JobService.get_job(db, id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )
    # Strictly enforce tenant ownership
    verify_institution_ownership(job.institution_id, membership)
    return job


@router.post("/{id}/cancel", response_model=JobCancelResponse)
def cancel_job(
    id: str,
    membership: Membership = Depends(
        require_roles(
            UserRole.INSTITUTION_ADMINISTRATOR,
            UserRole.TIMETABLE_COORDINATOR,
            UserRole.EXAM_CONTROLLER,
        )
    ),
    _csrf: None = Depends(verify_csrf_token),
    db: Session = Depends(get_db),
):
    """
    Cancels an active or queued job.
    Enforces tenant boundaries and role authorization.
    """
    job = JobService.get_job(db, id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )
    verify_institution_ownership(job.institution_id, membership)

    updated_job = JobService.request_cancellation(db, id, institution_id=membership.institution_id)
    if not updated_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )

    return JobCancelResponse(
        job_id=updated_job.id,
        status=updated_job.status,
        cancellation_requested=updated_job.cancellation_requested,
        message=f"Job {id} cancellation status: {updated_job.phase_label}",
    )
