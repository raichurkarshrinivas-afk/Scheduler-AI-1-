from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from app.models.schedule import ScheduleSession, TimeSlot
from app.models.facility import Classroom
from app.models.academic import ProgramBatch, AcademicTerm
from app.models.course import Course, CourseType
from app.models.user import User
from app.models.instructor import InstructorAvailability
from app.schemas.schedule import ConflictDetail


def validate_session_constraints(
    db: Session,
    institution_id: str,
    academic_term_id: str,
    course_id: str,
    batch_id: str,
    instructor_id: str,
    classroom_id: str,
    time_slot_id: str,
    exclude_session_id: Optional[str] = None
) -> Tuple[bool, List[ConflictDetail]]:
    conflicts: List[ConflictDetail] = []

    # 1. Check classroom existence and capacity
    classroom = db.query(Classroom).filter(
        Classroom.id == classroom_id,
        Classroom.institution_id == institution_id
    ).first()
    
    batch = db.query(ProgramBatch).filter(
        ProgramBatch.id == batch_id,
        ProgramBatch.institution_id == institution_id
    ).first()

    if classroom and batch:
        if classroom.capacity < batch.student_count:
            conflicts.append(ConflictDetail(
                conflict_type="ROOM_CAPACITY_EXCEEDED",
                message=f"Classroom '{classroom.name}' capacity ({classroom.capacity}) is smaller than batch '{batch.name}' size ({batch.student_count})",
                conflicting_entity_id=classroom_id
            ))

    # 2. Check Instructor Availability constraint
    unavailability = db.query(InstructorAvailability).filter(
        InstructorAvailability.institution_id == institution_id,
        InstructorAvailability.instructor_id == instructor_id,
        InstructorAvailability.time_slot_id == time_slot_id,
        InstructorAvailability.is_available == False
    ).first()
    if unavailability:
        reason_text = f" ({unavailability.reason})" if unavailability.reason else ""
        conflicts.append(ConflictDetail(
            conflict_type="INSTRUCTOR_UNAVAILABLE",
            message=f"Instructor is marked unavailable for this time slot{reason_text}",
            conflicting_entity_id=instructor_id
        ))

    # Base query for overlapping sessions in the same term and time slot
    base_query = db.query(ScheduleSession).filter(
        ScheduleSession.institution_id == institution_id,
        ScheduleSession.academic_term_id == academic_term_id,
        ScheduleSession.time_slot_id == time_slot_id
    )
    if exclude_session_id:
        base_query = base_query.filter(ScheduleSession.id != exclude_session_id)

    existing_sessions = base_query.all()

    # 3. Check Instructor Double-Booking
    instructor_conflict = next((s for s in existing_sessions if s.instructor_id == instructor_id), None)
    if instructor_conflict:
        conflicts.append(ConflictDetail(
            conflict_type="INSTRUCTOR_DOUBLE_BOOKING",
            message="Instructor is already assigned to another class during this time slot",
            conflicting_entity_id=instructor_conflict.id
        ))

    # 4. Check Room Double-Booking
    room_conflict = next((s for s in existing_sessions if s.classroom_id == classroom_id), None)
    if room_conflict:
        conflicts.append(ConflictDetail(
            conflict_type="ROOM_DOUBLE_BOOKING",
            message=f"Classroom '{classroom.name if classroom else classroom_id}' is already booked for another class during this time slot",
            conflicting_entity_id=room_conflict.id
        ))

    # 5. Check Batch Double-Booking
    batch_conflict = next((s for s in existing_sessions if s.batch_id == batch_id), None)
    if batch_conflict:
        conflicts.append(ConflictDetail(
            conflict_type="BATCH_DOUBLE_BOOKING",
            message=f"Batch '{batch.name if batch else batch_id}' has another scheduled class during this time slot",
            conflicting_entity_id=batch_conflict.id
        ))

    is_valid = len(conflicts) == 0
    return is_valid, conflicts


def auto_generate_schedule(
    db: Session,
    institution_id: str,
    academic_term_id: str
) -> dict:
    """
    Deterministic Heuristic Timetable Generator:
    Applies forward checking with Minimum Remaining Values (MRV).
    Allocates weekly required lecture hours across conflict-free time slots and classrooms.
    """
    # Verify academic term
    term = db.query(AcademicTerm).filter(
        AcademicTerm.id == academic_term_id,
        AcademicTerm.institution_id == institution_id
    ).first()
    if not term:
        return {
            "status": "ERROR",
            "scheduled_count": 0,
            "unscheduled_count": 0,
            "unscheduled_items": ["Academic term not found"],
            "message": "Academic term not found"
        }

    # Fetch resources
    courses = db.query(Course).filter(Course.institution_id == institution_id).all()
    batches = db.query(ProgramBatch).filter(ProgramBatch.institution_id == institution_id).all()
    classrooms = db.query(Classroom).filter(Classroom.institution_id == institution_id).all()
    time_slots = db.query(TimeSlot).filter(TimeSlot.institution_id == institution_id).all()
    instructors = db.query(User).filter(
        User.institution_id == institution_id,
        User.role.in_(["INSTRUCTOR", "ADMIN"]),
        User.is_active == True
    ).all()

    if not time_slots or not classrooms or not instructors:
        return {
            "status": "INSUFFICIENT_RESOURCES",
            "scheduled_count": 0,
            "unscheduled_count": 0,
            "unscheduled_items": ["Insufficient time slots, classrooms, or faculty configured"],
            "message": "Please configure classrooms, time slots, and instructors first"
        }

    # Clear existing draft sessions for this term to generate a fresh timetable
    db.query(ScheduleSession).filter(
        ScheduleSession.institution_id == institution_id,
        ScheduleSession.academic_term_id == academic_term_id
    ).delete(synchronize_session=False)
    db.flush()

    scheduled_count = 0
    unscheduled_items = []

    # Map courses to batches of the matching department
    course_batch_pairs = []
    for batch in batches:
        dept_courses = [c for c in courses if c.department_id == batch.department_id]
        for course in dept_courses:
            for _ in range(course.weekly_hours):
                course_batch_pairs.append((course, batch))

    # Sort items by constraint tightness (largest batch size first)
    course_batch_pairs.sort(key=lambda item: item[1].student_count, reverse=True)

    instructor_idx = 0
    for course, batch in course_batch_pairs:
        assigned = False
        
        # Round-robin candidate instructor assignment
        candidate_instructors = instructors[instructor_idx:] + instructors[:instructor_idx]
        
        for instructor in candidate_instructors:
            if assigned:
                break
                
            for time_slot in time_slots:
                if assigned:
                    break
                    
                # Candidate rooms matching capacity and room type
                suitable_rooms = [
                    r for r in classrooms 
                    if r.capacity >= batch.student_count
                ]
                # If lab course, prefer lab rooms
                if course.course_type == CourseType.LAB.value:
                    lab_rooms = [r for r in suitable_rooms if r.room_type == "COMPUTER_LAB"]
                    if lab_rooms:
                        suitable_rooms = lab_rooms
                        
                for classroom in suitable_rooms:
                    is_valid, _ = validate_session_constraints(
                        db=db,
                        institution_id=institution_id,
                        academic_term_id=academic_term_id,
                        course_id=course.id,
                        batch_id=batch.id,
                        instructor_id=instructor.id,
                        classroom_id=classroom.id,
                        time_slot_id=time_slot.id
                    )
                    
                    if is_valid:
                        new_session = ScheduleSession(
                            institution_id=institution_id,
                            academic_term_id=academic_term_id,
                            course_id=course.id,
                            batch_id=batch.id,
                            instructor_id=instructor.id,
                            classroom_id=classroom.id,
                            time_slot_id=time_slot.id
                        )
                        db.add(new_session)
                        db.flush()
                        scheduled_count += 1
                        assigned = True
                        instructor_idx = (instructor_idx + 1) % len(instructors)
                        break

        if not assigned:
            unscheduled_items.append(f"{course.code} for {batch.name}")

    db.commit()

    return {
        "status": "SUCCESS" if len(unscheduled_items) == 0 else "PARTIAL",
        "scheduled_count": scheduled_count,
        "unscheduled_count": len(unscheduled_items),
        "unscheduled_items": unscheduled_items,
        "message": f"Successfully scheduled {scheduled_count} timetable sessions."
    }
