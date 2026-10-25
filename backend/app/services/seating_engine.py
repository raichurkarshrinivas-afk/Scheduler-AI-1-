from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from app.models.seating import ExamSession, ExamEnrollment, SeatAssignment, ExamStatus
from app.models.facility import Classroom
from app.models.user import User
from app.models.course import Course
from app.schemas.seating import SeatCell, RoomGridOut, SeatingArrangementReport


def generate_exam_seating_arrangement(
    db: Session,
    institution_id: str,
    exam_session_id: str,
    classroom_ids: List[str]
) -> Dict[str, Any]:
    exam = db.query(ExamSession).filter(
        ExamSession.id == exam_session_id,
        ExamSession.institution_id == institution_id
    ).first()

    if not exam:
        return {"status": "ERROR", "message": "Exam session not found"}

    enrollments = db.query(ExamEnrollment).filter(
        ExamEnrollment.institution_id == institution_id,
        ExamEnrollment.exam_session_id == exam_session_id
    ).all()

    if not enrollments:
        return {"status": "ERROR", "message": "No students enrolled in this exam session"}

    rooms = db.query(Classroom).filter(
        Classroom.id.in_(classroom_ids),
        Classroom.institution_id == institution_id
    ).all()

    if not rooms:
        return {"status": "ERROR", "message": "No designated classrooms found"}

    # Calculate total capacity
    total_physical_seats = sum(r.rows * r.columns for r in rooms)
    total_students = len(enrollments)

    # Group students by course
    pools: Dict[str, List[ExamEnrollment]] = {}
    for enrollment in enrollments:
        pools.setdefault(enrollment.course_id, []).append(enrollment)

    # If single course, checkerboard halves the capacity
    is_single_course = len(pools) == 1
    effective_capacity = total_physical_seats // 2 if is_single_course else total_physical_seats
    
    if total_students > effective_capacity:
        return {
            "status": "CAPACITY_EXCEEDED",
            "message": f"Classrooms capacity ({effective_capacity} anti-cheat seats) is insufficient for {total_students} candidates.",
            "total_students": total_students,
            "available_seats": effective_capacity
        }

    # Clear previous assignments for this exam session
    db.query(SeatAssignment).filter(
        SeatAssignment.institution_id == institution_id,
        SeatAssignment.exam_session_id == exam_session_id
    ).delete(synchronize_session=False)
    db.flush()

    # Pre-fetch student & course info
    students_by_id = {
        u.id: u for u in db.query(User).filter(User.institution_id == institution_id).all()
    }
    courses_by_id = {
        c.id: c for c in db.query(Course).filter(Course.institution_id == institution_id).all()
    }

    seated_count = 0
    room_grids: List[RoomGridOut] = []

    for room in rooms:
        # matrix of course_id placed
        occupied_matrix: Dict[tuple, str] = {}
        room_grid_cells: List[List[SeatCell]] = []
        room_occupied_count = 0

        for r in range(room.rows):
            row_cells: List[SeatCell] = []
            for c in range(room.columns):
                desk_label = f"{room.room_number}-R{r+1}-C{c+1}"

                # Anti-cheating rule for single course: checkerboard spacing
                if is_single_course and (r + c) % 2 != 0:
                    row_cells.append(SeatCell(
                        row=r,
                        col=c,
                        desk_label=desk_label,
                        student_id=None,
                        student_name=None,
                        course_code=None,
                        is_occupied=False
                    ))
                    continue

                # Find candidate student from a pool whose course differs from neighbors
                left_course = occupied_matrix.get((r, c - 1))
                top_course = occupied_matrix.get((r - 1, c))
                forbidden_courses = {left_course, top_course} - {None}

                selected_candidate: Optional[ExamEnrollment] = None
                
                # Sort pools by remaining student count descending
                sorted_course_ids = sorted(
                    pools.keys(),
                    key=lambda cid: len(pools[cid]),
                    reverse=True
                )

                # Prioritize a course not in forbidden_courses
                for cid in sorted_course_ids:
                    if pools[cid] and cid not in forbidden_courses:
                        selected_candidate = pools[cid].pop(0)
                        break

                # If no ideal candidate, pop from largest available non-empty pool
                if not selected_candidate:
                    for cid in sorted_course_ids:
                        if pools[cid]:
                            selected_candidate = pools[cid].pop(0)
                            break

                if selected_candidate:
                    occupied_matrix[(r, c)] = selected_candidate.course_id
                    
                    assignment = SeatAssignment(
                        institution_id=institution_id,
                        exam_session_id=exam_session_id,
                        classroom_id=room.id,
                        student_id=selected_candidate.student_id,
                        course_id=selected_candidate.course_id,
                        seat_row=r,
                        seat_col=c,
                        desk_label=desk_label
                    )
                    db.add(assignment)
                    seated_count += 1
                    room_occupied_count += 1

                    student_obj = students_by_id.get(selected_candidate.student_id)
                    course_obj = courses_by_id.get(selected_candidate.course_id)

                    row_cells.append(SeatCell(
                        row=r,
                        col=c,
                        desk_label=desk_label,
                        student_id=selected_candidate.student_id,
                        student_name=student_obj.full_name if student_obj else "Student",
                        course_code=course_obj.code if course_obj else "COURSE",
                        is_occupied=True
                    ))
                else:
                    row_cells.append(SeatCell(
                        row=r,
                        col=c,
                        desk_label=desk_label,
                        student_id=None,
                        student_name=None,
                        course_code=None,
                        is_occupied=False
                    ))
            room_grid_cells.append(row_cells)

        room_grids.append(RoomGridOut(
            classroom_id=room.id,
            classroom_name=room.name,
            building=room.building,
            room_number=room.room_number,
            rows=room.rows,
            columns=room.columns,
            total_seats=room.rows * room.columns,
            occupied_seats=room_occupied_count,
            grid=room_grid_cells
        ))

    exam.status = ExamStatus.SEATS_ALLOCATED.value
    db.commit()

    return {
        "status": "SUCCESS",
        "exam_session_id": exam_session_id,
        "exam_name": exam.name,
        "exam_date": str(exam.exam_date),
        "total_students": total_students,
        "total_seated": seated_count,
        "rooms": [r.model_dump() for r in room_grids]
    }


def get_exam_seating_report(
    db: Session,
    institution_id: str,
    exam_session_id: str
) -> Optional[SeatingArrangementReport]:
    exam = db.query(ExamSession).filter(
        ExamSession.id == exam_session_id,
        ExamSession.institution_id == institution_id
    ).first()
    if not exam:
        return None

    assignments = db.query(SeatAssignment).filter(
        SeatAssignment.institution_id == institution_id,
        SeatAssignment.exam_session_id == exam_session_id
    ).all()

    assigned_by_room: Dict[str, Dict[tuple, SeatAssignment]] = {}
    for a in assignments:
        assigned_by_room.setdefault(a.classroom_id, {})[(a.seat_row, a.seat_col)] = a

    rooms = db.query(Classroom).filter(
        Classroom.id.in_(assigned_by_room.keys()),
        Classroom.institution_id == institution_id
    ).all()

    students_by_id = {
        u.id: u for u in db.query(User).filter(User.institution_id == institution_id).all()
    }
    courses_by_id = {
        c.id: c for c in db.query(Course).filter(Course.institution_id == institution_id).all()
    }

    room_reports: List[RoomGridOut] = []
    for room in rooms:
        grid: List[List[SeatCell]] = []
        occupied_count = 0
        for r in range(room.rows):
            row_cells: List[SeatCell] = []
            for c in range(room.columns):
                desk_label = f"{room.room_number}-R{r+1}-C{c+1}"
                assignment = assigned_by_room.get(room.id, {}).get((r, c))
                if assignment:
                    occupied_count += 1
                    s = students_by_id.get(assignment.student_id)
                    co = courses_by_id.get(assignment.course_id)
                    row_cells.append(SeatCell(
                        row=r,
                        col=c,
                        desk_label=desk_label,
                        student_id=assignment.student_id,
                        student_name=s.full_name if s else "Student",
                        course_code=co.code if co else "COURSE",
                        is_occupied=True
                    ))
                else:
                    row_cells.append(SeatCell(
                        row=r,
                        col=c,
                        desk_label=desk_label,
                        student_id=None,
                        student_name=None,
                        course_code=None,
                        is_occupied=False
                    ))
            grid.append(row_cells)

        room_reports.append(RoomGridOut(
            classroom_id=room.id,
            classroom_name=room.name,
            building=room.building,
            room_number=room.room_number,
            rows=room.rows,
            columns=room.columns,
            total_seats=room.rows * room.columns,
            occupied_seats=occupied_count,
            grid=grid
        ))

    return SeatingArrangementReport(
        exam_session_id=exam.id,
        exam_name=exam.name,
        exam_date=exam.exam_date,
        total_students=len(assignments),
        total_seated=len(assignments),
        rooms=room_reports
    )
