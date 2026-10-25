from datetime import date
from app.models.seating import ExamSession, ExamEnrollment, SeatAssignment
from app.models.user import User, UserRole
from app.services.seating_engine import generate_exam_seating_arrangement


def test_anti_cheat_seating_interleaved(db_session, fixture_data):
    # 1. Create an Exam Session
    exam = ExamSession(
        id="exam-midterm-fall",
        institution_id=fixture_data["inst_a"].id,
        academic_term_id=fixture_data["term_a"].id,
        name="Midterm Exam Fall 2026",
        exam_date=date(2026, 10, 15),
        time_slot_id=fixture_data["slot_mon1"].id
    )
    db_session.add(exam)
    db_session.flush()

    # Create 6 students (3 taking CS101, 3 taking MATH201)
    students_cs = []
    students_math = []
    for i in range(3):
        sc = User(
            id=f"student-cs-{i}",
            institution_id=fixture_data["inst_a"].id,
            email=f"cs_{i}@alpha.edu",
            hashed_password="dummy",
            full_name=f"CS Student {i}",
            role=UserRole.STUDENT.value
        )
        sm = User(
            id=f"student-math-{i}",
            institution_id=fixture_data["inst_a"].id,
            email=f"math_{i}@alpha.edu",
            hashed_password="dummy",
            full_name=f"Math Student {i}",
            role=UserRole.STUDENT.value
        )
        students_cs.append(sc)
        students_math.append(sm)
        db_session.add_all([sc, sm])
    db_session.flush()

    # Enrollments
    for sc in students_cs:
        db_session.add(ExamEnrollment(
            institution_id=fixture_data["inst_a"].id,
            exam_session_id=exam.id,
            student_id=sc.id,
            course_id=fixture_data["course_cs101"].id
        ))
    for sm in students_math:
        db_session.add(ExamEnrollment(
            institution_id=fixture_data["inst_a"].id,
            exam_session_id=exam.id,
            student_id=sm.id,
            course_id=fixture_data["course_math201"].id
        ))
    db_session.commit()

    # Run Seating Engine
    result = generate_exam_seating_arrangement(
        db=db_session,
        institution_id=fixture_data["inst_a"].id,
        exam_session_id=exam.id,
        classroom_ids=[fixture_data["room_lh1"].id]
    )

    assert result["status"] == "SUCCESS"
    assert result["total_seated"] == 6

    # Verify no two adjacent seats share the same course
    assignments = db_session.query(SeatAssignment).filter(
        SeatAssignment.exam_session_id == exam.id
    ).all()
    matrix = {(a.seat_row, a.seat_col): a.course_id for a in assignments}

    for (r, c), course_id in matrix.items():
        # Check right neighbor
        if (r, c + 1) in matrix:
            assert matrix[(r, c + 1)] != course_id, f"Cheating risk at ({r},{c}) and ({r},{c+1}): same course {course_id}"
        # Check bottom neighbor
        if (r + 1, c) in matrix:
            assert matrix[(r + 1, c)] != course_id, f"Cheating risk at ({r},{c}) and ({r+1},{c}): same course {course_id}"


def test_single_course_checkerboard_spacing(db_session, fixture_data):
    exam = ExamSession(
        id="exam-single-course",
        institution_id=fixture_data["inst_a"].id,
        academic_term_id=fixture_data["term_a"].id,
        name="Single Course Exam",
        exam_date=date(2026, 11, 1),
        time_slot_id=fixture_data["slot_mon1"].id
    )
    db_session.add(exam)
    db_session.flush()

    # 4 students in CS101 only
    for i in range(4):
        s = User(
            id=f"student-single-{i}",
            institution_id=fixture_data["inst_a"].id,
            email=f"single_{i}@alpha.edu",
            hashed_password="dummy",
            full_name=f"Single Student {i}",
            role=UserRole.STUDENT.value
        )
        db_session.add(s)
        db_session.flush()
        db_session.add(ExamEnrollment(
            institution_id=fixture_data["inst_a"].id,
            exam_session_id=exam.id,
            student_id=s.id,
            course_id=fixture_data["course_cs101"].id
        ))
    db_session.commit()

    result = generate_exam_seating_arrangement(
        db=db_session,
        institution_id=fixture_data["inst_a"].id,
        exam_session_id=exam.id,
        classroom_ids=[fixture_data["room_lh1"].id]
    )

    assert result["status"] == "SUCCESS"
    assert result["total_seated"] == 4

    assignments = db_session.query(SeatAssignment).filter(
        SeatAssignment.exam_session_id == exam.id
    ).all()
    # Check checkerboard rule: each seated student has (row + col) % 2 == 0
    for a in assignments:
        assert (a.seat_row + a.seat_col) % 2 == 0, f"Seat ({a.seat_row}, {a.seat_col}) violates checkerboard rule"
