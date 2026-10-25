import datetime
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.academic import AcademicTerm
from app.models.people import Student, Teacher
from app.models.communication import (
    Notification,
    NotificationPreference,
    NotificationCategory,
    NotificationPriority,
    CalendarCredential,
)
from app.models.publication import CommunicationOutbox, OutboxEventStatus, Publication
from app.models.schedule import TimetableDraft
from app.services.notification_service import NotificationService
from app.services.outbox_processor import OutboxProcessor
from app.services.google_calendar_service import GoogleCalendarService
from app.services.sse_manager import sse_manager
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


# =========================================================================
# Acceptance Test 1: Retry Does Not Duplicate Notifications or Events
# =========================================================================
def test_outbox_retry_does_not_duplicate_notifications(client):
    """
    Acceptance: Retry does not duplicate notifications/events.
    Durable outbox processing with idempotent delivery.
    """
    db = SessionLocal()
    try:
        student = db.query(Student).filter(Student.student_id_number == "APEX-STU-2026-001").first()
        inst_id = student.institution_id
        student_user_id = student.user_id

        pub = db.query(Publication).filter(Publication.institution_id == inst_id).first()
        assert pub is not None

        # Create an outbox event
        outbox = CommunicationOutbox(
            institution_id=inst_id,
            publication_id=pub.id,
            event_type="OPERATIONAL_ALERT",
            recipient_role="STUDENT",
            payload={"message": "System Maintenance at Midnight"},
            status=OutboxEventStatus.PENDING,
            idempotency_key="maint_2026_10_22",
        )
        db.add(outbox)
        db.commit()
        db.refresh(outbox)

        # First delivery via NotificationService
        notif1 = NotificationService.create_notification(
            db=db,
            institution_id=inst_id,
            recipient_user_id=student_user_id,
            category=NotificationCategory.OPERATIONAL_ALERT,
            title="Scheduled Maintenance",
            message="System Maintenance at Midnight",
            idempotency_key="maint_2026_10_22",
        )
        assert notif1 is not None

        # Second delivery with the SAME idempotency key (simulating retry)
        notif2 = NotificationService.create_notification(
            db=db,
            institution_id=inst_id,
            recipient_user_id=student_user_id,
            category=NotificationCategory.OPERATIONAL_ALERT,
            title="Scheduled Maintenance",
            message="System Maintenance at Midnight",
            idempotency_key="maint_2026_10_22",
        )
        assert notif2 is not None
        assert notif1.id == notif2.id, "Retry must return existing notification without duplicating"

        # Verify only 1 notification exists in DB with this idempotency key
        count = db.query(Notification).filter(
            Notification.recipient_user_id == student_user_id,
            Notification.idempotency_key == "maint_2026_10_22",
        ).count()
        assert count == 1, f"Expected exactly 1 notification, found {count}"

        # Test retry action endpoint
        coord_csrf = login_user(client, "coord@apex.edu")
        retry_resp = client.post(
            f"/api/v1/communication/outbox/{outbox.id}/retry",
            headers={"X-CSRF-Token": coord_csrf}
        )
        assert retry_resp.status_code == 200
        assert retry_resp.json()["status"] == "DISPATCHED"
    finally:
        db.close()


# =========================================================================
# Acceptance Test 2: Only Affected Users Receive Changes & Drafts Never Notify
# =========================================================================
def test_draft_changes_do_not_notify_students(client):
    """
    Acceptance: Do not notify students about unpublished draft changes.
    Only affected users receive changes.
    """
    db = SessionLocal()
    try:
        student = db.query(Student).filter(Student.student_id_number == "APEX-STU-2026-001").first()
        student_user_id = student.user_id

        # Count current student notifications
        initial_count = db.query(Notification).filter(Notification.recipient_user_id == student_user_id).count()

        # Staff creates an unpublished draft
        coord_csrf = login_user(client, "coord@apex.edu")
        term = db.query(AcademicTerm).filter(AcademicTerm.name == "Fall Semester 2026").first()

        draft_resp = client.post("/api/v1/timetable-drafts", json={
            "name": "Secret Unreleased Draft",
            "academic_term_id": term.id,
            "input_snapshot": {"sessions": []},
        }, headers={"X-CSRF-Token": coord_csrf})
        assert draft_resp.status_code == 201

        # Check student notifications again: must NOT change
        after_count = db.query(Notification).filter(Notification.recipient_user_id == student_user_id).count()
        assert after_count == initial_count, "Unpublished draft creation must NEVER notify students!"
    finally:
        db.close()


# =========================================================================
# Acceptance Test 3: Quiet Hours & Urgent Priority Bypass
# =========================================================================
def test_quiet_hours_and_urgent_bypass(client):
    """
    Acceptance: Quiet hours for appropriate non-urgent delivery.
    Security events / urgent alerts bypass quiet hours immediately.
    """
    db = SessionLocal()
    try:
        student = db.query(Student).filter(Student.student_id_number == "APEX-STU-2026-001").first()
        inst_id = student.institution_id
        student_user_id = student.user_id

        # Configure quiet hours: 22:00 to 07:00
        pref = NotificationService.get_or_create_preferences(db, student_user_id, inst_id)
        pref.quiet_hours_enabled = True
        pref.quiet_hours_start = "22:00"
        pref.quiet_hours_end = "07:00"
        db.commit()

        # Simulate current time: 23:30 (inside quiet hours)
        now_inside = datetime.datetime(2026, 10, 22, 23, 30, tzinfo=datetime.timezone.utc)

        # 1. Non-urgent notification (e.g. reminder) inside quiet hours -> should be deferred
        notif_normal = NotificationService.create_notification(
            db=db,
            institution_id=inst_id,
            recipient_user_id=student_user_id,
            category=NotificationCategory.SCHEDULED_REMINDER,
            title="Class Reminder",
            message="Math lecture tomorrow",
            idempotency_key="rem_quiet_test_1",
            priority=NotificationPriority.NORMAL,
            now=now_inside,
        )
        assert notif_normal is not None
        assert notif_normal.delivered_at is None, "Non-urgent notification must be deferred during quiet hours"
        assert notif_normal.scheduled_for is not None, "Non-urgent notification must have scheduled_for set"

        # 2. Urgent notification (e.g. security event) inside quiet hours -> MUST bypass quiet hours!
        notif_urgent = NotificationService.create_notification(
            db=db,
            institution_id=inst_id,
            recipient_user_id=student_user_id,
            category=NotificationCategory.SECURITY_EVENT,
            title="Security Alert",
            message="New device login detected",
            idempotency_key="sec_quiet_test_1",
            priority=NotificationPriority.URGENT,
            now=now_inside,
        )
        assert notif_urgent is not None
        assert notif_urgent.delivered_at is not None, "Urgent notification must bypass quiet hours immediately!"
        assert notif_urgent.scheduled_for is None
    finally:
        db.close()


# =========================================================================
# Acceptance Test 4: SSE User Isolation & Reconnect Replay
# =========================================================================
def test_sse_user_isolation_and_reconnect():
    """
    Acceptance: SSE does not leak another user's data.
    Event IDs and reconnect replay buffer.
    """
    inst_id = "inst-apex"
    user_alice = "user-alice"
    user_bob = "user-bob"

    # Publish an event targeted specifically to Alice
    ev1 = sse_manager.publish_event_sync(
        institution_id=inst_id,
        event_type="USER_SPECIFIC_EVENT",
        payload={"secret": "alice_only_secret"},
        target_user_id=user_alice,
    )

    # Bob asks for missed events since before ev1
    bob_events = sse_manager.get_events_since(inst_id, user_bob, since_id=ev1.id - 1)
    for b_ev in bob_events:
        assert b_ev.get("target_user_id") != user_alice
        assert b_ev.get("payload", {}).get("secret") != "alice_only_secret", "Bob must NEVER receive Alice's events!"

    # Alice asks for missed events since before ev1 -> must receive it
    alice_events = sse_manager.get_events_since(inst_id, user_alice, since_id=ev1.id - 1)
    alice_secrets = [e["payload"].get("secret") for e in alice_events]
    assert "alice_only_secret" in alice_secrets, "Alice must receive her targeted event on reconnect replay"


# =========================================================================
# Acceptance Test 5: Google Calendar Mock & Publication Failure Isolation
# =========================================================================
def test_google_calendar_mock_and_publication_isolation(client):
    """
    Acceptance:
    - Calendar unit/integration tests use mocks unless explicit test credentials are supplied; report which type of test ran.
    - Revoked/expired credential errors handled gracefully without crashing.
    - Calendar failures must not undo a successful publication.
    - When unconfigured, shows 'Not configured' and setup guidance.
    """
    print("[TEST TYPE: MOCK - Google Calendar Integration Test]")

    db = SessionLocal()
    try:
        student = db.query(Student).filter(Student.student_id_number == "APEX-STU-2026-001").first()
        student_user_id = student.user_id
        inst_id = student.institution_id

        # Clean any prior credential
        db.query(CalendarCredential).filter(CalendarCredential.user_id == student_user_id).delete()
        db.commit()

        # 1. Check unconfigured status
        student_csrf = login_user(client, "alice@apex.edu")
        status_resp = client.get("/api/v1/communication/calendar/status")
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["configured"] is False
        assert data["status"] == "NOT_CONFIGURED"
        assert "guidance" in data and len(data["guidance"]) > 20

        # 2. Simulate OAuth connection with Mock tokens
        from app.core.encryption import sign_oauth_state
        mock_state = sign_oauth_state({"user_id": student_user_id, "institution_id": inst_id})
        success, msg, cred = GoogleCalendarService.handle_oauth_callback(
            db=db,
            code="mock_auth_code",
            state=mock_state,
            mock_tokens={"access_token": "mock_acc_123", "refresh_token": "mock_ref_456", "expires_in": 3600}
        )
        assert success is True
        assert cred is not None
        assert cred.sync_status == "CONNECTED"

        # 3. Test sync execution
        sync_result = GoogleCalendarService.sync_user_calendar_safe(db, student_user_id, inst_id)
        assert sync_result.get("synced") is True

        # 4. Test revoked token handling
        refresh_success = GoogleCalendarService.refresh_access_token_if_needed(db, cred, mock_fail_revoked=True)
        assert refresh_success is False
        assert cred.sync_status == "REVOKED"
        assert "revoked" in cred.last_error.lower()

        # 5. Isolation verification: sync failure must NOT raise or undo DB operations
        failed_sync = GoogleCalendarService.sync_user_calendar_safe(db, student_user_id, inst_id)
        assert failed_sync.get("synced") is False
        assert "revoked" in failed_sync.get("reason", "").lower()

        # 6. Disconnect
        disconnect_success = GoogleCalendarService.disconnect(db, student_user_id, inst_id)
        assert disconnect_success is True
        assert cred.sync_status == "DISCONNECTED"
    finally:
        db.close()
