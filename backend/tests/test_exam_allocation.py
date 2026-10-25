import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.academic import AcademicTerm
from app.models.exam import ExamSitting
from app.services.theory_seating_engine import TheorySeatingEngine
from app.services.practical_exam_engine import PracticalExamEngine
from app.services.exam_export_service import ExamExportService
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


def login_controller(client: TestClient) -> str:
    resp = client.post("/api/v1/auth/login", json={
        "institution_code": "APEX",
        "identifier": "exam@apex.edu",
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


# 1. Exact-Fit Capacity
def test_exact_fit_capacity():
    candidates = [
        {"id": f"c-{i}", "roll_number": f"RN-{i}", "paper_id": "P1", "requires_accessible_seat": False}
        for i in range(4)
    ]
    rooms = [{
        "id": "r-1", "name": "Room 1", "grid_rows": 2, "grid_cols": 2,
        "seats": [
            {"id": "s-1", "row_num": 1, "col_num": 1, "bench_label": "B1", "is_usable_for_exam": True, "is_blocked": False, "is_accessible": False},
            {"id": "s-2", "row_num": 1, "col_num": 2, "bench_label": "B2", "is_usable_for_exam": True, "is_blocked": False, "is_accessible": False},
            {"id": "s-3", "row_num": 2, "col_num": 1, "bench_label": "B3", "is_usable_for_exam": True, "is_blocked": False, "is_accessible": False},
            {"id": "s-4", "row_num": 2, "col_num": 2, "bench_label": "B4", "is_usable_for_exam": True, "is_blocked": False, "is_accessible": False},
        ]
    }]
    snapshot = {"candidates": candidates, "rooms": rooms, "policy": {"hard_paper_adjacency": False}}
    result = TheorySeatingEngine.allocate(snapshot)
    assert result["status"] == "ALLOCATED"
    assert len(result["allocations"]) == 4
    assert result["validation_report"]["is_valid"] is True


# 2. One-Seat Shortfall
def test_one_seat_shortfall():
    # 5 candidates but only 4 usable seats
    candidates = [
        {"id": f"c-{i}", "roll_number": f"RN-{i}", "paper_id": "P1"}
        for i in range(5)
    ]
    rooms = [{
        "id": "r-1", "name": "Room 1",
        "seats": [
            {"id": f"s-{i}", "row_num": 1, "col_num": i, "is_usable_for_exam": True, "is_blocked": False}
            for i in range(4)
        ]
    }]
    snapshot = {"candidates": candidates, "rooms": rooms}
    result = TheorySeatingEngine.allocate(snapshot)
    assert result["status"] == "INSUFFICIENT_CAPACITY"
    assert result["error_code"] == "INSUFFICIENT_CAPACITY"
    assert "shortfall: 1" in result["error_message"]


# 3. Duplicate Candidate Detection
def test_duplicate_candidate_detection():
    # Candidate c-1 registered twice in allocations
    snapshot = {
        "candidates": [{"id": "c-1", "roll_number": "RN-1", "paper_id": "P1"}],
        "rooms": [{
            "id": "r-1",
            "seats": [
                {"id": "s-1", "row_num": 1, "col_num": 1, "is_usable_for_exam": True, "is_blocked": False},
                {"id": "s-2", "row_num": 1, "col_num": 2, "is_usable_for_exam": True, "is_blocked": False},
            ]
        }]
    }
    mutated_allocations = [
        {"candidate_id": "c-1", "room_id": "r-1", "seat_id": "s-1"},
        {"candidate_id": "c-1", "room_id": "r-1", "seat_id": "s-2"},
    ]
    report = TheorySeatingEngine.verify_theory_seating(snapshot, mutated_allocations)
    assert report["is_valid"] is False
    assert any(v["rule"] == "DUPLICATE_CANDIDATE" for v in report["violations"])


# 4. Duplicate Bench Detection
def test_duplicate_bench_detection():
    # Two different candidates assigned to the exact same bench s-1
    snapshot = {
        "candidates": [
            {"id": "c-1", "roll_number": "RN-1", "paper_id": "P1"},
            {"id": "c-2", "roll_number": "RN-2", "paper_id": "P1"},
        ],
        "rooms": [{
            "id": "r-1",
            "seats": [
                {"id": "s-1", "row_num": 1, "col_num": 1, "is_usable_for_exam": True, "is_blocked": False},
                {"id": "s-2", "row_num": 1, "col_num": 2, "is_usable_for_exam": True, "is_blocked": False},
            ]
        }]
    }
    mutated_allocations = [
        {"candidate_id": "c-1", "room_id": "r-1", "seat_id": "s-1"},
        {"candidate_id": "c-2", "room_id": "r-1", "seat_id": "s-1"},
    ]
    report = TheorySeatingEngine.verify_theory_seating(snapshot, mutated_allocations)
    assert report["is_valid"] is False
    assert any(v["rule"] == "DUPLICATE_BENCH" for v in report["violations"])


# 5. Blocked Seat Detection
def test_blocked_seat_detection():
    # Candidate placed on is_blocked=True seat
    snapshot = {
        "candidates": [{"id": "c-1", "roll_number": "RN-1", "paper_id": "P1"}],
        "rooms": [{
            "id": "r-1",
            "seats": [{"id": "s-blocked", "row_num": 1, "col_num": 1, "is_usable_for_exam": True, "is_blocked": True}]
        }]
    }
    allocations = [{"candidate_id": "c-1", "room_id": "r-1", "seat_id": "s-blocked"}]
    report = TheorySeatingEngine.verify_theory_seating(snapshot, allocations)
    assert report["is_valid"] is False
    assert any(v["rule"] == "BLOCKED_SEAT" for v in report["violations"])


# 6. Ineligible Accommodation Seat
def test_ineligible_accommodation_seat():
    # Candidate requires accessible seat, but assigned to seat where is_accessible=False
    snapshot = {
        "candidates": [{"id": "c-special", "roll_number": "RN-SPEC", "paper_id": "P1", "requires_accessible_seat": True}],
        "rooms": [{
            "id": "r-1",
            "seats": [{"id": "s-standard", "row_num": 1, "col_num": 1, "is_usable_for_exam": True, "is_blocked": False, "is_accessible": False}]
        }]
    }
    allocations = [{"candidate_id": "c-special", "room_id": "r-1", "seat_id": "s-standard"}]
    report = TheorySeatingEngine.verify_theory_seating(snapshot, allocations)
    assert report["is_valid"] is False
    assert any(v["rule"] == "INELIGIBLE_ACCOMMODATION_SEAT" for v in report["violations"])


# 7. Paper-Adjacency Policy (Hard vs Soft)
def test_paper_adjacency_policy_hard_vs_soft():
    # Two candidates with the same paper P1 on adjacent benches (1,1) and (1,2)
    snapshot_base = {
        "candidates": [
            {"id": "c-1", "roll_number": "RN-1", "paper_id": "P1"},
            {"id": "c-2", "roll_number": "RN-2", "paper_id": "P1"},
        ],
        "rooms": [{
            "id": "r-1",
            "seats": [
                {"id": "s-1", "row_num": 1, "col_num": 1, "is_usable_for_exam": True, "is_blocked": False},
                {"id": "s-2", "row_num": 1, "col_num": 2, "is_usable_for_exam": True, "is_blocked": False},
            ]
        }],
    }
    allocations = [
        {"candidate_id": "c-1", "room_id": "r-1", "seat_id": "s-1"},
        {"candidate_id": "c-2", "room_id": "r-1", "seat_id": "s-2"},
    ]

    # Test A: Hard Adjacency -> MUST BE REJECTED (Violation, not silently relaxed!)
    snapshot_hard = dict(snapshot_base, policy={"hard_paper_adjacency": True})
    report_hard = TheorySeatingEngine.verify_theory_seating(snapshot_hard, allocations)
    assert report_hard["is_valid"] is False
    assert any(v["rule"] == "PAPER_ADJACENCY_VIOLATION" for v in report_hard["violations"])

    # Test B: Soft Adjacency -> Allowed as valid but with a warning!
    snapshot_soft = dict(snapshot_base, policy={"hard_paper_adjacency": False})
    report_soft = TheorySeatingEngine.verify_theory_seating(snapshot_soft, allocations)
    assert report_soft["is_valid"] is True
    assert any(w["rule"] == "PAPER_ADJACENCY_WARNING" for w in report_soft["warnings"])


# 8. Practical Exam: Extra-Duration Overlap with Buffers
def test_practical_extra_duration_overlap_with_buffer():
    # Batch 1: 09:00 - 11:00 (120 mins) + 15 min buffer = ends at 11:15
    # Batch 2: starts at 11:00 in the same lab! (overlaps the 15-min turnaround buffer)
    snapshot = {
        "sittings": [
            {"batch_id": "b-1", "day": 0, "start_time": "09:00", "duration_minutes": 120, "buffer_minutes": 15, "lab_id": "lab-1"},
            {"batch_id": "b-2", "day": 0, "start_time": "11:00", "duration_minutes": 120, "buffer_minutes": 15, "lab_id": "lab-1"},
        ],
        "candidates": [],
        "labs": [{"id": "lab-1", "workstations": []}],
    }
    report = PracticalExamEngine.verify_practical_allocation(snapshot, allocations=[])
    assert report["is_valid"] is False
    assert any(v["rule"] == "LAB_OVERLAP" for v in report["violations"])


# 9. Practical Exam: Examiner Clash
def test_practical_examiner_clash():
    # Same chief examiner dr-smith in two concurrent batches in different labs
    snapshot = {
        "sittings": [
            {"batch_id": "b-1", "day": 0, "start_time": "09:00", "duration_minutes": 120, "buffer_minutes": 15, "lab_id": "lab-1", "chief_examiner_id": "dr-smith"},
            {"batch_id": "b-2", "day": 0, "start_time": "10:00", "duration_minutes": 120, "buffer_minutes": 15, "lab_id": "lab-2", "chief_examiner_id": "dr-smith"},
        ],
        "candidates": [],
        "labs": [{"id": "lab-1", "workstations": []}, {"id": "lab-2", "workstations": []}],
    }
    report = PracticalExamEngine.verify_practical_allocation(snapshot, allocations=[])
    assert report["is_valid"] is False
    assert any(v["rule"] == "EXAMINER_CLASH" for v in report["violations"])


# 10. Practical Exam: Workstation Incompatibility
def test_practical_workstation_incompatibility():
    # Candidate requires GPU, but assigned workstation only has Linux
    snapshot = {
        "sittings": [{"batch_id": "b-1", "day": 0, "start_time": "09:00", "duration_minutes": 120, "buffer_minutes": 15, "lab_id": "lab-1"}],
        "candidates": [{"id": "c-gpu", "roll_number": "RN-GPU", "batch_id": "b-1", "required_features": ["GPU"]}],
        "labs": [{
            "id": "lab-1",
            "workstations": [{"id": "ws-basic", "is_active": True, "features": ["Linux"]}]
        }],
    }
    allocations = [{"batch_id": "b-1", "candidate_id": "c-gpu", "lab_id": "lab-1", "workstation_id": "ws-basic"}]
    report = PracticalExamEngine.verify_practical_allocation(snapshot, allocations)
    assert report["is_valid"] is False
    assert any(v["rule"] == "WORKSTATION_INCOMPATIBLE" for v in report["violations"])


# 11. Export Content Matches Selected Snapshot & Omits Private Accommodations
def test_export_content_matches_snapshot_and_omits_private_accommodations(client):
    csrf = login_controller(client)
    headers = {"X-CSRF-Token": csrf}
    term_id = get_term_id()

    # Create theory sitting with private accommodation note
    snapshot = {
        "candidates": [
            {
                "id": "cand-secret",
                "roll_number": "ROLL-999",
                "name": "Jane Doe",
                "paper_id": "CS-101",
                "requires_accessible_seat": True,
                "private_accommodations": "CONFIDENTIAL: Needs front row wheelchair space and medical monitor.",
            }
        ],
        "rooms": [{
            "id": "hall-a",
            "name": "Main Examination Hall",
            "seats": [
                {"id": "bench-1", "row_num": 1, "col_num": 1, "bench_label": "Bench-A1", "is_usable_for_exam": True, "is_blocked": False, "is_accessible": True}
            ]
        }]
    }

    create_resp = client.post(
        "/api/v1/exams/theory/sittings",
        json={
            "name": "Export Audit Exam",
            "academic_term_id": term_id,
            "input_snapshot": snapshot,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    sitting_id = create_resp.json()["id"]

    # Allocate seating
    alloc_resp = client.post(f"/api/v1/exams/theory/sittings/{sitting_id}/allocate", headers=headers)
    assert alloc_resp.status_code == 200

    # Test Export: Hall Seat Plan
    export_resp = client.get(f"/api/v1/exams/theory/sittings/{sitting_id}/export/seat-plan")
    assert export_resp.status_code == 200
    export_data = export_resp.json()

    assert export_data["document_type"] == "HALL_SEAT_PLAN"
    assert export_data["sitting_id"] == sitting_id
    assert export_data["status_label"] in ("DRAFT", "PUBLISHED")
    assert "generated_at" in export_data

    # Match snapshot roll number & bench label
    seat_entry = export_data["seats"][0]
    assert seat_entry["roll_number"] == "ROLL-999"
    assert seat_entry["bench_label"] == "Bench-A1"

    # STRICT PRIVACY AUDIT: Ensure confidential note is NOT exposed in the exported public seat plan!
    assert "CONFIDENTIAL" not in str(export_data)
    assert "private_accommodations" not in seat_entry


def test_theory_seat_reassignment_and_swapping(client):
    csrf = login_controller(client)
    headers = {"X-CSRF-Token": csrf}
    db = SessionLocal()
    term = db.query(AcademicTerm).first()
    term_id = term.id
    db.close()

    snapshot = {
        "candidates": [
            {"id": "cand-1", "roll_number": "ROLL-101", "name": "Student A", "paper_code": "CS101"},
            {"id": "cand-2", "roll_number": "ROLL-102", "name": "Student B", "paper_code": "CS101"},
        ],
        "rooms": [{
            "id": "room-1", "name": "Hall Alpha",
            "seats": [
                {"id": "bench-1", "row_num": 1, "col_num": 1, "bench_label": "A1", "is_usable_for_exam": True, "is_blocked": False, "is_accessible": False},
                {"id": "bench-2", "row_num": 1, "col_num": 2, "bench_label": "A2", "is_usable_for_exam": True, "is_blocked": False, "is_accessible": False},
            ]
        }]
    }

    create_resp = client.post(
        "/api/v1/exams/theory/sittings",
        json={"name": "Reassign Test Sitting", "academic_term_id": term_id, "input_snapshot": snapshot},
        headers=headers,
    )
    sitting = create_resp.json()
    sid = sitting["id"]

    alloc_resp = client.post(f"/api/v1/exams/theory/sittings/{sid}/allocate", headers=headers)
    assert alloc_resp.status_code == 200
    alloc_sitting = alloc_resp.json()
    rev = alloc_sitting["revision"]

    # Test swap between cand-1 and cand-2
    swap_resp = client.patch(
        f"/api/v1/exams/theory/sittings/{sid}/seats/cand-1",
        json={"expected_revision": rev, "target_candidate_id": "cand-2"},
        headers=headers,
    )
    assert swap_resp.status_code == 200
    swapped = swap_resp.json()
    assert swapped["revision"] == rev + 1

    # Stale revision should return 409 Conflict
    stale_resp = client.patch(
        f"/api/v1/exams/theory/sittings/{sid}/seats/cand-1",
        json={"expected_revision": rev, "target_candidate_id": "cand-2"},
        headers=headers,
    )
    assert stale_resp.status_code == 409


def test_practical_sitting_lifecycle_reassignment_and_listing(client):
    csrf = login_controller(client)
    headers = {"X-CSRF-Token": csrf}
    db = SessionLocal()
    term = db.query(AcademicTerm).first()
    term_id = term.id
    db.close()

    snapshot = {
        "candidates": [
            {"id": "p-cand-1", "roll_number": "PR-01", "name": "Practical One", "required_os": "Linux", "required_features": []},
            {"id": "p-cand-2", "roll_number": "PR-02", "name": "Practical Two", "required_os": "Linux", "required_features": []},
        ],
        "labs": [{
            "id": "lab-comp", "name": "Computer Lab 1", "effective_capacity_limit": 10,
            "workstations": [
                {"id": "ws-01", "station_code": "WS-01", "is_usable": True, "os": "Linux", "installed_features": []},
                {"id": "ws-02", "station_code": "WS-02", "is_usable": True, "os": "Linux", "installed_features": []},
            ]
        }],
        "sittings": [
            {
                "batch_id": "batch-1", "lab_id": "lab-comp",
                "start_time": "10:00", "duration_minutes": 120, "turnaround_buffer_minutes": 15,
                "examiner_id": "examiner-1",
            }
        ]
    }

    create_resp = client.post(
        "/api/v1/exams/practical/sittings",
        json={"name": "Linux Practical Exam", "academic_term_id": term_id, "input_snapshot": snapshot},
        headers=headers,
    )
    assert create_resp.status_code == 201
    sid = create_resp.json()["id"]

    alloc_resp = client.post(f"/api/v1/exams/practical/sittings/{sid}/allocate", headers=headers)
    assert alloc_resp.status_code == 200
    sitting = alloc_resp.json()
    assert sitting["status"] == "CHECKED"
    assert len(sitting["output_allocations"]) == 2

    # Test practical workstation reassignment
    reassign_resp = client.patch(
        f"/api/v1/exams/practical/sittings/{sid}/workstations/p-cand-1",
        json={"expected_revision": sitting["revision"], "workstation_id": "ws-02"},
        headers=headers,
    )
    assert reassign_resp.status_code == 200
    updated = reassign_resp.json()
    assert updated["revision"] == sitting["revision"] + 1

    # Stale revision returns 409
    stale_resp = client.patch(
        f"/api/v1/exams/practical/sittings/{sid}/workstations/p-cand-1",
        json={"expected_revision": sitting["revision"], "workstation_id": "ws-01"},
        headers=headers,
    )
    assert stale_resp.status_code == 409

    # Test listing sittings
    list_all = client.get("/api/v1/exams/sittings")
    assert list_all.status_code == 200
    assert len(list_all.json()) >= 2

    list_theory = client.get("/api/v1/exams/theory/sittings")
    assert list_theory.status_code == 200
    assert any(s["exam_type"] == "THEORY" for s in list_theory.json())

    list_practical = client.get("/api/v1/exams/practical/sittings")
    assert list_practical.status_code == 200
    assert any(s["exam_type"] == "PRACTICAL" for s in list_practical.json())
