import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.schedule import TimetableDraft
from app.models.institution import Institution
from app.models.academic import AcademicTerm
from app.models.user import UserRole
from app.services.schedule_solver import ScheduleSolver
from app.services.schedule_checker import ScheduleChecker
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


def login_coordinator(client: TestClient) -> str:
    resp = client.post("/api/v1/auth/login", json={
        "institution_code": "APEX",
        "identifier": "coord@apex.edu",
        "password": "DevSeed2026!#",
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["csrf_token"]


def get_term_id() -> str:
    db = SessionLocal()
    term = db.query(AcademicTerm).first()
    term_id = term.id if term else "term-1"
    db.close()
    return term_id


def test_assignment_edit_and_revision_increment(client):
    csrf = login_coordinator(client)
    headers = {"X-CSRF-Token": csrf}
    term_id = get_term_id()

    snapshot = {
        "days": [0, 1, 2, 3, 4],
        "periods_per_day": 8,
        "sessions": [
            {"id": "sess-math", "name": "Mathematics", "duration": 1, "teacher_id": "prof-1", "section_id": "sec-a", "min_capacity": 30},
            {"id": "sess-phys", "name": "Physics", "duration": 1, "teacher_id": "prof-2", "section_id": "sec-b", "min_capacity": 30},
        ],
        "rooms": [
            {"id": "room-101", "name": "Room 101", "capacity": 40, "room_type": None, "features": []},
            {"id": "room-102", "name": "Room 102", "capacity": 40, "room_type": None, "features": []},
        ],
        "teachers": [
            {"id": "prof-1", "name": "Prof 1"},
            {"id": "prof-2", "name": "Prof 2"},
        ],
    }

    create_resp = client.post(
        "/api/v1/timetable-drafts",
        json={
            "name": "Revision Test Draft",
            "academic_term_id": term_id,
            "input_snapshot": snapshot,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    draft_data = create_resp.json()
    draft_id = draft_data["id"]
    assert draft_data["revision"] == 1

    solve_result = ScheduleSolver.solve(snapshot)
    assert solve_result["solver_status"] in ("OPTIMAL", "FEASIBLE")

    db = SessionLocal()
    draft = db.query(TimetableDraft).filter(TimetableDraft.id == draft_id).first()
    draft.output_assignments = solve_result["assignments"]
    draft.status = "CHECKED"
    db.commit()
    db.close()

    # Update assignment with correct expected_revision (1)
    edit_resp = client.patch(
        f"/api/v1/timetable-drafts/{draft_id}/assignments/sess-math",
        json={
            "expected_revision": 1,
            "day": 3,
            "period": 4,
            "room_id": "room-102",
            "is_locked": True,
        },
        headers=headers,
    )
    assert edit_resp.status_code == 200
    updated_data = edit_resp.json()
    assert updated_data["revision"] == 2
    updated_assign = next(a for a in updated_data["output_assignments"] if a["session_id"] == "sess-math")
    assert updated_assign["day"] == 3
    assert updated_assign["period"] == 4
    assert updated_assign["room_id"] == "room-102"
    assert updated_assign["is_locked"] is True


def test_revision_conflict_returns_409(client):
    csrf = login_coordinator(client)
    headers = {"X-CSRF-Token": csrf}
    term_id = get_term_id()

    create_resp = client.post(
        "/api/v1/timetable-drafts",
        json={
            "name": "Stale Edit Draft",
            "academic_term_id": term_id,
            "input_snapshot": {
                "sessions": [{"id": "s1", "name": "S1", "duration": 1}],
                "rooms": [{"id": "r1", "capacity": 50}],
            },
        },
        headers=headers,
    )
    draft_id = create_resp.json()["id"]

    db = SessionLocal()
    draft = db.query(TimetableDraft).filter(TimetableDraft.id == draft_id).first()
    draft.output_assignments = [{"session_id": "s1", "day": 0, "period": 0, "room_id": "r1"}]
    draft.revision = 3  # Draft is ahead
    db.commit()
    db.close()

    conflict_resp = client.patch(
        f"/api/v1/timetable-drafts/{draft_id}/assignments/s1",
        json={
            "expected_revision": 1,
            "day": 1,
            "period": 2,
        },
        headers=headers,
    )
    assert conflict_resp.status_code == 409
    assert "Revision conflict" in conflict_resp.json()["detail"]


def test_invalid_move_marks_draft_as_invalid(client):
    csrf = login_coordinator(client)
    headers = {"X-CSRF-Token": csrf}
    term_id = get_term_id()

    snapshot = {
        "days": [0, 1],
        "periods_per_day": 4,
        "sessions": [
            {"id": "sess-1", "name": "Session 1", "duration": 1, "teacher_id": "t1"},
            {"id": "sess-2", "name": "Session 2", "duration": 1, "teacher_id": "t2"},
        ],
        "rooms": [{"id": "r1", "capacity": 50}],
    }

    create_resp = client.post(
        "/api/v1/timetable-drafts",
        json={"name": "Collision Draft", "academic_term_id": term_id, "input_snapshot": snapshot},
        headers=headers,
    )
    draft_id = create_resp.json()["id"]

    db = SessionLocal()
    draft = db.query(TimetableDraft).filter(TimetableDraft.id == draft_id).first()
    draft.output_assignments = [
        {"session_id": "sess-1", "day": 0, "period": 0, "room_id": "r1"},
        {"session_id": "sess-2", "day": 0, "period": 1, "room_id": "r1"},
    ]
    draft.status = "CHECKED"
    db.commit()
    db.close()

    # Move sess-2 to (0, 0) directly overlapping sess-1 in room r1
    move_resp = client.patch(
        f"/api/v1/timetable-drafts/{draft_id}/assignments/sess-2",
        json={"expected_revision": 1, "day": 0, "period": 0, "room_id": "r1"},
        headers=headers,
    )
    assert move_resp.status_code == 200
    data = move_resp.json()
    assert data["status"] == "INVALID"
    assert data["validation_report"]["is_valid"] is False
    assert any(v["rule"] == "ROOM_OVERLAP" for v in data["validation_report"]["violations"])


def test_minimal_change_repair_preserves_locked_sessions(client):
    csrf = login_coordinator(client)
    headers = {"X-CSRF-Token": csrf}
    term_id = get_term_id()

    snapshot = {
        "days": [0, 1],
        "periods_per_day": 4,
        "sessions": [
            {"id": "sess-locked", "name": "Keynote Lecture", "duration": 1, "teacher_id": "t-vip", "min_capacity": 30},
            {"id": "sess-flexible", "name": "Lab Tutorial", "duration": 1, "teacher_id": "t-ta", "min_capacity": 30},
        ],
        "rooms": [
            {"id": "auditorium", "name": "Auditorium", "capacity": 100},
            {"id": "room-b", "name": "Room B", "capacity": 50},
        ],
    }

    create_resp = client.post(
        "/api/v1/timetable-drafts",
        json={"name": "Repair Test Draft", "academic_term_id": term_id, "input_snapshot": snapshot},
        headers=headers,
    )
    draft_id = create_resp.json()["id"]

    db = SessionLocal()
    draft = db.query(TimetableDraft).filter(TimetableDraft.id == draft_id).first()
    draft.output_assignments = [
        {"session_id": "sess-locked", "day": 0, "period": 0, "room_id": "auditorium", "is_locked": True},
        {"session_id": "sess-flexible", "day": 0, "period": 0, "room_id": "auditorium", "is_locked": False},
    ]
    draft.status = "INVALID"
    draft.revision = 1
    db.commit()
    db.close()

    # Call /repair
    repair_resp = client.post(
        f"/api/v1/timetable-drafts/{draft_id}/repair",
        json={"expected_revision": 1, "time_limit_seconds": 10},
        headers=headers,
    )
    assert repair_resp.status_code == 200
    repair_data = repair_resp.json()
    assert repair_data["is_valid"] is True
    assert repair_data["status"] == "CHECKED"
    assert repair_data["revision"] == 2

    # Verify sess-locked is STILL at (0, 0, auditorium)!
    locked_assign = next(a for a in repair_data["output_assignments"] if a["session_id"] == "sess-locked")
    assert locked_assign["day"] == 0
    assert locked_assign["period"] == 0
    assert locked_assign["room_id"] == "auditorium"

    # Verify sess-flexible was moved to resolve the collision
    flex_assign = next(a for a in repair_data["output_assignments"] if a["session_id"] == "sess-flexible")
    assert not (flex_assign["day"] == 0 and flex_assign["period"] == 0 and flex_assign["room_id"] == "auditorium")

    # Verify changes list recorded before/after
    assert repair_data["change_count"] >= 1
    flex_change = next((c for c in repair_data["changes"] if c["session_id"] == "sess-flexible"), None)
    assert flex_change is not None
    assert flex_change["before"]["room_id"] == "auditorium"
    assert "after" in flex_change


def test_published_draft_blocks_edits_and_repairs(client):
    csrf = login_coordinator(client)
    headers = {"X-CSRF-Token": csrf}
    term_id = get_term_id()

    create_resp = client.post(
        "/api/v1/timetable-drafts",
        json={"name": "Immutable Draft", "academic_term_id": term_id, "input_snapshot": {"sessions": []}},
        headers=headers,
    )
    draft_id = create_resp.json()["id"]

    db = SessionLocal()
    draft = db.query(TimetableDraft).filter(TimetableDraft.id == draft_id).first()
    draft.is_published = True
    draft.status = "PUBLISHED"
    db.commit()
    db.close()

    edit_resp = client.patch(
        f"/api/v1/timetable-drafts/{draft_id}/assignments/sess-1",
        json={"expected_revision": 1, "day": 1, "period": 1},
        headers=headers,
    )
    assert edit_resp.status_code == 400
    assert "Published timetable drafts are immutable" in edit_resp.json()["detail"]

    repair_resp = client.post(
        f"/api/v1/timetable-drafts/{draft_id}/repair",
        json={"expected_revision": 1},
        headers=headers,
    )
    assert repair_resp.status_code == 400
    assert "Published timetable drafts are immutable" in repair_resp.json()["detail"]
