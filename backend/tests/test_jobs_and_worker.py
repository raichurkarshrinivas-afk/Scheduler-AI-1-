import time
import uuid
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.core.config import settings
from app.models.institution import Institution
from app.models.user import User, Membership, UserRole, UserSession
from app.models.job import Job, JobStatus, JobType
from app.services.job_service import JobService
from app.worker import BackgroundWorker, JobExecutionContext
from app.seeds.seed import run_seed


@pytest.fixture(scope="module")
def seeded_db():
    db = SessionLocal()
    run_seed(db)
    yield db
    db.close()


@pytest.fixture(autouse=True)
def clean_jobs_table(seeded_db):
    """Ensures each test starts with an empty jobs table to prevent state leakage."""
    seeded_db.query(Job).delete()
    seeded_db.commit()
    yield
    seeded_db.query(Job).delete()
    seeded_db.commit()


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


# ==============================================================================
# 1. Job Survives API Restart
# ==============================================================================
def test_job_survives_api_restart(client, seeded_db):
    """Verifies that durable background jobs persist across client / API process restarts."""
    csrf_token = login_user(client, "coord@apex.edu", UserRole.TIMETABLE_COORDINATOR)

    # 1. Enqueue job via API
    resp = client.post(
        "/api/v1/jobs",
        json={
            "job_type": "TIMETABLE_SOLVE",
            "input_reference": {"term": "Autumn 2026", "cohort": "CS-A"},
            "max_attempts": 3,
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert resp.status_code == 201, resp.text
    job_data = resp.json()
    job_id = job_data["id"]
    assert job_data["status"] == "QUEUED"
    assert job_data["phase_label"] == "Queued"

    # 2. Simulate complete API restart by creating a completely fresh client instance
    fresh_client = TestClient(app, base_url="http://testserver")
    fresh_csrf = login_user(fresh_client, "coord@apex.edu", UserRole.TIMETABLE_COORDINATOR)

    # 3. Retrieve the job on the fresh client
    get_resp = fresh_client.get(f"/api/v1/jobs/{job_id}")
    assert get_resp.status_code == 200, get_resp.text
    persisted_job = get_resp.json()
    assert persisted_job["id"] == job_id
    assert persisted_job["status"] in ("QUEUED", "RUNNING")
    assert persisted_job["input_reference"]["term"] == "Autumn 2026"


# ==============================================================================
# 2. Worker Crash Leads to Lease Recovery
# ==============================================================================
def test_worker_crash_leads_to_lease_recovery(seeded_db):
    """Verifies that if a worker crashes or drops heartbeats, the lease expires and is recovered."""
    apex = seeded_db.query(Institution).filter(Institution.code == "APEX").first()
    assert apex is not None

    # 1. Create a job
    job = JobService.create_job(
        db=seeded_db,
        institution_id=apex.id,
        job_type="GENERIC_TASK",
        input_reference={"steps": 2, "step_duration": 0.05},
        max_attempts=3,
    )

    # 2. Worker 1 claims job
    claimed_job = JobService.claim_next_job(
        seeded_db,
        worker_id="worker-crash-test-1",
        lease_duration_seconds=30,
    )
    assert claimed_job is not None
    assert claimed_job.id == job.id
    assert claimed_job.status == JobStatus.RUNNING.value
    assert claimed_job.attempt_count == 1
    token_1 = claimed_job.lease_token
    assert token_1 is not None

    # 3. Simulate worker 1 crashing and lease expiring
    now = datetime.now(timezone.utc)
    claimed_job.lease_expiry = now - timedelta(seconds=15)
    seeded_db.commit()

    # 4. Trigger lease recovery
    recovered = JobService.recover_expired_leases(seeded_db)
    assert recovered == 1

    # 5. Check job state in DB: should be re-queued with attempt_count preserved
    seeded_db.refresh(job)
    assert job.status == JobStatus.QUEUED.value
    assert job.lease_token is None
    assert job.attempt_count == 1
    assert "Recovered from expired lease" in job.phase_label

    # 6. Worker 2 claims the recovered job with a new lease token
    worker_2 = BackgroundWorker(worker_id="worker-recovery-2", poll_interval=0.1)
    worker_2.step()

    seeded_db.refresh(job)
    assert job.status == JobStatus.SUCCEEDED.value
    assert job.attempt_count == 2
    assert job.result_reference is not None
    assert job.result_reference.get("status") == "SUCCESS"


# ==============================================================================
# 3. Duplicate Attempts Do Not Duplicate Final Results (Fencing Token)
# ==============================================================================
def test_duplicate_attempts_do_not_duplicate_final_results_via_fencing(seeded_db):
    """
    Verifies that a stale worker whose lease expired cannot overwrite
    a newer worker's results or update state (fencing).
    """
    apex = seeded_db.query(Institution).filter(Institution.code == "APEX").first()

    # 1. Create job
    job = JobService.create_job(
        db=seeded_db,
        institution_id=apex.id,
        job_type="TIMETABLE_SOLVE",
        input_reference={"cohort": "CS-B"},
        max_attempts=3,
    )

    # 2. Worker 1 claims job (lease token 1)
    claimed_1 = JobService.claim_next_job(seeded_db, worker_id="worker-stale-1", lease_duration_seconds=10)
    token_1 = claimed_1.lease_token

    # 3. Simulate lease expiry for Worker 1
    now = datetime.now(timezone.utc)
    claimed_1.lease_expiry = now - timedelta(seconds=1)
    seeded_db.commit()

    # 4. Lease recovered and Worker 2 claims job (lease token 2)
    JobService.recover_expired_leases(seeded_db)
    claimed_2 = JobService.claim_next_job(seeded_db, worker_id="worker-active-2", lease_duration_seconds=30)
    token_2 = claimed_2.lease_token
    assert token_2 != token_1

    # 5. Worker 2 finishes and finalizes successfully
    result_worker_2 = {"status": "FEASIBLE", "assigned_sessions_count": 42, "solver": "worker-2"}
    finalized_2 = JobService.finalize_success(seeded_db, job.id, token_2, result_worker_2)
    assert finalized_2 is True

    # 6. Stale Worker 1 wakes up and attempts to finalize with token_1
    stale_result = {"status": "CORRUPT", "assigned_sessions_count": 0, "solver": "stale-worker-1"}
    finalized_1 = JobService.finalize_success(seeded_db, job.id, token_1, stale_result)
    assert finalized_1 is False, "Stale worker MUST be fenced out!"

    # 7. Also verify stale worker heartbeat fails
    hb_success, _ = JobService.heartbeat(seeded_db, job.id, token_1)
    assert hb_success is False, "Stale worker heartbeat MUST be rejected!"

    # 8. Confirm DB row contains Worker 2's authoritative result
    seeded_db.refresh(job)
    assert job.status == JobStatus.SUCCEEDED.value
    assert job.result_reference["solver"] == "worker-2"
    assert job.result_reference["assigned_sessions_count"] == 42


# ==============================================================================
# 4. Cancellation Behaviour Tested (Queued and Running)
# ==============================================================================
def test_cancellation_behaviour(client, seeded_db):
    """Verifies cancellation for both queued and actively executing jobs."""
    csrf_token = login_user(client, "coord@apex.edu", UserRole.TIMETABLE_COORDINATOR)

    # --- Scenario A: Cancel a Queued Job ---
    resp_a = client.post(
        "/api/v1/jobs",
        json={"job_type": "SEATING_ALLOCATION", "input_reference": {"hall": "Auditorium"}},
        headers={"X-CSRF-Token": csrf_token},
    )
    job_a_id = resp_a.json()["id"]

    # Cancel immediately
    cancel_resp = client.post(f"/api/v1/jobs/{job_a_id}/cancel", headers={"X-CSRF-Token": csrf_token})
    assert cancel_resp.status_code == 200, cancel_resp.text
    assert cancel_resp.json()["status"] == "CANCELLED"

    # Verify status in database
    job_a = JobService.get_job(seeded_db, job_a_id)
    assert job_a.status == JobStatus.CANCELLED.value
    assert job_a.cancellation_requested is True

    # --- Scenario B: Cancel a Running Job ---
    apex = seeded_db.query(Institution).filter(Institution.code == "APEX").first()
    job_b = JobService.create_job(
        db=seeded_db,
        institution_id=apex.id,
        job_type="GENERIC_TASK",
        input_reference={"steps": 5, "step_duration": 0.2},
    )

    # Worker claims job
    claimed_b = JobService.claim_next_job(seeded_db, worker_id="worker-cancel-test")
    assert claimed_b is not None

    # Request cancellation while running
    cancel_resp_b = client.post(f"/api/v1/jobs/{job_b.id}/cancel", headers={"X-CSRF-Token": csrf_token})
    assert cancel_resp_b.status_code == 200
    assert cancel_resp_b.json()["cancellation_requested"] is True

    # Worker detects cancellation on heartbeat/check and marks job CANCELLED
    worker = BackgroundWorker(worker_id="worker-cancel-test")
    ctx = JobExecutionContext(job_b.id, claimed_b.lease_token, worker)
    ctx.is_cancelled = True
    JobService.finalize_cancelled(seeded_db, job_b.id, claimed_b.lease_token)

    seeded_db.refresh(job_b)
    assert job_b.status == JobStatus.CANCELLED.value
    assert job_b.error_code == "CANCELLED_BY_USER"


# ==============================================================================
# 5. Cross-Tenant Job Access Denied
# ==============================================================================
def test_cross_tenant_job_access_denied(client, seeded_db):
    """Ensures that a user from Institution A cannot view or cancel a job belonging to Institution B."""
    # 1. Create a second institution (Beta)
    beta = seeded_db.query(Institution).filter(Institution.code == "BETA").first()
    if not beta:
        beta = Institution(
            id=str(uuid.uuid4()),
            code="BETA",
            name="Beta Institute of Technology",
            slug="beta-institute",
            timezone="UTC",
        )
        seeded_db.add(beta)
        seeded_db.commit()

    # 2. Create a job belonging to Beta
    beta_job = JobService.create_job(
        db=seeded_db,
        institution_id=beta.id,
        job_type="REPORT_GENERATION",
        input_reference={"type": "PDF"},
    )

    # 3. Login as APEX Administrator
    apex_csrf = login_user(client, "admin@apex.edu", UserRole.INSTITUTION_ADMINISTRATOR, "APEX")

    # 4. Attempt to access Beta's job -> MUST return 404
    get_resp = client.get(f"/api/v1/jobs/{beta_job.id}")
    assert get_resp.status_code == 404, "Cross-tenant job access MUST be denied with 404!"

    # 5. Attempt to cancel Beta's job -> MUST return 404
    cancel_resp = client.post(
        f"/api/v1/jobs/{beta_job.id}/cancel",
        headers={"X-CSRF-Token": apex_csrf},
    )
    assert cancel_resp.status_code == 404, "Cross-tenant job cancellation MUST be denied with 404!"


# ==============================================================================
# 6. Two Workers Cannot Claim the Same Active Attempt
# ==============================================================================
def test_two_workers_cannot_claim_same_active_attempt(seeded_db):
    """Verifies that atomic claim semantics prevent multiple workers from claiming the same job."""
    apex = seeded_db.query(Institution).filter(Institution.code == "APEX").first()

    # 1. Enqueue exactly one job
    job = JobService.create_job(
        db=seeded_db,
        institution_id=apex.id,
        job_type="TIMETABLE_SOLVE",
        input_reference={"test": "single_claim"},
    )

    # 2. Worker A claims the job
    claim_a = JobService.claim_next_job(seeded_db, worker_id="worker-A")
    assert claim_a is not None
    assert claim_a.id == job.id
    assert claim_a.lease_owner == "worker-A"

    # 3. Worker B immediately attempts to claim next job -> MUST return None
    claim_b = JobService.claim_next_job(seeded_db, worker_id="worker-B")
    assert claim_b is None, "Worker B must not claim an already active job!"


# ==============================================================================
# 7. Per-Institution Concurrency Limits
# ==============================================================================
def test_per_institution_concurrency_limits(seeded_db):
    """Verifies that per-institution concurrency caps prevent monopolization."""
    apex = seeded_db.query(Institution).filter(Institution.code == "APEX").first()

    # Create 3 jobs for APEX
    job_1 = JobService.create_job(seeded_db, apex.id, "TEST", {"n": 1})
    job_2 = JobService.create_job(seeded_db, apex.id, "TEST", {"n": 2})
    job_3 = JobService.create_job(seeded_db, apex.id, "TEST", {"n": 3})

    max_conc = 2

    # Claim 1st job
    c1 = JobService.claim_next_job(seeded_db, "worker-1", max_institution_concurrency=max_conc)
    assert c1 is not None

    # Claim 2nd job
    c2 = JobService.claim_next_job(seeded_db, "worker-2", max_institution_concurrency=max_conc)
    assert c2 is not None

    # Attempt to claim 3rd job: APEX already has 2 RUNNING jobs, so claim should return None
    c3 = JobService.claim_next_job(seeded_db, "worker-3", max_institution_concurrency=max_conc)
    assert c3 is None, "Exceeded institution concurrency limit!"

    # Finalize job 1
    JobService.finalize_success(seeded_db, c1.id, c1.lease_token, {"done": True})

    # Now attempt to claim 3rd job again -> should succeed
    c3_again = JobService.claim_next_job(seeded_db, "worker-3", max_institution_concurrency=max_conc)
    assert c3_again is not None
    assert c3_again.id == job_3.id


# ==============================================================================
# 8. Maximum Attempts & Retry Backoff
# ==============================================================================
def test_max_attempts_and_retry_backoff(seeded_db):
    """Verifies that failed jobs are retried up to max_attempts, then transition to FAILED."""
    apex = seeded_db.query(Institution).filter(Institution.code == "APEX").first()

    # Create job with max_attempts = 2
    job = JobService.create_job(
        db=seeded_db,
        institution_id=apex.id,
        job_type="GENERIC_TASK",
        input_reference={"fail": True},
        max_attempts=2,
    )

    # Claim attempt 1
    c1 = JobService.claim_next_job(seeded_db, "worker-retry-1")
    assert c1.attempt_count == 1

    # Fail attempt 1
    JobService.finalize_failure(
        seeded_db,
        job.id,
        c1.lease_token,
        error_code="TRANSIENT_ERROR",
        error_message="Database lock timeout",
        retry_delay_seconds=1,
    )

    seeded_db.refresh(job)
    assert job.status == JobStatus.QUEUED.value
    assert job.attempt_count == 1
    assert "Queued for retry" in job.phase_label

    # Fast forward available_at to now
    job.available_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    seeded_db.commit()

    # Claim attempt 2
    c2 = JobService.claim_next_job(seeded_db, "worker-retry-2")
    assert c2.attempt_count == 2

    # Fail attempt 2 (reaches max_attempts)
    JobService.finalize_failure(
        seeded_db,
        job.id,
        c2.lease_token,
        error_code="PERMANENT_ERROR",
        error_message="Repeated solver timeout",
    )

    seeded_db.refresh(job)
    assert job.status == JobStatus.FAILED.value
    assert job.error_code == "PERMANENT_ERROR"
    assert job.finished_at is not None

