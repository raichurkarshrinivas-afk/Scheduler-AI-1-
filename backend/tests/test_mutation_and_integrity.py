import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.institution import Institution
from app.models.academic import AcademicTerm
from app.models.schedule import TimetableDraft
from app.services.schedule_checker import ScheduleChecker
from app.services.theory_seating_engine import TheorySeatingEngine
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


def login_user(client: TestClient, email: str, institution_code: str = "APEX") -> str:
    resp = client.post("/api/v1/auth/login", json={
        "institution_code": institution_code,
        "identifier": email,
        "password": "DevSeed2026!#",
    })
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return resp.json()["csrf_token"]


# =========================================================================
# Mutation 1: Missing Session (Completeness Violation)
# =========================================================================
def test_mutation_missing_session():
    """
    Mutation Test: Deliberately omit a mandatory session from output assignments.
    Verifier must catch the missing session with rule 'COMPLETENESS'.
    """
    snapshot = {
        "sessions": [
            {"id": "s-1", "name": "Algorithms Lecture", "teacher_id": "t-1", "duration": 1},
            {"id": "s-2", "name": "Database Systems", "teacher_id": "t-2", "duration": 1},
            {"id": "s-3", "name": "Computer Networks", "teacher_id": "t-3", "duration": 1},
        ],
        "rooms": [{"id": "r-1", "name": "Room 101", "capacity": 50}],
        "teachers": [
            {"id": "t-1", "name": "Dr. Turing"},
            {"id": "t-2", "name": "Dr. Lovelace"},
            {"id": "t-3", "name": "Dr. Hopper"},
        ],
    }

    # Deliberate mutation: only s-1 and s-2 are scheduled; s-3 is missing
    mutated_assignments = [
        {"session_id": "s-1", "day": 0, "period": 1, "room_id": "r-1"},
        {"session_id": "s-2", "day": 0, "period": 2, "room_id": "r-1"},
    ]

    report = ScheduleChecker.validate(snapshot, mutated_assignments)
    assert report["is_valid"] is False
    assert report["total_required"] == 3
    assert report["total_assigned"] == 2
    assert report["violations_count"] >= 1

    missing_violations = [v for v in report["violations"] if v["rule"] == "COMPLETENESS"]
    assert len(missing_violations) == 1
    assert missing_violations[0]["session_id"] == "s-3"


# =========================================================================
# Mutation 2: Teacher Overlap (Double-booking)
# =========================================================================
def test_mutation_teacher_overlap():
    """
    Mutation Test: Deliberately assign one teacher to two different rooms at the exact same period.
    Verifier must detect 'TEACHER_OVERLAP'.
    """
    snapshot = {
        "sessions": [
            {"id": "s-101", "name": "Physics I", "teacher_id": "t-newton", "duration": 1},
            {"id": "s-102", "name": "Calculus I", "teacher_id": "t-newton", "duration": 1},
        ],
        "rooms": [
            {"id": "r-lab", "name": "Physics Lab", "capacity": 40},
            {"id": "r-hall", "name": "Lecture Hall 1", "capacity": 100},
        ],
        "teachers": [{"id": "t-newton", "name": "Sir Isaac Newton"}],
    }

    # Deliberate mutation: same teacher assigned at day 1, period 3 in two rooms
    mutated_assignments = [
        {"session_id": "s-101", "day": 1, "period": 3, "room_id": "r-lab"},
        {"session_id": "s-102", "day": 1, "period": 3, "room_id": "r-hall"},
    ]

    report = ScheduleChecker.validate(snapshot, mutated_assignments)
    assert report["is_valid"] is False
    teacher_violations = [v for v in report["violations"] if v["rule"] == "TEACHER_OVERLAP"]
    assert len(teacher_violations) >= 1
    assert "t-newton" in teacher_violations[0]["message"]


# =========================================================================
# Mutation 3: Room Overlap (Room Collision)
# =========================================================================
def test_mutation_room_overlap():
    """
    Mutation Test: Deliberately assign two distinct sessions to the same physical room in the same time slot.
    Verifier must detect 'ROOM_OVERLAP'.
    """
    snapshot = {
        "sessions": [
            {"id": "s-eng", "name": "English Composition", "teacher_id": "t-shakespeare", "duration": 1},
            {"id": "s-hist", "name": "World History", "teacher_id": "t-herodotus", "duration": 1},
        ],
        "rooms": [{"id": "r-auditorium", "name": "Main Auditorium", "capacity": 200}],
        "teachers": [
            {"id": "t-shakespeare", "name": "William Shakespeare"},
            {"id": "t-herodotus", "name": "Herodotus"},
        ],
    }

    # Deliberate mutation: both sessions placed in r-auditorium on Friday (day 4) period 2
    mutated_assignments = [
        {"session_id": "s-eng", "day": 4, "period": 2, "room_id": "r-auditorium"},
        {"session_id": "s-hist", "day": 4, "period": 2, "room_id": "r-auditorium"},
    ]

    report = ScheduleChecker.validate(snapshot, mutated_assignments)
    assert report["is_valid"] is False
    room_violations = [v for v in report["violations"] if v["rule"] == "ROOM_OVERLAP"]
    assert len(room_violations) >= 1
    assert "r-auditorium" in room_violations[0]["message"]


# =========================================================================
# Mutation 4: Wrong Duration (Duration Mismatch)
# =========================================================================
def test_mutation_wrong_duration():
    """
    Mutation Test: Deliberately truncate a multi-period practical session.
    Verifier must detect 'DURATION_MISMATCH'.
    """
    snapshot = {
        "sessions": [
            {"id": "s-chem-lab", "name": "Organic Chemistry Lab", "teacher_id": "t-curie", "duration": 2},
        ],
        "rooms": [{"id": "r-chem", "name": "Chemistry Lab 1", "capacity": 30}],
        "teachers": [{"id": "t-curie", "name": "Marie Curie"}],
    }

    # Deliberate mutation: scheduled with duration 1 instead of required 2
    mutated_assignments = [
        {"session_id": "s-chem-lab", "day": 2, "period": 1, "room_id": "r-chem", "duration": 1},
    ]

    report = ScheduleChecker.validate(snapshot, mutated_assignments)
    assert report["is_valid"] is False
    duration_violations = [v for v in report["violations"] if v["rule"] == "DURATION_MISMATCH"]
    assert len(duration_violations) >= 1
    assert "duration is 1, expected 2" in duration_violations[0]["message"]


# =========================================================================
# Mutation 5: Duplicate Candidate in Theory Exam Seating
# =========================================================================
def test_mutation_duplicate_candidate():
    """
    Mutation Test: Deliberately assign a candidate to two separate benches in the same sitting.
    Seating verifier must detect 'DUPLICATE_CANDIDATE'.
    """
    snapshot = {
        "sitting_id": "exam-cs101-final",
        "candidates": [
            {"id": "cand-001", "name": "Alice Smith", "roll_number": "CS2026-001", "paper_id": "paper-cs101"},
            {"id": "cand-002", "name": "Bob Jones", "roll_number": "CS2026-002", "paper_id": "paper-cs101"},
        ],
        "rooms": [
            {
                "id": "hall-a",
                "name": "Examination Hall A",
                "seats": [
                    {"id": "bench-1", "row_num": 1, "col_num": 1, "is_usable": True, "is_blocked": False},
                    {"id": "bench-2", "row_num": 1, "col_num": 2, "is_usable": True, "is_blocked": False},
                    {"id": "bench-3", "row_num": 2, "col_num": 1, "is_usable": True, "is_blocked": False},
                ],
            }
        ],
    }

    # Deliberate mutation: cand-001 is assigned to BOTH bench-1 and bench-2
    mutated_allocations = [
        {"candidate_id": "cand-001", "room_id": "hall-a", "seat_id": "bench-1"},
        {"candidate_id": "cand-001", "room_id": "hall-a", "seat_id": "bench-2"},
    ]

    report = TheorySeatingEngine.verify_theory_seating(snapshot, mutated_allocations)
    assert report["is_valid"] is False
    dup_violations = [v for v in report["violations"] if v["rule"] == "DUPLICATE_CANDIDATE"]
    assert len(dup_violations) >= 1
    assert dup_violations[0]["candidate_id"] == "cand-001"


# =========================================================================
# Mutation 6: Candidate Assigned to Blocked Bench
# =========================================================================
def test_mutation_blocked_seat():
    """
    Mutation Test: Deliberately allocate a candidate to a bench marked broken/blocked.
    Seating verifier must detect 'BLOCKED_SEAT'.
    """
    snapshot = {
        "sitting_id": "exam-math-final",
        "candidates": [
            {"id": "cand-010", "name": "Charlie Brown", "roll_number": "MTH-010", "paper_id": "paper-math"},
        ],
        "rooms": [
            {
                "id": "hall-b",
                "name": "Examination Hall B",
                "seats": [
                    {"id": "bench-broken", "row_num": 1, "col_num": 1, "is_usable_for_exam": False, "is_blocked": True},
                ],
            }
        ],
    }

    mutated_allocations = [
        {"candidate_id": "cand-010", "room_id": "hall-b", "seat_id": "bench-broken"},
    ]

    report = TheorySeatingEngine.verify_theory_seating(snapshot, mutated_allocations)
    assert report["is_valid"] is False
    blocked_violations = [v for v in report["violations"] if v["rule"] == "BLOCKED_SEAT"]
    assert len(blocked_violations) >= 1
    assert blocked_violations[0]["seat_id"] == "bench-broken"


# =========================================================================
# Mutation 7: Stale Revision (Optimistic Concurrency Protection)
# =========================================================================
def test_mutation_stale_revision(client, seeded_db):
    """
    Mutation Test: Attempt to update draft assignment with an outdated expected revision.
    API must reject with HTTP 409 Conflict and preserve database integrity.
    """
    csrf = login_user(client, "coord@apex.edu", "APEX")
    headers = {"X-CSRF-Token": csrf}

    inst = seeded_db.query(Institution).filter(Institution.code == "APEX").first()
    term = seeded_db.query(AcademicTerm).filter(AcademicTerm.institution_id == inst.id).first()

    # Create a draft at revision 2
    draft = TimetableDraft(
        institution_id=inst.id,
        academic_term_id=term.id,
        name="Revision Mutation Test Draft",
        status="CHECKED",
        revision=2,
        input_hash="hash-mut-rev",
        input_snapshot={
            "sessions": [{"id": "s-rev", "name": "Rev Session", "duration": 1}],
            "rooms": [{"id": "r-rev", "name": "Room Rev", "capacity": 50}],
            "teachers": [{"id": "t-rev", "name": "Dr. Rev"}],
        },
        output_assignments=[
            {"session_id": "s-rev", "day": 0, "period": 1, "room_id": "r-rev"}
        ],
        is_published=False,
    )
    seeded_db.add(draft)
    seeded_db.commit()
    seeded_db.refresh(draft)

    # Client attempts update claiming expected_revision = 1 (stale revision) via PATCH
    resp = client.patch(
        f"/api/v1/timetable-drafts/{draft.id}/assignments/s-rev",
        headers=headers,
        json={
            "expected_revision": 1,
            "day": 2,
            "period": 3,
            "room_id": "r-rev",
        },
    )

    assert resp.status_code == 409
    assert "revision" in resp.json()["detail"].lower()

    # Verify draft in DB remains strictly at revision 2 and assignments unchanged
    seeded_db.expire_all()
    unchanged_draft = seeded_db.query(TimetableDraft).filter(TimetableDraft.id == draft.id).first()
    assert unchanged_draft.revision == 2
    assert unchanged_draft.output_assignments[0]["day"] == 0
    assert unchanged_draft.output_assignments[0]["period"] == 1


# =========================================================================
# Mutation 8: Cross-Tenant Identifier Injection
# =========================================================================
def test_mutation_cross_tenant_identifier(client, seeded_db):
    """
    Mutation Test: Coordinator from BEACON attempts to inspect, modify, or target an APEX draft.
    Must be rejected with HTTP 403 Forbidden or HTTP 404 Not Found to prevent data leakage.
    """
    inst_apex = seeded_db.query(Institution).filter(Institution.code == "APEX").first()
    term_apex = seeded_db.query(AcademicTerm).filter(AcademicTerm.institution_id == inst_apex.id).first()

    # Draft belongs to APEX
    apex_draft = TimetableDraft(
        institution_id=inst_apex.id,
        academic_term_id=term_apex.id,
        name="APEX Protected Draft",
        status="DRAFT",
        revision=1,
        input_hash="hash-apex-prot",
        input_snapshot={"sessions": [], "rooms": [], "teachers": []},
        output_assignments=[],
        is_published=False,
    )
    seeded_db.add(apex_draft)
    seeded_db.commit()
    seeded_db.refresh(apex_draft)

    # Login as BEACON coordinator
    beacon_csrf = login_user(client, "coord@beacon.edu", "BEACON")
    beacon_headers = {"X-CSRF-Token": beacon_csrf}

    # Attempt 1: Read APEX draft
    read_resp = client.get(f"/api/v1/timetable-drafts/{apex_draft.id}", headers=beacon_headers)
    assert read_resp.status_code in [403, 404]

    # Attempt 2: Generate APEX draft
    gen_resp = client.post(f"/api/v1/timetable-drafts/{apex_draft.id}/generate", headers=beacon_headers, json={})
    assert gen_resp.status_code in [403, 404]

    # Attempt 3: AI interpret targeting APEX draft
    ai_resp = client.post("/api/v1/ai/interpret-change", headers=beacon_headers, json={
        "draft_id": apex_draft.id,
        "request_text": "Move class to Tuesday",
    })
    assert ai_resp.status_code in [403, 404]
