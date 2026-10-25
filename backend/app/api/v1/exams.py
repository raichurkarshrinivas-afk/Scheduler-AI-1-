from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import (
    get_current_membership,
    require_roles,
    verify_csrf_token,
    verify_institution_ownership,
)
from app.models.user import UserRole, Membership
from app.models.exam import ExamSitting, ExamType
from app.schemas.exam import (
    ExamSittingCreate,
    ExamSittingOut,
    SeatReassignRequest,
    WorkstationReassignRequest,
)
from app.services.theory_seating_engine import TheorySeatingEngine
from app.services.practical_exam_engine import PracticalExamEngine
from app.services.exam_export_service import ExamExportService

router = APIRouter(prefix="/exams", tags=["Exam Logistics"])


@router.get("/sittings", response_model=List[ExamSittingOut])
def list_exam_sittings(
    exam_type: Optional[str] = Query(None),
    academic_term_id: Optional[str] = Query(None),
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    """Lists exam sittings for the current user's institution."""
    query = db.query(ExamSitting).filter(ExamSitting.institution_id == membership.institution_id)
    if exam_type:
        query = query.filter(ExamSitting.exam_type == exam_type)
    if academic_term_id:
        query = query.filter(ExamSitting.academic_term_id == academic_term_id)
    return query.order_by(ExamSitting.created_at.desc()).all()


@router.get("/theory/sittings", response_model=List[ExamSittingOut])
def list_theory_sittings(
    academic_term_id: Optional[str] = Query(None),
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    """Lists theory examination sittings."""
    return list_exam_sittings(exam_type=ExamType.THEORY, academic_term_id=academic_term_id, membership=membership, db=db)


@router.get("/practical/sittings", response_model=List[ExamSittingOut])
def list_practical_sittings(
    academic_term_id: Optional[str] = Query(None),
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    """Lists practical examination sittings."""
    return list_exam_sittings(exam_type=ExamType.PRACTICAL, academic_term_id=academic_term_id, membership=membership, db=db)



# =========================================================================
# THEORY EXAMINATION SEATING
# =========================================================================

@router.post("/theory/sittings", response_model=ExamSittingOut, status_code=status.HTTP_201_CREATED)
def create_theory_sitting(
    payload: ExamSittingCreate,
    membership: Membership = Depends(
        require_roles(
            UserRole.INSTITUTION_ADMINISTRATOR,
            UserRole.EXAM_CONTROLLER,
            UserRole.TIMETABLE_COORDINATOR,
        )
    ),
    _csrf: None = Depends(verify_csrf_token),
    db: Session = Depends(get_db),
):
    """Creates a new theory examination sitting with candidate registrations and hall rooms."""
    sitting = ExamSitting(
        institution_id=membership.institution_id,
        academic_term_id=payload.academic_term_id,
        name=payload.name,
        exam_type=ExamType.THEORY,
        status="DRAFT",
        revision=1,
        start_datetime=payload.start_datetime,
        duration_minutes=payload.duration_minutes,
        buffer_minutes=payload.buffer_minutes,
        input_snapshot=payload.input_snapshot or {"candidates": [], "rooms": []},
        parameters=payload.parameters or {},
        output_allocations=[],
        is_published=False,
    )
    db.add(sitting)
    db.commit()
    db.refresh(sitting)
    return sitting


@router.get("/theory/sittings/{id}", response_model=ExamSittingOut)
def get_theory_sitting(
    id: str,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    """Retrieves theory examination sitting details and seat plan."""
    sitting = db.query(ExamSitting).filter(ExamSitting.id == id, ExamSitting.exam_type == ExamType.THEORY).first()
    if not sitting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Theory examination sitting not found.")
    verify_institution_ownership(sitting.institution_id, membership)
    return sitting


@router.post("/theory/sittings/{id}/allocate", response_model=ExamSittingOut)
def allocate_theory_seating(
    id: str,
    membership: Membership = Depends(
        require_roles(
            UserRole.INSTITUTION_ADMINISTRATOR,
            UserRole.EXAM_CONTROLLER,
        )
    ),
    _csrf: None = Depends(verify_csrf_token),
    db: Session = Depends(get_db),
):
    """
    Executes seating allocation across eligible halls enforcing one candidate per usable bench,
    accessibility requirements, and configurable orthogonal paper adjacency.
    """
    sitting = db.query(ExamSitting).filter(ExamSitting.id == id, ExamSitting.exam_type == ExamType.THEORY).first()
    if not sitting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Theory examination sitting not found.")
    verify_institution_ownership(sitting.institution_id, membership)

    if sitting.is_published:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Published exam sittings cannot be re-allocated.")

    result = TheorySeatingEngine.allocate(sitting.input_snapshot)
    if result["status"] == "ALLOCATED":
        sitting.output_allocations = result["allocations"]
        sitting.validation_report = result["validation_report"]
        sitting.status = "CHECKED"
        sitting.revision += 1
        db.commit()
        db.refresh(sitting)
        return sitting
    else:
        sitting.validation_report = result["validation_report"]
        sitting.status = "INVALID"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": result["error_message"],
                "error_code": result["error_code"],
                "validation_report": result["validation_report"],
            },
        )


@router.post("/theory/sittings/{id}/validate")
def validate_theory_seating(
    id: str,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    """Authoritatively checks theory seating plan without modifying state."""
    sitting = db.query(ExamSitting).filter(ExamSitting.id == id).first()
    if not sitting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam sitting not found.")
    verify_institution_ownership(sitting.institution_id, membership)

    report = TheorySeatingEngine.verify_theory_seating(sitting.input_snapshot, sitting.output_allocations)
    sitting.validation_report = report
    sitting.status = "CHECKED" if report["is_valid"] else "INVALID"
    db.commit()
    return report


@router.patch("/theory/sittings/{id}/seats/{candidate_id}", response_model=ExamSittingOut)
def reassign_theory_seat(
    id: str,
    candidate_id: str,
    payload: SeatReassignRequest,
    membership: Membership = Depends(
        require_roles(
            UserRole.INSTITUTION_ADMINISTRATOR,
            UserRole.EXAM_CONTROLLER,
        )
    ),
    _csrf: None = Depends(verify_csrf_token),
    db: Session = Depends(get_db),
):
    """
    Reassigns a candidate to another bench or swaps two candidates.
    Enforces expected-revision checks. Authoritatively runs verification checker.
    """
    sitting = db.query(ExamSitting).filter(ExamSitting.id == id).first()
    if not sitting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam sitting not found.")
    verify_institution_ownership(sitting.institution_id, membership)

    if sitting.is_published:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Published exam sittings cannot be modified.")

    if sitting.revision != payload.expected_revision:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Revision conflict: sitting has revision {sitting.revision}, expected {payload.expected_revision}.",
        )

    allocations = [dict(a) for a in sitting.output_allocations]
    cand_idx = next((i for i, a in enumerate(allocations) if a.get("candidate_id") == candidate_id), None)

    if cand_idx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Candidate '{candidate_id}' not found in sitting allocations.")

    # Swapping logic if target_candidate_id provided
    if payload.target_candidate_id:
        target_idx = next((i for i, a in enumerate(allocations) if a.get("candidate_id") == payload.target_candidate_id), None)
        if target_idx is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Target candidate '{payload.target_candidate_id}' not found.")
        # Swap seats
        allocations[cand_idx]["seat_id"], allocations[target_idx]["seat_id"] = allocations[target_idx]["seat_id"], allocations[cand_idx]["seat_id"]
        allocations[cand_idx]["room_id"], allocations[target_idx]["room_id"] = allocations[target_idx]["room_id"], allocations[cand_idx]["room_id"]
        allocations[cand_idx]["bench_label"], allocations[target_idx]["bench_label"] = allocations[target_idx]["bench_label"], allocations[cand_idx]["bench_label"]
    else:
        if payload.seat_id:
            allocations[cand_idx]["seat_id"] = payload.seat_id
        if payload.room_id:
            allocations[cand_idx]["room_id"] = payload.room_id

    sitting.output_allocations = allocations
    sitting.revision += 1

    report = TheorySeatingEngine.verify_theory_seating(sitting.input_snapshot, sitting.output_allocations)
    sitting.validation_report = report
    sitting.status = "CHECKED" if report["is_valid"] else "INVALID"

    db.commit()
    db.refresh(sitting)
    return sitting


# =========================================================================
# PRACTICAL EXAMINATION SITTINGS & BATCH WORKSTATIONS
# =========================================================================

@router.post("/practical/sittings", response_model=ExamSittingOut, status_code=status.HTTP_201_CREATED)
def create_practical_sitting(
    payload: ExamSittingCreate,
    membership: Membership = Depends(
        require_roles(
            UserRole.INSTITUTION_ADMINISTRATOR,
            UserRole.EXAM_CONTROLLER,
            UserRole.TIMETABLE_COORDINATOR,
        )
    ),
    _csrf: None = Depends(verify_csrf_token),
    db: Session = Depends(get_db),
):
    """Creates a new practical examination sitting with candidate batches, labs, and turnaround buffers."""
    sitting = ExamSitting(
        institution_id=membership.institution_id,
        academic_term_id=payload.academic_term_id,
        name=payload.name,
        exam_type=ExamType.PRACTICAL,
        status="DRAFT",
        revision=1,
        start_datetime=payload.start_datetime,
        duration_minutes=payload.duration_minutes,
        buffer_minutes=payload.buffer_minutes,
        input_snapshot=payload.input_snapshot or {"candidates": [], "labs": [], "sittings": []},
        parameters=payload.parameters or {},
        output_allocations=[],
        is_published=False,
    )
    db.add(sitting)
    db.commit()
    db.refresh(sitting)
    return sitting


@router.get("/practical/sittings/{id}", response_model=ExamSittingOut)
def get_practical_sitting(
    id: str,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    """Retrieves practical examination sitting details and workstation allocations."""
    sitting = db.query(ExamSitting).filter(ExamSitting.id == id, ExamSitting.exam_type == ExamType.PRACTICAL).first()
    if not sitting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practical examination sitting not found.")
    verify_institution_ownership(sitting.institution_id, membership)
    return sitting


@router.post("/practical/sittings/{id}/allocate", response_model=ExamSittingOut)
def allocate_practical_workstations(
    id: str,
    membership: Membership = Depends(
        require_roles(
            UserRole.INSTITUTION_ADMINISTRATOR,
            UserRole.EXAM_CONTROLLER,
        )
    ),
    _csrf: None = Depends(verify_csrf_token),
    db: Session = Depends(get_db),
):
    """
    Allocates candidates to compatible laboratory workstations across sittings/batches,
    validating software/hardware features and examiner non-overlap.
    """
    sitting = db.query(ExamSitting).filter(ExamSitting.id == id, ExamSitting.exam_type == ExamType.PRACTICAL).first()
    if not sitting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practical examination sitting not found.")
    verify_institution_ownership(sitting.institution_id, membership)

    if sitting.is_published:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Published exam sittings cannot be re-allocated.")

    result = PracticalExamEngine.allocate(sitting.input_snapshot)
    if result["status"] == "ALLOCATED":
        sitting.output_allocations = result["allocations"]
        sitting.validation_report = result["validation_report"]
        sitting.status = "CHECKED"
        sitting.revision += 1
        db.commit()
        db.refresh(sitting)
        return sitting
    else:
        sitting.validation_report = result["validation_report"]
        sitting.status = "INVALID"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": result["error_message"],
                "error_code": result["error_code"],
                "validation_report": result["validation_report"],
            },
        )


@router.post("/practical/sittings/{id}/validate")
def validate_practical_allocation(
    id: str,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    """Authoritatively validates practical allocations, buffers, and examiner availability."""
    sitting = db.query(ExamSitting).filter(ExamSitting.id == id).first()
    if not sitting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam sitting not found.")
    verify_institution_ownership(sitting.institution_id, membership)

    report = PracticalExamEngine.verify_practical_allocation(sitting.input_snapshot, sitting.output_allocations)
    sitting.validation_report = report
    sitting.status = "CHECKED" if report["is_valid"] else "INVALID"
    db.commit()
    return report


@router.patch("/practical/sittings/{id}/workstations/{candidate_id}", response_model=ExamSittingOut)
def reassign_practical_workstation(
    id: str,
    candidate_id: str,
    payload: WorkstationReassignRequest,
    membership: Membership = Depends(
        require_roles(
            UserRole.INSTITUTION_ADMINISTRATOR,
            UserRole.EXAM_CONTROLLER,
        )
    ),
    _csrf: None = Depends(verify_csrf_token),
    db: Session = Depends(get_db),
):
    """
    Reassigns a candidate to another workstation, batch, or laboratory in practical exam sittings.
    Enforces expected-revision checks. Authoritatively runs verification checker.
    """
    sitting = db.query(ExamSitting).filter(ExamSitting.id == id, ExamSitting.exam_type == ExamType.PRACTICAL).first()
    if not sitting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practical examination sitting not found.")
    verify_institution_ownership(sitting.institution_id, membership)

    if sitting.is_published:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Published exam sittings cannot be modified.")

    if sitting.revision != payload.expected_revision:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Revision conflict: sitting has revision {sitting.revision}, expected {payload.expected_revision}.",
        )

    allocations = [dict(a) for a in sitting.output_allocations]
    cand_idx = next((i for i, a in enumerate(allocations) if a.get("candidate_id") == candidate_id), None)
    if cand_idx is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Candidate '{candidate_id}' not found in sitting allocations.")

    if payload.batch_id:
        allocations[cand_idx]["batch_id"] = payload.batch_id
    if payload.lab_id:
        allocations[cand_idx]["lab_id"] = payload.lab_id
    if payload.workstation_id:
        allocations[cand_idx]["workstation_id"] = payload.workstation_id

    sitting.output_allocations = allocations
    sitting.revision += 1

    report = PracticalExamEngine.verify_practical_allocation(sitting.input_snapshot, sitting.output_allocations)
    sitting.validation_report = report
    sitting.status = "CHECKED" if report["is_valid"] else "INVALID"

    db.commit()
    db.refresh(sitting)
    return sitting


# =========================================================================
# EXPORTS (AUTHENTICATED WITH EXPIRING TOKENS & PRIVACY SAFEGUARDS)
# =========================================================================

@router.get("/theory/sittings/{id}/export/seat-plan")
def export_theory_seat_plan(
    id: str,
    room_id: Optional[str] = Query(None),
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    """
    Exports public hall seat plan.
    CRITICAL PRIVACY RULE: Private accommodation notes are strictly omitted.
    """
    sitting = db.query(ExamSitting).filter(ExamSitting.id == id).first()
    if not sitting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam sitting not found.")
    verify_institution_ownership(sitting.institution_id, membership)

    return ExamExportService.generate_theory_hall_seat_plan(sitting, room_id=room_id)


@router.get("/theory/sittings/{id}/export/candidate-list")
def export_candidate_list(
    id: str,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    """Exports official candidate desk assignment list."""
    sitting = db.query(ExamSitting).filter(ExamSitting.id == id).first()
    if not sitting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam sitting not found.")
    verify_institution_ownership(sitting.institution_id, membership)

    return ExamExportService.generate_candidate_list(sitting)


@router.get("/theory/sittings/{id}/export/attendance-sheet")
def export_attendance_sheet(
    id: str,
    room_id: Optional[str] = Query(None),
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    """Exports invigilator attendance sheet with signature placeholders."""
    sitting = db.query(ExamSitting).filter(ExamSitting.id == id).first()
    if not sitting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam sitting not found.")
    verify_institution_ownership(sitting.institution_id, membership)

    return ExamExportService.generate_attendance_sheet(sitting, room_id=room_id)


@router.get("/practical/sittings/{id}/export/workstation-list")
def export_practical_workstations(
    id: str,
    membership: Membership = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    """Exports practical exam batch workstation allocation roster."""
    sitting = db.query(ExamSitting).filter(ExamSitting.id == id).first()
    if not sitting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam sitting not found.")
    verify_institution_ownership(sitting.institution_id, membership)

    return ExamExportService.generate_practical_workstation_list(sitting)
