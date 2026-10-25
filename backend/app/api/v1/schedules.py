from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_institution, require_role, get_current_user
from app.models.schedule import TimeSlot, ScheduleSession
from app.models.course import Course
from app.models.academic import ProgramBatch, AcademicTerm
from app.models.user import User, UserRole
from app.models.facility import Classroom
from app.schemas.schedule import (
    TimeSlotCreate,
    TimeSlotOut,
    ScheduleSessionCreate,
    ScheduleSessionOut,
    ScheduleValidationResponse,
    AutoScheduleRequest,
    AutoScheduleResponse,
)
from app.services.scheduling_engine import validate_session_constraints, auto_generate_schedule

router = APIRouter(prefix="/schedules", tags=["Schedules & Timetable"])


# --- TimeSlots ---
@router.get("/timeslots", response_model=List[TimeSlotOut])
def list_time_slots(inst_id: str = Depends(require_institution), db: Session = Depends(get_db)):
    return db.query(TimeSlot).filter(TimeSlot.institution_id == inst_id).all()


@router.post("/timeslots", response_model=TimeSlotOut, status_code=status.HTTP_201_CREATED)
def create_time_slot(
    payload: TimeSlotCreate,
    inst_id: str = Depends(require_institution),
    current_user: User = Depends(require_role([UserRole.ADMIN.value, UserRole.SUPERADMIN.value])),
    db: Session = Depends(get_db)
):
    slot = TimeSlot(
        institution_id=inst_id,
        day_of_week=payload.day_of_week,
        slot_name=payload.slot_name,
        start_time=payload.start_time,
        end_time=payload.end_time
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot


# --- Validation ---
@router.post("/validate", response_model=ScheduleValidationResponse)
def validate_schedule_candidate(
    payload: ScheduleSessionCreate,
    inst_id: str = Depends(require_institution),
    db: Session = Depends(get_db)
):
    is_valid, conflicts = validate_session_constraints(
        db=db,
        institution_id=inst_id,
        academic_term_id=payload.academic_term_id,
        course_id=payload.course_id,
        batch_id=payload.batch_id,
        instructor_id=payload.instructor_id,
        classroom_id=payload.classroom_id,
        time_slot_id=payload.time_slot_id
    )
    return ScheduleValidationResponse(is_valid=is_valid, conflicts=conflicts)


# --- Sessions ---
@router.get("/sessions", response_model=List[ScheduleSessionOut])
def list_schedule_sessions(
    academic_term_id: Optional[str] = None,
    batch_id: Optional[str] = None,
    instructor_id: Optional[str] = None,
    inst_id: str = Depends(require_institution),
    db: Session = Depends(get_db)
):
    query = db.query(ScheduleSession).filter(ScheduleSession.institution_id == inst_id)
    if academic_term_id:
        query = query.filter(ScheduleSession.academic_term_id == academic_term_id)
    if batch_id:
        query = query.filter(ScheduleSession.batch_id == batch_id)
    if instructor_id:
        query = query.filter(ScheduleSession.instructor_id == instructor_id)

    sessions = query.all()
    results = []
    for s in sessions:
        results.append(ScheduleSessionOut(
            id=s.id,
            institution_id=s.institution_id,
            academic_term_id=s.academic_term_id,
            course_id=s.course_id,
            course_code=s.course.code if s.course else None,
            course_name=s.course.name if s.course else None,
            batch_id=s.batch_id,
            batch_name=s.batch.name if s.batch else None,
            instructor_id=s.instructor_id,
            instructor_name=s.instructor.full_name if s.instructor else None,
            classroom_id=s.classroom_id,
            classroom_name=s.classroom.name if s.classroom else None,
            time_slot_id=s.time_slot_id,
            time_slot_name=s.time_slot.slot_name if s.time_slot else None,
            day_of_week=s.time_slot.day_of_week if s.time_slot else None
        ))
    return results


@router.post("/sessions", response_model=ScheduleSessionOut, status_code=status.HTTP_201_CREATED)
def create_schedule_session(
    payload: ScheduleSessionCreate,
    inst_id: str = Depends(require_institution),
    current_user: User = Depends(require_role([UserRole.ADMIN.value, UserRole.SUPERADMIN.value])),
    db: Session = Depends(get_db)
):
    is_valid, conflicts = validate_session_constraints(
        db=db,
        institution_id=inst_id,
        academic_term_id=payload.academic_term_id,
        course_id=payload.course_id,
        batch_id=payload.batch_id,
        instructor_id=payload.instructor_id,
        classroom_id=payload.classroom_id,
        time_slot_id=payload.time_slot_id
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Scheduling conflict detected",
                "conflicts": [c.model_dump() for c in conflicts]
            }
        )

    session_entry = ScheduleSession(
        institution_id=inst_id,
        academic_term_id=payload.academic_term_id,
        course_id=payload.course_id,
        batch_id=payload.batch_id,
        instructor_id=payload.instructor_id,
        classroom_id=payload.classroom_id,
        time_slot_id=payload.time_slot_id
    )
    db.add(session_entry)
    db.commit()
    db.refresh(session_entry)

    return ScheduleSessionOut(
        id=session_entry.id,
        institution_id=session_entry.institution_id,
        academic_term_id=session_entry.academic_term_id,
        course_id=session_entry.course_id,
        course_code=session_entry.course.code if session_entry.course else None,
        course_name=session_entry.course.name if session_entry.course else None,
        batch_id=session_entry.batch_id,
        batch_name=session_entry.batch.name if session_entry.batch else None,
        instructor_id=session_entry.instructor_id,
        instructor_name=session_entry.instructor.full_name if session_entry.instructor else None,
        classroom_id=session_entry.classroom_id,
        classroom_name=session_entry.classroom.name if session_entry.classroom else None,
        time_slot_id=session_entry.time_slot_id,
        time_slot_name=session_entry.time_slot.slot_name if session_entry.time_slot else None,
        day_of_week=session_entry.time_slot.day_of_week if session_entry.time_slot else None
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule_session(
    session_id: str,
    inst_id: str = Depends(require_institution),
    current_user: User = Depends(require_role([UserRole.ADMIN.value, UserRole.SUPERADMIN.value])),
    db: Session = Depends(get_db)
):
    session_entry = db.query(ScheduleSession).filter(
        ScheduleSession.id == session_id,
        ScheduleSession.institution_id == inst_id
    ).first()
    if not session_entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule session not found")

    db.delete(session_entry)
    db.commit()
    return None


@router.post("/auto-generate", response_model=AutoScheduleResponse)
def run_auto_generate_timetable(
    payload: AutoScheduleRequest,
    inst_id: str = Depends(require_institution),
    current_user: User = Depends(require_role([UserRole.ADMIN.value, UserRole.SUPERADMIN.value])),
    db: Session = Depends(get_db)
):
    result = auto_generate_schedule(
        db=db,
        institution_id=inst_id,
        academic_term_id=payload.academic_term_id
    )
    return AutoScheduleResponse(**result)
