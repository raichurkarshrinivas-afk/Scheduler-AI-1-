import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.feedback import FeedbackSubmission, FeedbackStatus, FeedbackInternalNote
from app.models.institution import Institution
from app.models.people import Student
from app.models.user import User, Membership, UserRole
from app.services.feedback_service import public_feedback_limiter
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
# Acceptance 1: Anonymous Valid Submission
# =========================================================================
def test_anonymous_valid_submission(client):
    """
    Acceptance: Anonymous valid submission.
    Generic confirmation that does not expose internal records or UUIDs.
    Confirmation reflects actual database persistence.
    """
    public_feedback_limiter.reset_for_testing()

    payload = {
        "contact_name": "Jane Visitor",
        "contact_email": "visitor@example.org",
        "category": "GENERAL_INQUIRY",
        "subject": "Inquiry regarding campus scheduling",
        "message": "We are interested in learning how Scheduler handles multi-building practical lab sessions.",
    }

    resp = client.post("/api/v1/feedback/public", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["success"] is True
    assert "reference_code" in data
    ref_code = data["reference_code"]
    assert ref_code.startswith("FB-")
    # Verify internal UUID is NOT exposed
    assert "id" not in data

    # Verify actual database persistence
    db = SessionLocal()
    try:
        sub = db.query(FeedbackSubmission).filter(FeedbackSubmission.reference_code == ref_code).first()
        assert sub is not None
        assert sub.subject == payload["subject"]
        assert sub.message == payload["message"]
        assert sub.contact_name == "Jane Visitor"
        assert sub.contact_email == "visitor@example.org"
        assert sub.institution_id is None, "Public submissions must have null institution_id"
        assert sub.submitting_user_id is None, "Public submissions must have null submitting_user_id"
        assert sub.status == "new"
    finally:
        db.close()


# =========================================================================
# Acceptance 2: Authenticated Submission
# =========================================================================
def test_authenticated_feedback_submission(client):
    """
    Acceptance: Authenticated submission.
    User and institution association derived strictly from session.
    """
    student_csrf = login_user(client, "alice@apex.edu")

    payload = {
        "category": "SUGGESTION",
        "subject": "Add dark mode toggle for mobile timetable",
        "message": "It would be wonderful to toggle high-contrast dark mode during evening study sessions.",
        "page_reference": "/student/timetable",
    }

    resp = client.post("/api/v1/feedback/submit", json=payload, headers={"X-CSRF-Token": student_csrf})
    assert resp.status_code == 200
    data = resp.json()

    assert data["subject"] == payload["subject"]
    assert data["category"] == "SUGGESTION"
    assert data["page_reference"] == "/student/timetable"
    assert data["status"] == "new"
    ref_code = data["reference_code"]

    db = SessionLocal()
    try:
        student = db.query(Student).filter(Student.student_id_number == "APEX-STU-2026-001").first()
        sub = db.query(FeedbackSubmission).filter(FeedbackSubmission.reference_code == ref_code).first()
        assert sub is not None
        assert sub.submitting_user_id == student.user_id, "User ID must be derived from session"
        assert sub.institution_id == student.institution_id, "Institution ID must be derived from session"
    finally:
        db.close()


# =========================================================================
# Acceptance 3: Invalid and Oversized Content Rejected
# =========================================================================
def test_invalid_and_oversized_content_rejected(client):
    """
    Acceptance: Server-side field and size validation. Invalid/oversized content rejected.
    """
    public_feedback_limiter.reset_for_testing()

    # 1. Subject too short (< 3 chars)
    resp1 = client.post("/api/v1/feedback/public", json={
        "subject": "Hi",
        "message": "This is a valid length message here.",
    })
    assert resp1.status_code == 422 or resp1.status_code == 400

    # 2. Message too short (< 10 chars)
    resp2 = client.post("/api/v1/feedback/public", json={
        "subject": "Valid Subject Line",
        "message": "Too short",
    })
    assert resp2.status_code == 422 or resp2.status_code == 400

    # 3. Message oversized (> 5000 chars)
    resp3 = client.post("/api/v1/feedback/public", json={
        "subject": "Valid Subject Line",
        "message": "A" * 5001,
    })
    assert resp3.status_code == 422 or resp3.status_code == 400

    # 4. Invalid email format
    resp4 = client.post("/api/v1/feedback/public", json={
        "contact_email": "not-an-email",
        "subject": "Valid Subject Line",
        "message": "This is a valid length message here.",
    })
    assert resp4.status_code == 422 or resp4.status_code == 400


# =========================================================================
# Acceptance 4: Rate Limiting
# =========================================================================
def test_public_contact_rate_limiting(client):
    """
    Acceptance: Rate limits.
    Rapid excessive submissions from same IP rejected with 429.
    """
    public_feedback_limiter.reset_for_testing()

    valid_payload = {
        "subject": "Inquiry Subject",
        "message": "This is a legitimate message from a user inquiring about features.",
    }

    # 5 allowed submissions
    for i in range(5):
        r = client.post("/api/v1/feedback/public", json=valid_payload)
        assert r.status_code == 200, f"Attempt {i+1} should succeed"

    # 6th submission must trigger 429
    r6 = client.post("/api/v1/feedback/public", json=valid_payload)
    assert r6.status_code == 429, f"Attempt 6 must be rate-limited, got {r6.status_code}"
    assert "rate limit exceeded" in r6.json()["detail"].lower()

    public_feedback_limiter.reset_for_testing()


# =========================================================================
# Acceptance 5: Bot-Abuse Mitigation (Honeypot Trap)
# =========================================================================
def test_bot_abuse_honeypot_trap(client):
    """
    Acceptance: Basic bot-abuse mitigation.
    Honeypot trap traps automated bots without persisting spam.
    """
    public_feedback_limiter.reset_for_testing()

    bot_payload = {
        "subject": "Buy crypto tokens now!",
        "message": "Visit our malicious spam link right now for massive returns.",
        "honeypot": "I am an automated spam bot filling hidden inputs",
    }

    resp = client.post("/api/v1/feedback/public", json=bot_payload)
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Confirm spam was NOT inserted into database
    db = SessionLocal()
    try:
        spam = db.query(FeedbackSubmission).filter(FeedbackSubmission.subject == "Buy crypto tokens now!").first()
        assert spam is None, "Spam caught by honeypot must not be persisted in database"
    finally:
        db.close()


# =========================================================================
# Acceptance 6: Stored-XSS Payload Remains Inert Plain Text
# =========================================================================
def test_stored_xss_payload_remains_inert(client):
    """
    Acceptance: Stored-XSS payload remains inert.
    Never render submitted content as trusted HTML.
    """
    public_feedback_limiter.reset_for_testing()

    xss_subject = "<script>alert('XSS-SUBJECT')</script>"
    xss_message = "<img src=x onerror=alert('XSS-PAYLOAD')>Hello <b>World</b>"

    resp = client.post("/api/v1/feedback/public", json={
        "subject": xss_subject,
        "message": xss_message,
    })
    assert resp.status_code == 200
    ref_code = resp.json()["reference_code"]

    db = SessionLocal()
    try:
        sub = db.query(FeedbackSubmission).filter(FeedbackSubmission.reference_code == ref_code).first()
        assert sub is not None
        # Stored faithfully without unescaped execution or loss
        assert sub.subject == xss_subject
        assert sub.message == xss_message

        # Coordinator reviews the submission
        coord_csrf = login_user(client, "admin@apex.edu")
        detail_resp = client.get(f"/api/v1/feedback/manage/{sub.id}", headers={"X-CSRF-Token": coord_csrf})
        assert detail_resp.status_code == 200
        data = detail_resp.json()
        assert data["subject"] == xss_subject
        assert data["message"] == xss_message
    finally:
        db.close()


# =========================================================================
# Acceptance 7: Student Sees Only Their Own Submissions & No Internal Notes
# =========================================================================
def test_student_isolation_and_internal_notes_protection(client):
    """
    Acceptance:
    - Student sees only their own submissions.
    - Internal notes in a separately protected structure (never returned to student).
    """
    student_csrf = login_user(client, "alice@apex.edu")

    # 1. Alice submits feedback
    sub_resp = client.post("/api/v1/feedback/submit", json={
        "category": "ACCESS_ISSUE",
        "subject": "Lab 102 Card Access",
        "message": "My student ID card fails on the electronic lock at Room 102.",
    }, headers={"X-CSRF-Token": student_csrf})
    assert sub_resp.status_code == 200
    alice_sub_id = sub_resp.json()["id"]

    # 2. Staff adds an internal reviewer note
    admin_csrf = login_user(client, "admin@apex.edu")
    note_resp = client.post(
        f"/api/v1/feedback/manage/{alice_sub_id}/notes",
        json={"note": "Confidential internal note: Contact Campus Security facility manager directly."},
        headers={"X-CSRF-Token": admin_csrf}
    )
    assert note_resp.status_code == 200

    # 3. Staff updates status to reviewing
    status_resp = client.patch(
        f"/api/v1/feedback/manage/{alice_sub_id}/status",
        json={"status": "reviewing"},
        headers={"X-CSRF-Token": admin_csrf}
    )
    assert status_resp.status_code == 200

    # 4. Alice checks her submissions:
    # - Must contain her submission
    # - Must NOT contain internal notes
    student_csrf = login_user(client, "alice@apex.edu")
    my_resp = client.get("/api/v1/feedback/my-submissions", headers={"X-CSRF-Token": student_csrf})
    assert my_resp.status_code == 200
    my_submissions = my_resp.json()
    assert any(s["id"] == alice_sub_id for s in my_submissions)
    for s in my_submissions:
        assert "internal_notes" not in s, "Internal notes must NEVER be exposed in student submissions endpoint!"

    # 5. Bob (different student) checks his submissions:
    # - Must NOT see Alice's submission
    bob_csrf = login_user(client, "bob@apex.edu")
    bob_resp = client.get("/api/v1/feedback/my-submissions", headers={"X-CSRF-Token": bob_csrf})
    assert bob_resp.status_code == 200
    bob_sub_ids = [s["id"] for s in bob_resp.json()]
    assert alice_sub_id not in bob_sub_ids, "Bob must NEVER see Alice's submitted feedback"


# =========================================================================
# Acceptance 8: Cross-Institution Review Denied
# =========================================================================
def test_cross_institution_review_denied(client):
    """
    Acceptance:
    - Institution feedback visible only to permitted institution reviewers.
    - Cross-institution review denied (403 Forbidden).
    """
    db = SessionLocal()
    try:
        beacon_inst = db.query(Institution).filter(Institution.code == "BEACON").first()
        assert beacon_inst is not None

        # Create a feedback item belonging strictly to Beacon University
        beacon_sub = FeedbackSubmission(
            reference_code=f"FB-BCN-{__import__('uuid').uuid4().hex[:6].upper()}",
            institution_id=beacon_inst.id,
            category="SCHEDULING_ISSUE",
            subject="Beacon Exam Clash Issue",
            message="Clash between CS-301 and EE-201 scheduled for Monday morning.",
            status=FeedbackStatus.NEW.value,
        )
        db.add(beacon_sub)
        db.commit()
        beacon_sub_id = beacon_sub.id
    finally:
        db.close()

    # Coordinator at APEX tries to access Beacon's feedback
    apex_coord_csrf = login_user(client, "coord@apex.edu", institution_code="APEX")

    cross_resp = client.get(
        f"/api/v1/feedback/manage/{beacon_sub_id}",
        headers={"X-CSRF-Token": apex_coord_csrf}
    )
    assert cross_resp.status_code == 403, "Staff from APEX must be denied access to Beacon University feedback!"
    assert "cross-institution" in cross_resp.json()["detail"].lower()
