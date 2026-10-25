from app.services.scheduling_engine import validate_session_constraints, auto_generate_schedule
from app.models.schedule import ScheduleSession
from app.models.instructor import InstructorAvailability
from app.models.facility import Classroom


def test_conflict_room_capacity_exceeded(db_session, fixture_data):
    # Create a small classroom with capacity 10
    small_room = Classroom(
        id="room-small",
        institution_id=fixture_data["inst_a"].id,
        name="Small Room",
        building="Main",
        room_number="SR-1",
        capacity=10,
        rows=2,
        columns=5
    )
    db_session.add(small_room)
    db_session.commit()

    # Batch has student_count = 25
    is_valid, conflicts = validate_session_constraints(
        db=db_session,
        institution_id=fixture_data["inst_a"].id,
        academic_term_id=fixture_data["term_a"].id,
        course_id=fixture_data["course_cs101"].id,
        batch_id=fixture_data["batch_cs1"].id,
        instructor_id=fixture_data["instructor_a"].id,
        classroom_id=small_room.id,
        time_slot_id=fixture_data["slot_mon1"].id
    )

    assert not is_valid
    types = [c.conflict_type for c in conflicts]
    assert "ROOM_CAPACITY_EXCEEDED" in types


def test_conflict_instructor_unavailable(db_session, fixture_data):
    # Mark instructor unavailable on slot_mon1
    unavail = InstructorAvailability(
        institution_id=fixture_data["inst_a"].id,
        instructor_id=fixture_data["instructor_a"].id,
        day_of_week="MON",
        time_slot_id=fixture_data["slot_mon1"].id,
        is_available=False,
        reason="Faculty Academic Council Meeting"
    )
    db_session.add(unavail)
    db_session.commit()

    is_valid, conflicts = validate_session_constraints(
        db=db_session,
        institution_id=fixture_data["inst_a"].id,
        academic_term_id=fixture_data["term_a"].id,
        course_id=fixture_data["course_cs101"].id,
        batch_id=fixture_data["batch_cs1"].id,
        instructor_id=fixture_data["instructor_a"].id,
        classroom_id=fixture_data["room_lh1"].id,
        time_slot_id=fixture_data["slot_mon1"].id
    )

    assert not is_valid
    types = [c.conflict_type for c in conflicts]
    assert "INSTRUCTOR_UNAVAILABLE" in types


def test_conflict_instructor_and_room_double_booking(db_session, fixture_data):
    # Existing session booked in slot_mon1
    existing = ScheduleSession(
        institution_id=fixture_data["inst_a"].id,
        academic_term_id=fixture_data["term_a"].id,
        course_id=fixture_data["course_cs101"].id,
        batch_id=fixture_data["batch_cs1"].id,
        instructor_id=fixture_data["instructor_a"].id,
        classroom_id=fixture_data["room_lh1"].id,
        time_slot_id=fixture_data["slot_mon1"].id
    )
    db_session.add(existing)
    db_session.commit()

    # Another session trying to use the same instructor and room in slot_mon1
    is_valid, conflicts = validate_session_constraints(
        db=db_session,
        institution_id=fixture_data["inst_a"].id,
        academic_term_id=fixture_data["term_a"].id,
        course_id=fixture_data["course_math201"].id,
        batch_id="another-batch-id",
        instructor_id=fixture_data["instructor_a"].id,
        classroom_id=fixture_data["room_lh1"].id,
        time_slot_id=fixture_data["slot_mon1"].id
    )

    assert not is_valid
    types = [c.conflict_type for c in conflicts]
    assert "INSTRUCTOR_DOUBLE_BOOKING" in types
    assert "ROOM_DOUBLE_BOOKING" in types


def test_valid_session_no_conflicts(db_session, fixture_data):
    # Slot MON 2 is completely free
    is_valid, conflicts = validate_session_constraints(
        db=db_session,
        institution_id=fixture_data["inst_a"].id,
        academic_term_id=fixture_data["term_a"].id,
        course_id=fixture_data["course_cs101"].id,
        batch_id=fixture_data["batch_cs1"].id,
        instructor_id=fixture_data["instructor_a"].id,
        classroom_id=fixture_data["room_lh1"].id,
        time_slot_id=fixture_data["slot_mon2"].id
    )

    assert is_valid
    assert len(conflicts) == 0


def test_heuristic_scheduler_engine(db_session, fixture_data):
    result = auto_generate_schedule(
        db=db_session,
        institution_id=fixture_data["inst_a"].id,
        academic_term_id=fixture_data["term_a"].id
    )
    assert result["status"] in ["SUCCESS", "PARTIAL"]
    assert result["scheduled_count"] > 0
