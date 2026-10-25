import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.main import app
from app.core.database import SessionLocal
from app.core.security import hash_session_token
from app.models.institution import Institution
from app.models.academic import AcademicTerm
from app.models.user import User, UserSession
from app.models.job import Job, JobStatus, JobType
from app.models.publication import CommunicationOutbox, OutboxEventStatus, Publication
from app.models.communication import CalendarCredential
from app.services.job_service import JobService
from app.services.outbox_processor import OutboxProcessor
from app.services.google_calendar_service import GoogleCalendarService
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
# Failure 1: Database Unavailable
# =========================================================================
def test_failure_database_unavailable(client):
    """
    Failure Test: Database becomes temporarily unreachable.
    Liveness probe (/health/live) must return 200 OK without requiring DB.
    Readiness probe (/health/ready) must return 503 Service Unavailable.
    """
    live_resp = client.get("/health/live")
    assert live_resp.status_code == 200
    assert live_resp.json()["status"] == "ok"

    with patch("app.api.health.engine.connect", side_effect=OperationalError("Connection refused to PostgreSQL", None, None)):
        ready_resp = client.get("/health/ready")
        assert ready_resp.status_code == 503
        data = ready_resp.json()
        assert data["status"] == "unavailable"
        assert data["ready"] is False
        assert data["database"] == "disconnected"


# =========================================================================
# Failure 2: Worker Process Terminated (Expired Lease Recovery)
# =========================================================================
def test_failure_worker_terminated_lease_recovery():
    """
    Failure Test: Worker process dies mid-execution leaving a RUNNING job.
    Supervisor scan (JobService.recover_expired_leases) must detect expired lease,
    re-queue the job if attempts remain, and update phase label.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        inst = db.query(Institution).filter(Institution.code == "APEX").first()

        dead_worker_job = Job(
            id=str(uuid.uuid4()),
            institution_id=inst.id,
            job_type=JobType.TIMETABLE_SOLVE.value,
            input_reference={"test": "crash_recovery"},
            status=JobStatus.RUNNING.value,
            phase_label="Claimed by dead-worker-101",
            attempt_count=1,
            max_attempts=3,
            lease_owner="dead-worker-101",
            lease_token="dead_token_abc",
            lease_expiry=now - timedelta(seconds=60),  # Expired 60s ago
            heartbeat_at=now - timedelta(seconds=70),
            cancellation_requested=False,
        )
        db.add(dead_worker_job)
        db.commit()

        recovered_count = JobService.recover_expired_leases(db)
        assert recovered_count >= 1

        db.expire_all()
        job = db.query(Job).filter(Job.id == dead_worker_job.id).first()
        assert job.status == JobStatus.QUEUED.value
        assert job.lease_token is None
        assert job.lease_expiry is None
        assert "Recovered from expired lease" in job.phase_label
    finally:
        db.close()


# =========================================================================
# Failure 3: Duplicate Job Execution & Fencing Collision
# =========================================================================
def test_failure_duplicate_job_execution():
    """
    Failure Test: Stale worker attempts to heartbeat or update job after lease reassignment.
    Fencing tokens must reject the stale worker (heartbeat returns False).
    """
    db = SessionLocal()
    try:
        inst = db.query(Institution).filter(Institution.code == "APEX").first()
        now = datetime.now(timezone.utc)

        # Create actively leased job
        running_job = Job(
            id=str(uuid.uuid4()),
            institution_id=inst.id,
            job_type=JobType.TIMETABLE_SOLVE.value,
            input_reference={"test": "fencing"},
            status=JobStatus.RUNNING.value,
            phase_label="Claimed by worker-1",
            attempt_count=1,
            max_attempts=3,
            lease_owner="worker-1",
            lease_token="valid_token_123",
            lease_expiry=now + timedelta(seconds=30),
            heartbeat_at=now,
            cancellation_requested=False,
        )
        db.add(running_job)
        db.commit()

        # Stale worker attempts to heartbeat with invalid token
        success_fencing, cancel_req = JobService.heartbeat(
            db=db,
            job_id=running_job.id,
            lease_token="stale_invalid_token_999",
            lease_duration_seconds=30,
        )

        assert success_fencing is False

        # Legitimate worker heartbeats with valid token
        valid_fencing, cancel_req2 = JobService.heartbeat(
            db=db,
            job_id=running_job.id,
            lease_token="valid_token_123",
            lease_duration_seconds=30,
        )
        assert valid_fencing is True
    finally:
        db.close()


# =========================================================================
# Failure 4: Expired Session Cookie
# =========================================================================
def test_failure_expired_session(client):
    """
    Failure Test: Client presents an expired session cookie.
    Must return HTTP 401 Unauthorized and prompt for re-authentication.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "admin@apex.edu").first()
        inst = db.query(Institution).filter(Institution.code == "APEX").first()
        raw_token = f"expired_test_token_{uuid.uuid4().hex}"
        token_hash = hash_session_token(raw_token)

        now = datetime.now(timezone.utc)
        expired_session = UserSession(
            user_id=user.id,
            institution_id=inst.id,
            csrf_token=uuid.uuid4().hex,
            session_token_hash=token_hash,
            expires_at=now - timedelta(hours=2),
            created_at=now - timedelta(hours=10),
            last_activity_at=now - timedelta(hours=2),
        )
        db.add(expired_session)
        db.commit()

        fresh_client = TestClient(app, cookies={"scheduler_session": raw_token})
        resp = fresh_client.get("/api/v1/me")
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"].lower()
    finally:
        db.close()


# =========================================================================
# Failure 5: External Calendar Service Unavailable
# =========================================================================
def test_failure_calendar_unavailable():
    """
    Failure Test: External calendar API raises an outage/connection error.
    Sync must catch the failure safely without corrupting publication records or crashing.
    """
    db = SessionLocal()
    try:
        inst = db.query(Institution).filter(Institution.code == "APEX").first()
        user = db.query(User).first()

        now = datetime.now(timezone.utc)
        cred = db.query(CalendarCredential).filter(CalendarCredential.user_id == user.id).first()
        if not cred:
            cred = CalendarCredential(
                user_id=user.id,
                institution_id=inst.id,
                calendar_id="cal_outage_test@scheduler.internal",
                encrypted_access_token="enc_token",
                token_expiry=now + timedelta(hours=2),
                sync_status="CONNECTED",
            )
            db.add(cred)
        else:
            cred.sync_status = "CONNECTED"
            cred.calendar_id = "cal_outage_test@scheduler.internal"
            cred.token_expiry = now + timedelta(hours=2)
            cred.last_error = None
        
        # Create a fresh publication with an assignment matching user.id so sync calls create_or_update_event
        db.query(Publication).filter(Publication.source_id == 'source-cal-fail').delete()
        db.commit()
        term = db.query(AcademicTerm).filter(AcademicTerm.institution_id == inst.id).first()
        test_pub = Publication(
            institution_id=inst.id,
            academic_term_id=term.id,
            publication_type="TIMETABLE",
            source_id="source-cal-fail",
            version_number=99999,
            publication_note="Calendar failure test pub",
            published_by_user_id=user.id,
            published_at=now,
            is_active=True,
            snapshot={"assignments": [{"session_id": "sess-cal-fail-1", "teacher_id": str(user.id), "subject_code": "CS101", "room_name": "Lab 101"}]},
        )
        db.add(test_pub)
        db.commit()

        with patch("app.services.google_calendar_service._global_mock_client.create_or_update_event", side_effect=RuntimeError("Google Calendar API 503 Server Error")):
            res = GoogleCalendarService.sync_user_calendar_safe(db, str(user.id), inst.id, publication=test_pub)
            assert res["synced"] is False
            err_str = res.get("error") or res.get("reason") or ""
            assert "503" in err_str

            db.expire_all()
            updated_cred = db.query(CalendarCredential).filter(CalendarCredential.user_id == user.id).first()
            assert updated_cred.last_error is not None
            assert "503" in updated_cred.last_error
    finally:
        db.close()


# =========================================================================
# Failure 6: Outbox Notification Delivery Failure and Retry
# =========================================================================
def test_failure_notification_retry():
    """
    Failure Test: An outbox event fails delivery (e.g. downstream worker unavailable).
    Outbox processor must increment retry_count, log last_error, set status to FAILED,
    and allow idempotent re-dispatch when retried.
    """
    db = SessionLocal()
    try:
        inst = db.query(Institution).filter(Institution.code == "APEX").first()
        term = db.query(AcademicTerm).filter(AcademicTerm.institution_id == inst.id).first()

        pub = db.query(Publication).filter(Publication.institution_id == inst.id).first()
        if not pub:
            pub = Publication(
                institution_id=inst.id,
                academic_term_id=term.id,
                publication_type="TIMETABLE",
                version_number=999,
                publication_note="Test pub for failure test",
                publisher_user_id=inst.id,
                is_active=True,
                snapshot={},
            )
            db.add(pub)
            db.commit()

        bad_event = CommunicationOutbox(
            institution_id=inst.id,
            publication_id=pub.id,
            event_type="TIMETABLE_PUBLISHED",
            recipient_role="ALL",
            payload={"publication_note": "Failing event test"},
            status=OutboxEventStatus.PENDING,
            retry_count=0,
            max_retries=3,
        )
        db.add(bad_event)
        db.commit()

        # Simulate downstream notification delivery failure
        with patch("app.services.notification_service.NotificationService.get_affected_users_for_publication", side_effect=RuntimeError("Downstream delivery worker unavailable")):
            success = OutboxProcessor.process_single_event(db, bad_event)
            assert success is False

        db.expire_all()
        failed_ev = db.query(CommunicationOutbox).filter(CommunicationOutbox.id == bad_event.id).first()
        assert failed_ev.status == OutboxEventStatus.FAILED
        assert failed_ev.retry_count == 1
        assert failed_ev.last_error is not None
        assert "downstream delivery" in failed_ev.last_error.lower()
        assert failed_ev.next_retry_at is not None

        # Manual retry request re-attempts execution and succeeds once downstream is restored
        re_ev = OutboxProcessor.retry_event(db, bad_event.id)
        assert re_ev is not None
        assert re_ev.status == OutboxEventStatus.DISPATCHED
        assert re_ev.last_error is None
    finally:
        db.close()


# =========================================================================
# Failure 7: Export Error Handling
# =========================================================================
def test_failure_export_error_handling(client):
    """
    Failure Test: Requesting export for a nonexistent exam sitting or corrupt ID.
    Must return HTTP 404 cleanly without 500 internal server error or process crash.
    """
    csrf = login_user(client, "admin@apex.edu", "APEX")
    resp = client.get("/api/v1/exams/sittings/00000000-0000-0000-0000-000000000000/export-labels", headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()
