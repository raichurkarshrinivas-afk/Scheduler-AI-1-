import pytest
from datetime import datetime, timezone, date
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.academic import AcademicTerm
from app.models.schedule import TimetableDraft, CalendarException, CalendarExceptionType
from app.models.exam import ExamSitting, ExamType
from app.models.people import Student
from app.models.publication import Publication, SharedResourceReservation, CommunicationOutbox
from app.seeds.seed import run_seed


@pytest.fixture(scope="module")
def seeded_db():
    db = SessionLocal()
    run_seed(db)
    yield db
    db.close()


@pytest.fixture
def client(seeded_db):
    return TestClient(app, base_url="http://testserver")


def login_user(client: TestClient, email: str) -> str:
    resp = client.post("/api/v1/auth/login", json={
        "institution_code": "APEX",
        "identifier": email,
        "password": "DevSeed2026!#",
    })
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["csrf_token"]


def test_students_cannot_see_drafts(client):
    """Acceptance 1: Students cannot see unpublished drafts."""
    coord_csrf = login_user(client, "coord@apex.edu")
    headers = {"X-CSRF-Token": coord_csrf}

    db = SessionLocal()
    term = db.query(AcademicTerm).filter(AcademicTerm.name == "Fall Semester 2026").first()
    term_id = term.id
    db.close()

    # Create an unpublished draft
    snapshot = {
        "sessions": [{"id": "s-secret", "name": "Secret Unreleased Lecture", "section_id": "sec-cs-a", "teacher_id": "t-1"}],
        "rooms": [{"id": "r-1", "name": "Room 101"}],
        "teachers": [{"id": "t-1", "name": "Prof Secret"}],
        "sections": [{"id": "sec-cs-a", "name": "CS Section A"}],
    }
    assignments = [{"session_id": "s-secret", "day": 0, "period": 1, "room_id": "r-1"}]

    create_resp = client.post("/api/v1/timetable-drafts", json={
        "name": "Unpublished Draft",
        "academic_term_id": term_id,
        "input_snapshot": snapshot,
    }, headers=headers)
    assert create_resp.status_code == 201
    draft_id = create_resp.json()["id"]

    # Student logs in
    student_csrf = login_user(client, "alice@apex.edu")
    s_headers = {"X-CSRF-Token": student_csrf}

    # Attempt to view timetable
    tt_resp = client.get("/api/v1/student/timetable", headers=s_headers)
    assert tt_resp.status_code == 200
    data = tt_resp.json()

    # Draft content must NOT be visible!
    assert "Secret Unreleased Lecture" not in str(data)


def test_stale_revision_publication_rejected(client):
    """Acceptance 2: Publication with mismatched/stale expected_revision is rejected."""
    coord_csrf = login_user(client, "coord@apex.edu")
    headers = {"X-CSRF-Token": coord_csrf}

    db = SessionLocal()
    term = db.query(AcademicTerm).first()
    term_id = term.id
    db.close()

    snapshot = {
        "sessions": [{"id": "s-1", "name": "Algorithm Design", "section_id": "sec-1", "teacher_id": "t-1"}],
        "rooms": [{"id": "r-1", "name": "Hall 1", "capacity": 50}],
        "teachers": [{"id": "t-1", "name": "Dr. Turing"}],
        "sections": [{"id": "sec-1", "name": "CS-1"}],
    }
    assignments = [{"session_id": "s-1", "day": 0, "period": 0, "room_id": "r-1"}]

    create_resp = client.post("/api/v1/timetable-drafts", json={
        "name": "Stale Revision Test Draft",
        "academic_term_id": term_id,
        "input_snapshot": snapshot,
    }, headers=headers)
    draft = create_resp.json()
    draft_id = draft["id"]
    current_rev = draft["revision"]

    # Initialize assignment in draft
    db = SessionLocal()
    d_init = db.query(TimetableDraft).filter(TimetableDraft.id == draft_id).first()
    d_init.output_assignments = [{"session_id": "s-1", "day": 0, "period": 0, "room_id": "r-1"}]
    d_init.status = "CHECKED"
    db.commit()
    db.close()

    # Move assignment to increment revision to revision + 1
    move_resp = client.patch(f"/api/v1/timetable-drafts/{draft_id}/assignments/s-1", json={
        "expected_revision": current_rev,
        "day": 1,
        "period": 0,
        "room_id": "r-1",
    }, headers=headers)
    assert move_resp.status_code == 200
    updated_draft = move_resp.json()
    assert updated_draft["revision"] == current_rev + 1

    # Attempt to publish with STALE expected_revision
    pub_resp = client.post("/api/v1/publications/publish", json={
        "draft_id": draft_id,
        "publication_type": "TIMETABLE",
        "expected_revision": current_rev,  # Stale!
        "publication_note": "Stale publication attempt",
    }, headers=headers)
    assert pub_resp.status_code == 409
    assert "Stale revision" in pub_resp.json()["detail"]


def test_two_competing_publications_cannot_double_book_same_resource(client):
    """Acceptance 3: Two competing publications cannot double-book the same shared resource."""
    import uuid
    coord_csrf = login_user(client, "coord@apex.edu")
    headers = {"X-CSRF-Token": coord_csrf}

    db = SessionLocal()
    term = db.query(AcademicTerm).first()
    term_id = term.id
    db.close()

    shared_room_id = f"room-compete-{uuid.uuid4().hex[:6]}"

    # Draft A books shared room on Monday Period 0
    snap_a = {
        "sessions": [{"id": "sess-a", "name": "Physics Class", "section_id": "sec-phy", "teacher_id": "t-phy"}],
        "rooms": [{"id": shared_room_id, "name": "Shared Lab 101", "capacity": 50}],
        "teachers": [{"id": "t-phy", "name": "Prof Newton"}],
        "sections": [{"id": "sec-phy", "name": "PHY-A"}],
    }
    draft_a_resp = client.post("/api/v1/timetable-drafts", json={
        "name": "Schedule A", "academic_term_id": term_id, "input_snapshot": snap_a,
    }, headers=headers)
    draft_a = draft_a_resp.json()

    # Draft B ALSO books the SAME room on Monday Period 0
    snap_b = {
        "sessions": [{"id": "sess-b", "name": "Chemistry Class", "section_id": "sec-chm", "teacher_id": "t-chm"}],
        "rooms": [{"id": shared_room_id, "name": "Shared Lab 101", "capacity": 50}],
        "teachers": [{"id": "t-chm", "name": "Prof Curie"}],
        "sections": [{"id": "sec-chm", "name": "CHM-A"}],
    }
    draft_b_resp = client.post("/api/v1/timetable-drafts", json={
        "name": "Schedule B", "academic_term_id": term_id, "input_snapshot": snap_b,
    }, headers=headers)
    draft_b = draft_b_resp.json()

    # Step 1: Assign Draft A and Publish it successfully
    db = SessionLocal()
    da = db.query(TimetableDraft).filter(TimetableDraft.id == draft_a["id"]).first()
    da.output_assignments = [{"session_id": "sess-a", "day": 0, "period": 0, "room_id": shared_room_id}]
    da.status = "CHECKED"
    db.commit()
    db.close()

    draft_a_fresh = client.get(f"/api/v1/timetable-drafts/{draft_a['id']}", headers=headers).json()

    pub_a_resp = client.post("/api/v1/publications/publish", json={
        "draft_id": draft_a["id"], "publication_type": "TIMETABLE",
        "expected_revision": draft_a_fresh["revision"], "publication_note": "Published Schedule A",
    }, headers=headers)
    assert pub_a_resp.status_code == 201

    # Step 2: Assign Draft B to the SAME room and period
    db = SessionLocal()
    db_b = db.query(TimetableDraft).filter(TimetableDraft.id == draft_b["id"]).first()
    db_b.output_assignments = [{"session_id": "sess-b", "day": 0, "period": 0, "room_id": shared_room_id}]
    db_b.status = "CHECKED"
    db.commit()
    db.close()

    draft_b_fresh = client.get(f"/api/v1/timetable-drafts/{draft_b['id']}", headers=headers).json()

    # Step 3: Attempting to publish Draft B MUST BE REJECTED due to reservation collision!
    pub_b_resp = client.post("/api/v1/publications/publish", json={
        "draft_id": draft_b["id"], "publication_type": "TIMETABLE",
        "expected_revision": draft_b_fresh["revision"], "publication_note": "Competing publish",
    }, headers=headers)
    assert pub_b_resp.status_code == 409
    assert "RESOURCE_RESERVATION_CONFLICT" in pub_b_resp.json()["detail"]


def test_history_preserved_and_restored_version_rechecked(client):
    """Acceptance 4: Rollback/restore preserves publication history and re-checks restored content."""
    coord_csrf = login_user(client, "coord@apex.edu")
    headers = {"X-CSRF-Token": coord_csrf}

    db = SessionLocal()
    term = db.query(AcademicTerm).first()
    term_id = term.id
    db.close()

    snap = {
        "sessions": [{"id": "s-hist", "name": "History Lecture", "section_id": "sec-hist", "teacher_id": "t-hist"}],
        "rooms": [{"id": "r-hist-uniq", "name": "Room Hist 1", "capacity": 40}],
        "teachers": [{"id": "t-hist", "name": "Prof History"}],
        "sections": [{"id": "sec-hist", "name": "HIST-1"}],
    }

    create_resp = client.post("/api/v1/timetable-drafts", json={
        "name": "Version History Draft", "academic_term_id": term_id, "input_snapshot": snap,
    }, headers=headers)
    draft_id = create_resp.json()["id"]

    # Place assignment and publish Version 1
    db = SessionLocal()
    db.query(SharedResourceReservation).filter(SharedResourceReservation.resource_id == 'r-hist-uniq').delete()
    db.commit()
    dh = db.query(TimetableDraft).filter(TimetableDraft.id == draft_id).first()
    dh.output_assignments = [{"session_id": "s-hist", "day": 5, "period": 7, "room_id": "r-hist-uniq"}]
    dh.status = "CHECKED"
    db.commit()
    db.close()

    draft_fresh = client.get(f"/api/v1/timetable-drafts/{draft_id}", headers=headers).json()

    pub_resp = client.post("/api/v1/publications/publish", json={
        "draft_id": draft_id, "publication_type": "TIMETABLE",
        "expected_revision": draft_fresh["revision"], "publication_note": "Initial Release Version 1",
    }, headers=headers)
    assert pub_resp.status_code == 201
    pub_v1 = pub_resp.json()
    v1_id = pub_v1["id"]

    # Restore Version 1 as a NEW draft
    restore_resp = client.post(f"/api/v1/publications/{v1_id}/restore", headers=headers)
    assert restore_resp.status_code == 201
    restored_draft = restore_resp.json()

    # Acceptance: Restored content must be a new draft, revision 1, independent checker ran
    assert restored_draft["revision"] == 1
    assert restored_draft["is_published"] == False
    assert restored_draft["status"] == "CHECKED"
    assert "validation_report" in restored_draft
    assert restored_draft["validation_report"]["is_valid"] == True

    # Acceptance: Publication history is completely preserved!
    history_resp = client.get("/api/v1/publications", headers=headers)
    assert history_resp.status_code == 200
    pub_ids = [p["id"] for p in history_resp.json()]
    assert v1_id in pub_ids


def test_student_browser_journey_and_privacy_safeguards(client):
    """
    Acceptance 5 & 6:
    - Students cannot query another student's data.
    - Student journey displays real published assignments and exact seats.
    """
    # 1. Staff publishes theory exam sitting with exact candidate bench
    ctrl_csrf = login_user(client, "exam@apex.edu")
    headers = {"X-CSRF-Token": ctrl_csrf}

    db = SessionLocal()
    term = db.query(AcademicTerm).first()
    term_id = term.id
    # Look up Alice's student ID number
    alice_stu = db.query(Student).filter(Student.student_id_number == "APEX-STU-2026-001").first()
    assert alice_stu is not None
    alice_roll = alice_stu.student_id_number
    db.close()

    exam_snap = {
        "candidates": [
            {
                "id": "cand-alice", "roll_number": alice_roll, "name": "Alice Miller",
                "paper_code": "CS-FINAL-2026", "paper_name": "Distributed Systems",
                "requires_accessible_seat": True, "accessibility_notes": "Ground floor aisle seat",
                "private_accommodations": "CONFIDENTIAL MEDICAL NOTE: DO NOT DISCLOSE",
            },
            {
                "id": "cand-bob", "roll_number": "APEX-STU-2026-002", "name": "Bob Vance",
                "paper_code": "CS-FINAL-2026", "paper_name": "Distributed Systems",
            }
        ],
        "rooms": [{
            "id": "hall-omega", "name": "Omega Examination Hall",
            "seats": [
                {"id": "bench-om-1", "row_num": 1, "col_num": 1, "bench_label": "Omega-A1", "is_usable_for_exam": True, "is_blocked": False, "is_accessible": True},
                {"id": "bench-om-2", "row_num": 1, "col_num": 2, "bench_label": "Omega-A2", "is_usable_for_exam": True, "is_blocked": False, "is_accessible": False},
            ]
        }]
    }

    sitting_resp = client.post("/api/v1/exams/theory/sittings", json={
        "name": "Official Winter Theory Finals", "academic_term_id": term_id, "input_snapshot": exam_snap,
    }, headers=headers)
    assert sitting_resp.status_code == 201
    sitting_id = sitting_resp.json()["id"]

    # Allocate seating
    alloc_resp = client.post(f"/api/v1/exams/theory/sittings/{sitting_id}/allocate", headers=headers)
    assert alloc_resp.status_code == 200
    sitting_fresh = alloc_resp.json()

    # Publish the exam sitting
    pub_exam_resp = client.post("/api/v1/publications/publish", json={
        "draft_id": sitting_id, "publication_type": "EXAM_THEORY",
        "expected_revision": sitting_fresh["revision"], "publication_note": "Finals Seating Released",
    }, headers=headers)
    assert pub_exam_resp.status_code == 201

    # 2. Alice Miller logs in
    student_csrf = login_user(client, "alice@apex.edu")
    s_headers = {"X-CSRF-Token": student_csrf}

    # Verify Profile
    profile_resp = client.get("/api/v1/student/me", headers=s_headers)
    assert profile_resp.status_code == 200
    p = profile_resp.json()
    assert p["roll_number"] == alice_roll
    assert p["email"] == "alice@apex.edu"

    # Verify Home Dashboard
    home_resp = client.get("/api/v1/student/home", headers=s_headers)
    assert home_resp.status_code == 200
    home = home_resp.json()
    assert home["profile"]["roll_number"] == alice_roll

    # Verify Exam Seats: MUST return EXACT SEAT DETAILS for Alice
    exams_resp = client.get("/api/v1/student/exams", headers=s_headers)
    assert exams_resp.status_code == 200
    seats = exams_resp.json()
    assert len(seats) >= 1
    alice_seat = seats[0]

    assert alice_seat["hall_name"] == "Omega Examination Hall"
    assert alice_seat["bench_label"] == "Omega-A1"
    assert alice_seat["paper_code"] == "CS-FINAL-2026"
    assert alice_seat["is_accessible"] == True

    # PRIVACY SAFEGUARD: Confirm confidential note is NEVER exposed to the student endpoint
    assert "CONFIDENTIAL MEDICAL NOTE" not in str(alice_seat)

    # ACCEPTANCE: Students cannot query another student's data by tampering query parameters
    tamper_resp = client.get("/api/v1/student/exams?student_id=cand-bob&roll_number=APEX-STU-2026-002", headers=s_headers)
    assert tamper_resp.status_code == 200
    tamper_data = tamper_resp.json()
    # Still returns Alice's seat only! Bob's seat is never returned.
    assert tamper_data[0]["bench_label"] == "Omega-A1"
    assert "Omega-A2" not in str(tamper_data)
