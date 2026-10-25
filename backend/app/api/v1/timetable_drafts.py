import json
import hashlib
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
from app.models.user import UserRole, Membership
from app.models.schedule import TimetableDraft, Session as DbSession
from app.schemas.timetable_draft import (
    TimetableDraftCreate,
    TimetableDraftOut,
    TimetableDraftGenerateResponse,
    AssignmentUpdate,
    RepairRequest,
    RepairResponse,
)
from app.services.job_service import JobService
from app.services.schedule_checker import ScheduleChecker
from app.services.schedule_solver import ScheduleSolver

router = APIRouter(prefix="/timetable-drafts", tags=["Timetable Drafts"])


def compute_snapshot_hash(snapshot: dict) -> str:
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@router.post("", response_model=TimetableDraftOut, status_code=status.HTTP_201_CREATED)
def create_timetable_draft(
    payload: TimetableDraftCreate,
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
    Creates a new immutable input snapshot and draft record.
    Calculates SHA-256 hash of the snapshot to guarantee provenance.
    """
    snapshot = payload.input_snapshot or {
        "term_id": payload.academic_term_id,
        "sessions": [],
        "rooms": [],
        "teachers": [],
        "days": [0, 1, 2, 3, 4],
        "periods_per_day": 8,
    }
    input_hash = compute_snapshot_hash(snapshot)

    draft = TimetableDraft(
        institution_id=membership.institution_id,
        academic_term_id=payload.academic_term_id,
        name=payload.name,
        status="DRAFT",
        revision=1,
        input_hash=input_hash,
        input_snapshot=snapshot,
        parameters=payload.parameters or {},
        output_assignments=[],
        is_published=False,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


@router.get("/{id}", response_model=TimetableDraftOut)
def get_timetable_draft(
    id: str,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    """Retrieves timetable draft details and verification reports."""
    draft = db.query(TimetableDraft).filter(TimetableDraft.id == id).first()
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timetable draft not found.",
        )
    verify_institution_ownership(draft.institution_id, membership)
    return draft


@router.post("/{id}/generate", response_model=TimetableDraftGenerateResponse, status_code=status.HTTP_202_ACCEPTED)
def generate_timetable(
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
    Asynchronously dispatches an OR-Tools CP-SAT solving task to the background worker.
    Rejects generation if the timetable draft is already published.
    Returns HTTP 202 Accepted and a job reference.
    """
    draft = db.query(TimetableDraft).filter(TimetableDraft.id == id).first()
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timetable draft not found.",
        )
    verify_institution_ownership(draft.institution_id, membership)

    if draft.is_published or draft.status == "PUBLISHED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Published timetable drafts are immutable and cannot be regenerated.",
        )

    # Enqueue background job
    job = JobService.create_job(
        db=db,
        institution_id=membership.institution_id,
        job_type="TIMETABLE_SOLVE",
        input_reference={"draft_id": draft.id},
    )

    draft.status = "GENERATING"
    db.commit()

    return TimetableDraftGenerateResponse(
        draft_id=draft.id,
        job_id=job.id,
        status="QUEUED",
        message="Timetable generation job dispatched to background worker.",
    )


@router.post("/{id}/check")
def check_timetable(
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
    Executes the independent validation checker against the draft's output assignments.
    Updates the draft validation report and sets status to CHECKED if clean.
    """
    draft = db.query(TimetableDraft).filter(TimetableDraft.id == id).first()
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timetable draft not found.",
        )
    verify_institution_ownership(draft.institution_id, membership)

    report = ScheduleChecker.validate(draft.input_snapshot, draft.output_assignments)
    draft.validation_report = report
    if report["is_valid"]:
        draft.status = "CHECKED"
    else:
        draft.status = "INVALID"

    db.commit()
    return report


@router.patch("/{id}/assignments/{assignment_id}", response_model=TimetableDraftOut)
def update_draft_assignment(
    id: str,
    assignment_id: str,
    payload: AssignmentUpdate,
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
    Updates a single assignment in a draft timetable.
    Enforces expected-revision optimistic locking (returns 409 Conflict if stale).
    Rejects edits on published drafts.
    Runs independent checker to update status and validation report.
    """
    draft = db.query(TimetableDraft).filter(TimetableDraft.id == id).first()
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timetable draft not found.",
        )
    verify_institution_ownership(draft.institution_id, membership)

    if draft.is_published or draft.status == "PUBLISHED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Published timetable drafts are immutable and cannot be edited.",
        )

    # Revision check
    if draft.revision != payload.expected_revision:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Revision conflict: draft has revision {draft.revision}, but edit expected revision {payload.expected_revision}.",
        )

    # Find assignment in draft.output_assignments
    assignments = [dict(a) for a in draft.output_assignments]
    target_idx = None
    for idx, a in enumerate(assignments):
        if a.get("id") == assignment_id or a.get("session_id") == assignment_id:
            target_idx = idx
            break

    if target_idx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment '{assignment_id}' not found in draft.",
        )

    assign = assignments[target_idx]
    if payload.day is not None:
        assign["day"] = payload.day
    target_period = payload.period if payload.period is not None else payload.start_period
    if target_period is not None:
        assign["period"] = target_period
    if payload.room_id is not None:
        assign["room_id"] = payload.room_id
    if payload.is_locked is not None:
        assign["is_locked"] = payload.is_locked

    assignments[target_idx] = assign
    draft.output_assignments = assignments
    draft.revision += 1

    # Authoritative validation
    report = ScheduleChecker.validate(draft.input_snapshot, draft.output_assignments)
    draft.validation_report = report
    if report.get("is_valid"):
        draft.status = "CHECKED"
    else:
        draft.status = "INVALID"

    db.commit()
    db.refresh(draft)
    return draft


@router.post("/{id}/repair", response_model=RepairResponse)
def repair_timetable(
    id: str,
    payload: RepairRequest,
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
    Executes minimal-change repair on a timetable draft using CP-SAT.
    Enforces expected-revision checks.
    Preserves locked assignments.
    Minimizes disruption costs and returns before/after change comparisons.
    """
    draft = db.query(TimetableDraft).filter(TimetableDraft.id == id).first()
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timetable draft not found.",
        )
    verify_institution_ownership(draft.institution_id, membership)

    if draft.is_published or draft.status == "PUBLISHED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Published timetable drafts are immutable and cannot be repaired.",
        )

    if draft.revision != payload.expected_revision:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Revision conflict: draft has revision {draft.revision}, but repair expected revision {payload.expected_revision}.",
        )

    result = ScheduleSolver.repair(
        snapshot=draft.input_snapshot,
        baseline_assignments=draft.output_assignments,
        time_limit_seconds=float(payload.time_limit_seconds or 30),
    )

    if result["solver_status"] in ("OPTIMAL", "FEASIBLE"):
        draft.output_assignments = result["assignments"]
        draft.revision += 1

        report = ScheduleChecker.validate(draft.input_snapshot, draft.output_assignments)
        draft.validation_report = report
        draft.status = "CHECKED" if report.get("is_valid") else "INVALID"

        db.commit()
        db.refresh(draft)

        return RepairResponse(
            draft_id=draft.id,
            revision=draft.revision,
            status=draft.status,
            is_valid=report.get("is_valid", False),
            changes=result["changes"],
            change_count=result["change_count"],
            validation_report=report,
            output_assignments=draft.output_assignments,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": f"Repair solver terminated with status {result['solver_status']}. Schedule cannot be repaired without relaxing constraints or unlocking sessions.",
                "solver_status": result["solver_status"],
                "error_code": result.get("error_code"),
                "error_message": result.get("error_message"),
            },
        )
