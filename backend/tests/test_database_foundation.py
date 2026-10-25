import pytest
from datetime import date, time, datetime, timezone
from sqlalchemy.exc import IntegrityError

from app.models import (
    Institution,
    User,
    Membership,
    UserRole,
    Department,
    AcademicTerm,
    Subject,
    SubjectType,
    CourseOffering,
    Section,
    Enrolment,
    EnrolmentStatus,
    Teacher,
    Student,
    TeacherQualification,
    Building,
    Room,
    RoomType,
    Seat,
    Workstation,
    Session,
    SessionType,
    SessionStatus,
    AvailabilityRule,
    TargetType,
    CalendarException,
    CalendarExceptionType,
    ConstraintRule,
    ConstraintType,
    AuditEvent,
)
from app.seeds.seed import run_seed
from app.core.timezone import validate_timezone, get_term_timezone, combine_term_datetime, from_utc_to_term


@pytest.fixture
def two_institutions(db_session):
    """Provides two clean isolated institutions."""
    inst1 = Institution(name="Alpha Institute", slug="alpha-inst", code="ALPHA", timezone="America/New_York")
    inst2 = Institution(name="Beta Polytechnic", slug="beta-poly", code="BETA", timezone="Europe/London")
    db_session.add_all([inst1, inst2])
    db_session.flush()
    return inst1, inst2


# ------------------------------------------------------------------------------
# 1. Tenant-Scoped Uniqueness Tests
# ------------------------------------------------------------------------------

def test_tenant_scoped_uniqueness_allows_same_code_across_different_tenants(db_session, two_institutions):
    """Two different institutions CAN use identical codes (e.g., 'CS', '2026-FALL', 'MAIN')."""
    inst1, inst2 = two_institutions

    # Same department code in two tenants
    dept1 = Department(institution_id=inst1.id, code="CS", name="Computer Science Alpha")
    dept2 = Department(institution_id=inst2.id, code="CS", name="Computer Science Beta")
    db_session.add_all([dept1, dept2])
    db_session.flush()

    # Same building code in two tenants
    bldg1 = Building(institution_id=inst1.id, code="MAIN", name="Alpha Main Hall")
    bldg2 = Building(institution_id=inst2.id, code="MAIN", name="Beta Main Hall")
    db_session.add_all([bldg1, bldg2])
    db_session.flush()

    # Same subject code in two tenants
    subj1 = Subject(institution_id=inst1.id, department_id=dept1.id, code="CS101", name="Alpha Intro")
    subj2 = Subject(institution_id=inst2.id, department_id=dept2.id, code="CS101", name="Beta Intro")
    db_session.add_all([subj1, subj2])
    db_session.flush()

    assert dept1.code == dept2.code == "CS"
    assert bldg1.code == bldg2.code == "MAIN"
    assert subj1.code == subj2.code == "CS101"


def test_tenant_scoped_uniqueness_rejects_duplicate_within_same_tenant(db_session, two_institutions):
    """Within the same institution, duplicate unique codes MUST be rejected with IntegrityError."""
    inst1, _ = two_institutions

    dept1 = Department(institution_id=inst1.id, code="CS", name="First CS Dept")
    db_session.add(dept1)
    db_session.flush()

    # Attempt duplicate code in same tenant
    dept2 = Department(institution_id=inst1.id, code="CS", name="Duplicate CS Dept")
    db_session.add(dept2)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


# ------------------------------------------------------------------------------
# 2. Cross-Tenant Relationship Rejection Tests
# ------------------------------------------------------------------------------

def test_cross_tenant_rejection_subject_referencing_foreign_department(db_session, two_institutions):
    """A Subject belonging to Institution 1 cannot reference a Department belonging to Institution 2."""
    inst1, inst2 = two_institutions

    dept_in_inst2 = Department(institution_id=inst2.id, code="ENG", name="Beta Engineering")
    db_session.add(dept_in_inst2)
    db_session.flush()

    # Subject belongs to inst1, but department belongs to inst2
    cross_subj = Subject(
        institution_id=inst1.id,
        department_id=dept_in_inst2.id,
        code="CS202",
        name="Illegal Cross-Tenant Subject",
    )
    db_session.add(cross_subj)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_cross_tenant_rejection_room_referencing_foreign_building(db_session, two_institutions):
    """A Room belonging to Institution 1 cannot reference a Building belonging to Institution 2."""
    inst1, inst2 = two_institutions

    bldg_in_inst2 = Building(institution_id=inst2.id, code="HALL-B", name="Beta Building")
    db_session.add(bldg_in_inst2)
    db_session.flush()

    # Room belongs to inst1, but building belongs to inst2
    cross_room = Room(
        institution_id=inst1.id,
        building_id=bldg_in_inst2.id,
        room_number="101",
        name="Cross-Tenant Room",
        physical_capacity=50,
        usable_exam_benches=25,
    )
    db_session.add(cross_room)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_cross_tenant_rejection_seat_referencing_foreign_room(db_session, two_institutions):
    """A Seat belonging to Institution 1 cannot reference a Room belonging to Institution 2."""
    inst1, inst2 = two_institutions

    bldg2 = Building(institution_id=inst2.id, code="B2", name="Building 2")
    db_session.add(bldg2)
    db_session.flush()

    room2 = Room(
        institution_id=inst2.id,
        building_id=bldg2.id,
        room_number="201",
        name="Room 2",
        physical_capacity=30,
        usable_exam_benches=15,
    )
    db_session.add(room2)
    db_session.flush()

    # Seat in inst1 referencing room in inst2
    cross_seat = Seat(
        institution_id=inst1.id,
        room_id=room2.id,
        row_num=1,
        col_num=1,
        bench_label="B-R1-C1",
    )
    db_session.add(cross_seat)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


def test_cross_tenant_rejection_enrolment_referencing_foreign_student(db_session, two_institutions):
    """An Enrolment in Institution 1 cannot enrol a Student belonging to Institution 2."""
    inst1, inst2 = two_institutions

    user1 = User(email="u1@test.edu", hashed_password="pwd", full_name="User One")
    user2 = User(email="u2@test.edu", hashed_password="pwd", full_name="User Two")
    db_session.add_all([user1, user2])
    db_session.flush()

    # Student belongs to inst2
    student_in_inst2 = Student(
        institution_id=inst2.id,
        user_id=user2.id,
        student_id_number="BETA-001",
        admission_year=2026,
    )
    db_session.add(student_in_inst2)

    # Section belongs to inst1
    dept1 = Department(institution_id=inst1.id, code="CS", name="Computer Science")
    term1 = AcademicTerm(institution_id=inst1.id, code="T1", name="Term 1", start_date=date(2026, 1, 1), end_date=date(2026, 6, 1), timezone="UTC")
    db_session.add_all([dept1, term1])
    db_session.flush()

    subj1 = Subject(institution_id=inst1.id, department_id=dept1.id, code="CS101", name="Intro")
    db_session.add(subj1)
    db_session.flush()

    off1 = CourseOffering(institution_id=inst1.id, subject_id=subj1.id, academic_term_id=term1.id)
    db_session.add(off1)
    db_session.flush()

    sec1 = Section(institution_id=inst1.id, course_offering_id=off1.id, name="Section A", capacity=30)
    db_session.add(sec1)
    db_session.flush()

    # Enrolment in inst1 referencing student from inst2
    cross_enrolment = Enrolment(
        institution_id=inst1.id,
        student_id=student_in_inst2.id,
        section_id=sec1.id,
        status=EnrolmentStatus.ENROLLED,
    )
    db_session.add(cross_enrolment)

    with pytest.raises(IntegrityError):
        db_session.flush()

    db_session.rollback()


# ------------------------------------------------------------------------------
# 3. Model Identity Separately from Institution Membership
# ------------------------------------------------------------------------------

def test_user_identity_separated_from_memberships(db_session, two_institutions):
    """A single user identity can belong to multiple institutions with different roles."""
    inst1, inst2 = two_institutions

    user = User(email="dr.feynman@science.org", hashed_password="pwd", full_name="Dr. Richard Feynman")
    db_session.add(user)
    db_session.flush()

    # Membership in Institution 1 as Teacher
    mem1 = Membership(institution_id=inst1.id, user_id=user.id, role=UserRole.TEACHER)
    # Membership in Institution 2 as Exam Controller
    mem2 = Membership(institution_id=inst2.id, user_id=user.id, role=UserRole.EXAM_CONTROLLER)
    db_session.add_all([mem1, mem2])
    db_session.flush()

    user_memberships = db_session.query(Membership).filter_by(user_id=user.id).all()
    assert len(user_memberships) == 2
    roles = {m.role for m in user_memberships}
    assert roles == {UserRole.TEACHER, UserRole.EXAM_CONTROLLER}


# ------------------------------------------------------------------------------
# 4. Capacity vs Exam Benches & Bench vs Workstation Distinctions
# ------------------------------------------------------------------------------

def test_room_physical_capacity_versus_usable_exam_benches(db_session, two_institutions):
    """Distinguishes physical lecture seating from usable examination benches."""
    inst1, _ = two_institutions
    bldg = Building(institution_id=inst1.id, code="SCI", name="Science")
    db_session.add(bldg)
    db_session.flush()

    hall = Room(
        institution_id=inst1.id,
        building_id=bldg.id,
        room_number="101",
        name="Grand Hall",
        room_type=RoomType.LECTURE_HALL,
        physical_capacity=100,      # Can seat 100 students for normal lectures
        usable_exam_benches=50,     # Only 50 benches usable for exams due to anti-cheat spacing
        grid_rows=10,
        grid_cols=10,
    )
    db_session.add(hall)
    db_session.flush()

    assert hall.physical_capacity == 100
    assert hall.usable_exam_benches == 50
    assert hall.physical_capacity >= hall.usable_exam_benches


def test_benches_with_usable_blocked_and_accessible_states(db_session, two_institutions):
    """Demonstrates bench states: usable, blocked (maintenance), accessible (wheelchair)."""
    inst1, _ = two_institutions
    bldg = Building(institution_id=inst1.id, code="SCI", name="Science")
    db_session.add(bldg)
    db_session.flush()

    room = Room(
        institution_id=inst1.id,
        building_id=bldg.id,
        room_number="102",
        name="Hall 102",
        room_type=RoomType.CLASSROOM,
        physical_capacity=30,
        usable_exam_benches=15,
    )
    db_session.add(room)
    db_session.flush()

    seat_regular = Seat(institution_id=inst1.id, room_id=room.id, row_num=1, col_num=1, bench_label="B1", is_usable_for_exam=True, is_blocked=False, is_accessible=False)
    seat_blocked = Seat(institution_id=inst1.id, room_id=room.id, row_num=1, col_num=2, bench_label="B2", is_usable_for_exam=False, is_blocked=True, is_accessible=False)
    seat_accessible = Seat(institution_id=inst1.id, room_id=room.id, row_num=1, col_num=3, bench_label="B3", is_usable_for_exam=True, is_blocked=False, is_accessible=True)
    db_session.add_all([seat_regular, seat_blocked, seat_accessible])
    db_session.flush()

    assert seat_regular.is_usable_for_exam is True
    assert seat_blocked.is_blocked is True
    assert seat_accessible.is_accessible is True


def test_practical_workstation_with_features(db_session, two_institutions):
    """Demonstrates practical laboratory workstation modeling with feature tags."""
    inst1, _ = two_institutions
    bldg = Building(institution_id=inst1.id, code="ENG", name="Engineering")
    db_session.add(bldg)
    db_session.flush()

    lab = Room(
        institution_id=inst1.id,
        building_id=bldg.id,
        room_number="LAB1",
        name="Robotics Lab",
        room_type=RoomType.COMPUTER_LAB,
        physical_capacity=20,
        usable_exam_benches=10,
    )
    db_session.add(lab)
    db_session.flush()

    ws = Workstation(
        institution_id=inst1.id,
        room_id=lab.id,
        workstation_number=1,
        label="WS-01",
        has_computer=True,
        operating_system="Ubuntu 24.04 LTS",
        features=["GPU", "ROS2", "Robotic Arm Interface"],
        is_active=True,
        is_accessible=True,
    )
    db_session.add(ws)
    db_session.flush()

    fetched = db_session.query(Workstation).filter_by(id=ws.id).first()
    assert "ROS2" in fetched.features
    assert fetched.operating_system == "Ubuntu 24.04 LTS"


# ------------------------------------------------------------------------------
# 5. Explicit Term Timezone Handling
# ------------------------------------------------------------------------------

def test_explicit_term_timezone_handling(two_institutions):
    """Validates term timezone validation, conversions, and UTC consistency."""
    inst1, inst2 = two_institutions

    assert validate_timezone(inst1.timezone) is True
    assert validate_timezone(inst2.timezone) is True
    assert validate_timezone("Invalid/Nowhere") is False

    ny_tz = get_term_timezone(inst1.timezone)
    london_tz = get_term_timezone(inst2.timezone)

    # Combine local date and time in term timezone into UTC
    event_date = date(2026, 10, 15)
    event_time = time(9, 0) # 09:00 AM New York time (EDT, UTC-4)
    utc_dt = combine_term_datetime(event_date, event_time, inst1.timezone)

    assert utc_dt.tzinfo == timezone.utc
    assert utc_dt.hour == 13  # 09:00 EDT + 4 hours = 13:00 UTC

    # Convert back to local term time
    local_dt = from_utc_to_term(utc_dt, inst1.timezone)
    assert local_dt.hour == 9
    assert local_dt.date() == event_date


# ------------------------------------------------------------------------------
# 6. Idempotent Seed Execution Test
# ------------------------------------------------------------------------------

def test_seed_command_runs_twice_idempotently(db_session):
    """Seed command must run twice consecutively without duplicating records or throwing errors."""
    # First seed run
    run_seed(db_session)
    count_inst_1 = db_session.query(Institution).count()
    count_users_1 = db_session.query(User).count()
    count_rooms_1 = db_session.query(Room).count()
    count_seats_1 = db_session.query(Seat).count()
    count_ws_1 = db_session.query(Workstation).count()
    count_sessions_1 = db_session.query(Session).count()

    # Second seed run
    run_seed(db_session)
    count_inst_2 = db_session.query(Institution).count()
    count_users_2 = db_session.query(User).count()
    count_rooms_2 = db_session.query(Room).count()
    count_seats_2 = db_session.query(Seat).count()
    count_ws_2 = db_session.query(Workstation).count()
    count_sessions_2 = db_session.query(Session).count()

    assert count_inst_1 == count_inst_2 == 2
    assert count_users_1 == count_users_2 == 12
    assert count_rooms_1 == count_rooms_2 == 2
    assert count_seats_1 == count_seats_2 == 30
    assert count_ws_1 == count_ws_2 == 4
    assert count_sessions_1 == count_sessions_2 == 2