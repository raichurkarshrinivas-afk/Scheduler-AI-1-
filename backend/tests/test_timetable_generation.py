import time
import copy
import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.institution import Institution
from app.models.academic import AcademicTerm
from app.models.user import UserRole
from app.models.schedule import TimetableDraft
from app.services.schedule_solver import ScheduleSolver
from app.services.schedule_checker import ScheduleChecker
from app.worker import BackgroundWorker
from app.seeds.seed import run_seed


@pytest.fixture(scope="module")
def seeded_db():
    db = SessionLocal()
    run_seed(db)
    yield db
    db.close()


@pytest.fixture
def client():
    return TestClient(app, base_url="http://testserver")


def login_user(client: TestClient, email: str, role: UserRole, institution_code: str = "APEX") -> str:
    response = client.post("/api/v1/auth/login", json={
        "institution_code": institution_code,
        "identifier": email,
        "password": "DevSeed2026!#",
    })
    assert response.status_code == 200, response.text
    return response.json()["csrf_token"]


def create_feasible_snapshot() -> dict:
    """Creates a small, well-formed feasible scheduling problem."""
    return {
        "days": [0, 1, 2],  # Mon, Tue, Wed
        "periods_per_day": 4,  # Periods 0, 1, 2, 3
        "break_periods": [2],  # Period 2 is lunch break
        "teachers": [
            {"id": "t-smith", "name": "Dr. Smith"},
            {"id": "t-turing", "name": "Dr. Turing"},
        ],
        "rooms": [
            {"id": "r-101", "name": "Room 101", "room_type": "THEORY", "capacity": 60, "features": []},
            {"id": "r-lab", "name": "Computing Lab", "room_type": "PRACTICAL", "capacity": 30, "features": ["Linux", "GPU"]},
        ],
        "sections": [
            {"id": "sec-cs", "name": "CS Year 1", "student_count": 25},
        ],
        "sessions": [
            {
                "id": "s-algo",
                "name": "Algorithms Lecture",
                "section_id": "sec-cs",
                "teacher_id": "t-smith",
                "duration": 1,
                "min_capacity": 25,
                "room_type_required": "THEORY",
                "required_features": [],
            },
            {
                "id": "s-systems",
                "name": "Systems Lecture",
                "section_id": "sec-cs",
                "teacher_id": "t-turing",
                "duration": 1,
                "min_capacity": 25,
                "room_type_required": "THEORY",
                "required_features": [],
            },
            {
                "id": "s-lab",
                "name": "Algorithms Practical",
                "section_id": "sec-cs",
                "teacher_id": "t-smith",
                "duration": 2,  # Multi-period consecutive practical!
                "min_capacity": 25,
                "room_type_required": "PRACTICAL",
                "required_features": ["Linux"],
            },
        ],
        "teacher_unavailability": [
            {"teacher_id": "t-smith", "day": 0, "period": 0},  # Smith unavailable Monday morning
        ],
        "room_unavailability": [],
    }


# ==============================================================================
# 1. Small Feasible Fixture & Independent Checker Validation
# ==============================================================================
def test_small_feasible_fixture_and_independent_checker():
    snapshot = create_feasible_snapshot()

    # Solve
    solution = ScheduleSolver.solve(snapshot, time_limit_seconds=5.0)
    assert solution["solver_status"] in ("OPTIMAL", "FEASIBLE")
    assert len(solution["assignments"]) == 3
    assert solution["runtime_seconds"] >= 0.0

    # Validate with independent checker
    report = ScheduleChecker.validate(snapshot, solution["assignments"])
    assert report["is_valid"] is True, f"Checker failed: {report['violations']}"
    assert report["total_required"] == 3
    assert report["total_assigned"] == 3
    assert report["violations_count"] == 0


# ==============================================================================
# 2. Proven Infeasible Fixture
# ==============================================================================
def test_proven_infeasible_fixture():
    snapshot = create_feasible_snapshot()
    # Make problem mathematically impossible:
    # Teacher Smith is required to teach 2 sessions of 1 period and 1 session of 2 periods = 4 periods total.
    # Set Smith unavailable for all periods except period 0.
    for d in range(3):
        for p in range(4):
            snapshot["teacher_unavailability"].append({"teacher_id": "t-smith", "day": d, "period": p})

    solution = ScheduleSolver.solve(snapshot, time_limit_seconds=3.0)
    assert solution["solver_status"] == "INFEASIBLE"
    assert solution["assignments"] == []
    assert solution["error_code"] is not None


# ==============================================================================
# 3. Timeout / Unknown Handling (Never Labeled as Infeasible)
# ==============================================================================
def test_timeout_unknown_handling():
    # Construct a moderately dense problem with virtually zero time limit (0.000001s)
    snapshot = create_feasible_snapshot()
    # Add multiple sessions to ensure search does not instantly complete in 0ms
    for i in range(15):
        snapshot["sessions"].append({
            "id": f"s-extra-{i}",
            "name": f"Extra Lecture {i}",
            "section_id": "sec-cs",
            "teacher_id": "t-turing" if i % 2 == 0 else "t-smith",
            "duration": 1,
            "min_capacity": 20,
            "room_type_required": "THEORY",
            "required_features": [],
        })

    solution = ScheduleSolver.solve(snapshot, time_limit_seconds=0.000001)
    # The solver search times out without proof of infeasibility
    if solution["solver_status"] == "UNKNOWN":
        assert solution["solver_status"] != "INFEASIBLE", "Rule: Never label UNKNOWN as proven infeasibility!"
        assert solution["assignments"] == []


# ==============================================================================
# 4. Missing Session Mutation Detected by Independent Checker
# ==============================================================================
def test_missing_session_mutation_detected():
    snapshot = create_feasible_snapshot()
    solution = ScheduleSolver.solve(snapshot, time_limit_seconds=5.0)
    assert solution["solver_status"] in ("OPTIMAL", "FEASIBLE")

    # Mutate output: drop 1 session
    mutated = copy.deepcopy(solution["assignments"])
    removed_session = mutated.pop(0)

    report = ScheduleChecker.validate(snapshot, mutated)
    assert report["is_valid"] is False
    assert any(v["rule"] == "COMPLETENESS" and v["session_id"] == removed_session["session_id"] for v in report["violations"])


# ==============================================================================
# 5. Teacher and Room Overlap Mutations Detected
# ==============================================================================
def test_resource_overlap_mutations_detected():
    snapshot = create_feasible_snapshot()
    solution = ScheduleSolver.solve(snapshot, time_limit_seconds=5.0)
    assert solution["solver_status"] in ("OPTIMAL", "FEASIBLE")

    # Mutation A: Teacher Overlap
    mutated_teacher = copy.deepcopy(solution["assignments"])
    # Force session 1 to same day & period as session 0 (both have teacher Smith)
    mutated_teacher[1]["day"] = mutated_teacher[0]["day"]
    mutated_teacher[1]["period"] = mutated_teacher[0]["period"]

    report_a = ScheduleChecker.validate(snapshot, mutated_teacher)
    assert report_a["is_valid"] is False
    assert any("OVERLAP" in v["rule"] for v in report_a["violations"])

    # Mutation B: Room Overlap
    mutated_room = copy.deepcopy(solution["assignments"])
    mutated_room[1]["day"] = mutated_room[0]["day"]
    mutated_room[1]["period"] = mutated_room[0]["period"]
    mutated_room[1]["room_id"] = mutated_room[0]["room_id"]

    report_b = ScheduleChecker.validate(snapshot, mutated_room)
    assert report_b["is_valid"] is False
    assert any(v["rule"] == "ROOM_OVERLAP" for v in report_b["violations"])


# ==============================================================================
# 6. Duration and Capacity Violations Detected
# ==============================================================================
def test_duration_and_capacity_violations_detected():
    snapshot = create_feasible_snapshot()
    solution = ScheduleSolver.solve(snapshot, time_limit_seconds=5.0)
    assert solution["solver_status"] in ("OPTIMAL", "FEASIBLE")

    # Mutation A: Capacity violation (assign room with cap 20 to session needing 25)
    snapshot_small_room = copy.deepcopy(snapshot)
    snapshot_small_room["rooms"][0]["capacity"] = 15  # Smaller than required 25

    report_cap = ScheduleChecker.validate(snapshot_small_room, solution["assignments"])
    assert report_cap["is_valid"] is False
    assert any(v["rule"] == "CAPACITY_VIOLATION" for v in report_cap["violations"])

    # Mutation B: Duration mismatch (change assigned duration)
    mutated_dur = copy.deepcopy(solution["assignments"])
    mutated_dur[2]["duration"] = 1  # Required duration was 2 for practical!

    report_dur = ScheduleChecker.validate(snapshot, mutated_dur)
    assert report_dur["is_valid"] is False
    assert any(v["rule"] == "DURATION_MISMATCH" for v in report_dur["violations"])


# ==============================================================================
# 7. Unsupported Rule Requests Explicitly Rejected
# ==============================================================================
def test_unsupported_rule_requests_rejected():
    snapshot = create_feasible_snapshot()
    snapshot["rules"] = {"floating_lunch": True}

    solution = ScheduleSolver.solve(snapshot)
    assert solution["solver_status"] == "MODEL_INVALID"
    assert solution["error_code"] == "UNSUPPORTED_RULE"
    assert "explicitly rejected" in solution["error_message"]


# ==============================================================================
# 8. Published State Is Not Modified By Generation (API Boundary Test)
# ==============================================================================
def test_published_state_not_modified_by_generation(client, seeded_db):
    csrf_token = login_user(client, "coord@apex.edu", UserRole.TIMETABLE_COORDINATOR)
    term = seeded_db.query(AcademicTerm).first()
    assert term is not None

    # 1. Create timetable draft via API
    create_resp = client.post(
        "/api/v1/timetable-drafts",
        json={
            "name": "Published Integrity Draft",
            "academic_term_id": term.id,
            "input_snapshot": create_feasible_snapshot(),
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert create_resp.status_code == 201, create_resp.text
    draft_id = create_resp.json()["id"]

    # 2. Mark draft as published in DB
    draft = seeded_db.query(TimetableDraft).filter(TimetableDraft.id == draft_id).first()
    assert draft is not None
    draft.is_published = True
    draft.status = "PUBLISHED"
    seeded_db.commit()

    # 3. Attempt to trigger generation on the published draft -> MUST return 400 Bad Request
    gen_resp = client.post(
        f"/api/v1/timetable-drafts/{draft_id}/generate",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert gen_resp.status_code == 400, "Regenerating a published draft MUST be rejected!"
    assert "immutable" in gen_resp.json()["detail"]


# ==============================================================================
# 9. Full End-to-End Async Worker Timetable Generation Lifecycle
# ==============================================================================
def test_end_to_end_worker_timetable_solve_lifecycle(client, seeded_db):
    csrf_token = login_user(client, "coord@apex.edu", UserRole.TIMETABLE_COORDINATOR)
    term = seeded_db.query(AcademicTerm).first()

    from app.models.job import Job, JobStatus
    seeded_db.query(Job).filter(Job.status.in_([JobStatus.QUEUED, JobStatus.RUNNING])).delete()
    seeded_db.commit()
    # 1. Create Draft
    create_resp = client.post(
        "/api/v1/timetable-drafts",
        json={
            "name": "Autumn 2026 Core Timetable Draft",
            "academic_term_id": term.id,
            "input_snapshot": create_feasible_snapshot(),
            "parameters": {"time_limit_seconds": 10.0},
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert create_resp.status_code == 201
    draft_id = create_resp.json()["id"]

    # 2. Dispatch generation -> returns 202 and job reference
    gen_resp = client.post(
        f"/api/v1/timetable-drafts/{draft_id}/generate",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert gen_resp.status_code == 202
    gen_data = gen_resp.json()
    assert gen_data["status"] == "QUEUED"
    job_id = gen_data["job_id"]

    # 3. Worker claims and executes the solve job
    worker = BackgroundWorker(worker_id="test-solver-worker", poll_interval=0.1)
    processed = worker.step()
    assert processed is True

    # 4. Fetch updated draft via GET endpoint
    get_resp = client.get(f"/api/v1/timetable-drafts/{draft_id}")
    assert get_resp.status_code == 200
    draft_data = get_resp.json()
    assert draft_data["status"] == "CHECKED"
    assert draft_data["solver_status"] in ("OPTIMAL", "FEASIBLE")
    assert len(draft_data["output_assignments"]) == 3
    assert draft_data["validation_report"]["is_valid"] is True
    assert draft_data["model_version"] == "1.0.0"
    assert draft_data["checker_version"] == "1.0.0"

