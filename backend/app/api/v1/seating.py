from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_institution, require_role, get_current_user
from app.models.seating import ExamSession, ExamEnrollment, SeatAssignment, ExamStatus
from app.models.user import User, UserRole
from app.models.academic import AcademicTerm
from app.models.schedule import TimeSlot
from app.schemas.seating import (
    ExamSessionCreate,
    ExamSessionOut,
    ExamEnrollmentBulkCreate,
    GenerateSeatingRequest,
    SeatAssignmentOut,
    SeatingArrangementReport,
)
from app.services.seating_engine import generate_exam_seating_arrangement, get_exam_seating_report

router = APIRouter(prefix="/seating", tags=["Exams & Seating"])


@router.get("/exams", response_model=List[ExamSessionOut])
def list_exams(inst_id: str = Depends(require_institution), db: Session = Depends(get_db)):
    return db.query(ExamSession).filter(ExamSession.institution_id == inst_id).all()


@router.post("/exams", response_model=ExamSessionOut, status_code=status.HTTP_201_CREATED)
def create_exam_session(
    payload: ExamSessionCreate,
    inst_id: str = Depends(require_institution),
    current_user: User = Depends(require_role([UserRole.ADMIN.value, UserRole.SUPERADMIN.value])),
    db: Session = Depends(get_db)
):
    exam = ExamSession(
        institution_id=inst_id,
        academic_term_id=payload.academic_term_id,
        name=payload.name,
        exam_date=payload.exam_date,
        time_slot_id=payload.time_slot_id,
        status=ExamStatus.DRAFT.value
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam


@router.post("/exams/{exam_id}/enrollments", status_code=status.HTTP_201_CREATED)
def bulk_enroll_students(
    exam_id: str,
    payload: ExamEnrollmentBulkCreate,
    inst_id: str = Depends(require_institution),
    current_user: User = Depends(require_role([UserRole.ADMIN.value, UserRole.SUPERADMIN.value])),
    db: Session = Depends(get_db)
):
    exam = db.query(ExamSession).filter(
        ExamSession.id == exam_id,
        ExamSession.institution_id == inst_id
    ).first()
    if not exam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam session not found")

    created = 0
    for item in payload.enrollments:
        # Check if already enrolled in this exam session
        exists = db.query(ExamEnrollment).filter(
            ExamEnrollment.institution_id == inst_id,
            ExamEnrollment.exam_session_id == exam_id,
            ExamEnrollment.student_id == item.student_id
        ).first()
        if not exists:
            enrollment = ExamEnrollment(
                institution_id=inst_id,
                exam_session_id=exam_id,
                student_id=item.student_id,
                course_id=item.course_id
            )
            db.add(enrollment)
            created += 1

    db.commit()
    return {"message": f"Successfully enrolled {created} students into exam session", "enrolled_count": created}


@router.post("/exams/{exam_id}/generate-seating")
def generate_seating(
    exam_id: str,
    payload: GenerateSeatingRequest,
    inst_id: str = Depends(require_institution),
    current_user: User = Depends(require_role([UserRole.ADMIN.value, UserRole.SUPERADMIN.value])),
    db: Session = Depends(get_db)
):
    result = generate_exam_seating_arrangement(
        db=db,
        institution_id=inst_id,
        exam_session_id=exam_id,
        classroom_ids=payload.classroom_ids
    )

    if result.get("status") == "ERROR":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("message"))
    elif result.get("status") == "CAPACITY_EXCEEDED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result.get("message"))

    return result


@router.get("/exams/{exam_id}/report", response_model=SeatingArrangementReport)
def get_seating_report(
    exam_id: str,
    inst_id: str = Depends(require_institution),
    db: Session = Depends(get_db)
):
    report = get_exam_seating_report(db=db, institution_id=inst_id, exam_session_id=exam_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam seating plan not found or not yet generated")
    return report


@router.get("/exams/{exam_id}/hall-ticket/{student_id}", response_model=SeatAssignmentOut)
def get_student_hall_ticket(
    exam_id: str,
    student_id: str,
    inst_id: str = Depends(require_institution),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Students can only view their own hall ticket unless Admin
    if current_user.role == UserRole.STUDENT.value and current_user.id != student_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Cannot view another student's seat allocation")

    assignment = db.query(SeatAssignment).filter(
        SeatAssignment.institution_id == inst_id,
        SeatAssignment.exam_session_id == exam_id,
        SeatAssignment.student_id == student_id
    ).first()

    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No seat assignment found for this student")

    return SeatAssignmentOut(
        id=assignment.id,
        exam_session_id=assignment.exam_session_id,
        classroom_id=assignment.classroom_id,
        classroom_name=assignment.classroom.name if assignment.classroom else None,
        student_id=assignment.student_id,
        student_name=assignment.student.full_name if assignment.student else None,
        course_id=assignment.course_id,
        course_code=assignment.course.code if assignment.course else None,
        seat_row=assignment.seat_row,
        seat_col=assignment.seat_col,
        desk_label=assignment.desk_label
    )
