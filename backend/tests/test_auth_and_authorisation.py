import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal
from app.core.config import settings
from app.core.security import hash_password, hash_session_token
from app.models.institution import Institution
from app.models.user import User, Membership, UserRole, UserSession
from app.models.people import Teacher, Student
from app.models.audit import AuditEvent
from app.seeds.seed import run_seed


@pytest.fixture(scope="module")
def seeded_db():
    """Ensures database has fresh seed data before test suite runs."""
    db = SessionLocal()
    run_seed(db)
    yield db
    db.close()


@pytest.fixture
def client():
    return TestClient(app, base_url="http://testserver")


# ==============================================================================
# 1. Successful Login for Each Role & Identifier Resolution
# ==============================================================================

@pytest.mark.parametrize("email,role", [
    ("admin@apex.edu", UserRole.INSTITUTION_ADMINISTRATOR),
    ("coord@apex.edu", UserRole.TIMETABLE_COORDINATOR),
    ("exam@apex.edu", UserRole.EXAM_CONTROLLER),
    ("smith@apex.edu", UserRole.TEACHER),
    ("alice@apex.edu", UserRole.STUDENT),
])
def test_successful_login_for_each_role_by_email(client, seeded_db, email, role):
    response = client.post("/api/v1/auth/login", json={
        "institution_code": "APEX",
        "identifier": email,
        "password": "DevSeed2026!#",
    })
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["user"]["email"] == email
    assert data["user"]["role"] == role.value
    assert data["user"]["institution_code"] == "APEX"
    assert "csrf_token" in data
    assert len(data["csrf_token"]) > 20

    # Verify HttpOnly cookie is set
    session_cookie = response.cookies.get(settings.SESSION_COOKIE_NAME)
    assert session_cookie is not None
    assert len(session_cookie) > 20

    # Verify raw token is NOT stored in DB, only token_hash
    token_hash = hash_session_token(session_cookie)
    db_session = seeded_db.query(UserSession).filter_by(session_token_hash=token_hash).first()
    assert db_session is not None
    assert db_session.user_id == data["user"]["id"]


def test_teacher_login_via_assigned_employee_id(client, seeded_db):
    """Teachers can log in using their assigned employee ID (e.g. APEX-FAC-101)."""
    response = client.post("/api/v1/auth/login", json={
        "institution_code": "APEX",
        "identifier": "APEX-FAC-101",
        "password": "DevSeed2026!#",
    })
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["user"]["email"] == "smith@apex.edu"
    assert data["user"]["employee_id"] == "APEX-FAC-101"
    assert data["user"]["role"] == UserRole.TEACHER.value


def test_student_login_via_institution_scoped_prn(client, seeded_db):
    """Students can log in using their institution-scoped PRN/roll number (e.g. APEX-STU-2026-001)."""
    response = client.post("/api/v1/auth/login", json={
        "institution_code": "APEX",
        "identifier": "APEX-STU-2026-001",
        "password": "DevSeed2026!#",
    })
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["user"]["email"] == "alice@apex.edu"
    assert data["user"]["roll_number"] == "APEX-STU-2026-001"
    assert data["user"]["role"] == UserRole.STUDENT.value


# ==============================================================================
# 2. Generic Login Failures (No Account Existence Disclosure)
# ==============================================================================

def test_generic_failure_invalid_password(client):
    res = client.post("/api/v1/auth/login", json={
        "institution_code": "APEX",
        "identifier": "admin@apex.edu",
        "password": "WrongPassword123!",
    })
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid credentials."


def test_generic_failure_nonexistent_user(client):
    res = client.post("/api/v1/auth/login", json={
        "institution_code": "APEX",
        "identifier": "nonexistent_ghost@apex.edu",
        "password": "AnyPassword123!",
    })
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid credentials."


def test_generic_failure_nonexistent_institution(client):
    res = client.post("/api/v1/auth/login", json={
        "institution_code": "NONEXISTENT_ORG",
        "identifier": "admin@apex.edu",
        "password": "AnyPassword123!",
    })
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid credentials."


# ==============================================================================
# 3. Student Ownership Isolation (Student Cannot Access Another Student's Record)
# ==============================================================================

def test_student_cannot_access_another_students_record(client, seeded_db):
    # Retrieve student IDs for Alice and Bob
    alice_student = seeded_db.query(Student).filter_by(student_id_number="APEX-STU-2026-001").first()
    bob_student = seeded_db.query(Student).filter_by(student_id_number="APEX-STU-2026-002").first()
    assert alice_student and bob_student

    # Log in as Alice
    login_res = client.post("/api/v1/auth/login", json={
        "institution_code": "APEX",
        "identifier": "alice@apex.edu",
        "password": "DevSeed2026!#",
    })
    assert login_res.status_code == 200

    # 1. Alice accessing her own record -> 200 OK
    own_res = client.get(f"/api/v1/students/{alice_student.id}")
    assert own_res.status_code == 200
    assert own_res.json()["roll_number"] == "APEX-STU-2026-001"

    # 2. Alice accessing Bob's record -> 403 Forbidden!
    foreign_res = client.get(f"/api/v1/students/{bob_student.id}")
    assert foreign_res.status_code == 403
    assert "Access denied: Students may only access their own educational records." in foreign_res.json()["detail"]


# ==============================================================================
# 4. Cross-Institution Access Denied
# ==============================================================================

def test_cross_institution_admin_reset_denied(client, seeded_db):
    # Charlie belongs to BEACON institution
    charlie = seeded_db.query(User).filter_by(email="charlie@beacon.edu").first()
    assert charlie is not None

    # Log in as APEX administrator
    login_res = client.post("/api/v1/auth/login", json={
        "institution_code": "APEX",
        "identifier": "admin@apex.edu",
        "password": "DevSeed2026!#",
    })
    assert login_res.status_code == 200
    csrf_token = login_res.json()["csrf_token"]

    # APEX admin attempts to reset password for user in BEACON -> 404 / denied
    reset_res = client.post(
        f"/api/v1/admin/users/{charlie.id}/reset-password",
        headers={"X-CSRF-Token": csrf_token},
        json={"temporary_password": "NewTempPass2026!#"},
    )
    assert reset_res.status_code == 404
    assert "User not found in your institution." in reset_res.json()["detail"]


# ==============================================================================
# 5. CSRF Protection for State-Changing Requests
# ==============================================================================

def test_csrf_missing_token_rejected(client):
    login_res = client.post("/api/v1/auth/login", json={
        "institution_code": "APEX",
        "identifier": "admin@apex.edu",
        "password": "DevSeed2026!#",
    })
    assert login_res.status_code == 200

    # Attempt state-changing logout WITHOUT X-CSRF-Token header -> 403
    logout_res = client.post("/api/v1/auth/logout")
    assert logout_res.status_code == 403
    assert "CSRF validation failed" in logout_res.json()["detail"]


def test_csrf_mismatched_token_rejected(client):
    login_res = client.post("/api/v1/auth/login", json={
        "institution_code": "APEX",
        "identifier": "admin@apex.edu",
        "password": "DevSeed2026!#",
    })
    assert login_res.status_code == 200

    # Attempt state-changing logout with invalid CSRF token -> 403
    logout_res = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": "invalid-forged-csrf-token"})
    assert logout_res.status_code == 403
    assert "CSRF validation failed" in logout_res.json()["detail"]


# ==============================================================================
# 6. Logout & Session Invalidation
# ==============================================================================

def test_logout_invalidates_session(client):
    login_res = client.post("/api/v1/auth/login", json={
        "institution_code": "APEX",
        "identifier": "admin@apex.edu",
        "password": "DevSeed2026!#",
    })
    csrf_token = login_res.json()["csrf_token"]

    # Verify authenticated
    me_res = client.get("/api/v1/me")
    assert me_res.status_code == 200

    # Perform logout
    logout_res = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert logout_res.status_code == 200

    # Verify session is now invalidated
    me_after = client.get("/api/v1/me")
    assert me_after.status_code == 401


# ==============================================================================
# 7. Password Reset & Forced Password Change Workflow
# ==============================================================================

def test_admin_reset_workflow_and_forced_password_change(client, seeded_db):
    bob = seeded_db.query(User).filter_by(email="bob@apex.edu").first()
    assert bob is not None

    # 1. Log in as APEX Admin and reset Bob's password
    admin_login = client.post("/api/v1/auth/login", json={
        "institution_code": "APEX",
        "identifier": "admin@apex.edu",
        "password": "DevSeed2026!#",
    })
    admin_csrf = admin_login.json()["csrf_token"]

    temp_pwd = "TempBobPass2026!#"
    reset_res = client.post(
        f"/api/v1/admin/users/{bob.id}/reset-password",
        headers={"X-CSRF-Token": admin_csrf},
        json={"temporary_password": temp_pwd},
    )
    assert reset_res.status_code == 200
    assert reset_res.json()["must_change_password"] is True

    # 2. Bob logs in with temporary password
    bob_login = client.post("/api/v1/auth/login", json={
        "institution_code": "APEX",
        "identifier": "bob@apex.edu",
        "password": temp_pwd,
    })
    assert bob_login.status_code == 200
    assert bob_login.json()["must_change_password"] is True
    bob_csrf = bob_login.json()["csrf_token"]

    # 3. Bob tries to access protected resource before changing password -> 403 Forbidden!
    bob_student = seeded_db.query(Student).filter_by(user_id=bob.id).first()
    blocked_res = client.get(f"/api/v1/students/{bob_student.id}")
    assert blocked_res.status_code == 403
    assert blocked_res.headers.get("X-Error-Code") == "PASSWORD_CHANGE_REQUIRED"

    # 4. Bob changes password
    new_perm_pwd = "BobPermanentPass2026!#"
    change_res = client.post(
        "/api/v1/auth/change-password",
        headers={"X-CSRF-Token": bob_csrf},
        json={
            "current_password": temp_pwd,
            "new_password": new_perm_pwd,
        },
    )
    assert change_res.status_code == 200

    # 5. Bob can now access protected resource
    allowed_res = client.get(f"/api/v1/students/{bob_student.id}")
    assert allowed_res.status_code == 200
    assert allowed_res.json()["roll_number"] == bob_student.roll_number


# ==============================================================================
# 8. Password Change Invalidates Other Active Sessions
# ==============================================================================

def test_password_change_invalidates_other_sessions(client, seeded_db):
    # Log in on "Device 1"
    client1 = TestClient(app, base_url="http://testserver")
    res1 = client1.post("/api/v1/auth/login", json={
        "institution_code": "APEX",
        "identifier": "coord@apex.edu",
        "password": "DevSeed2026!#",
    })
    assert res1.status_code == 200

    # Log in on "Device 2"
    client2 = TestClient(app, base_url="http://testserver")
    res2 = client2.post("/api/v1/auth/login", json={
        "institution_code": "APEX",
        "identifier": "coord@apex.edu",
        "password": "DevSeed2026!#",
    })
    assert res2.status_code == 200
    csrf2 = res2.json()["csrf_token"]

    # Both devices can access /me
    assert client1.get("/api/v1/me").status_code == 200
    assert client2.get("/api/v1/me").status_code == 200

    # Change password from Device 2
    change_res = client2.post(
        "/api/v1/auth/change-password",
        headers={"X-CSRF-Token": csrf2},
        json={
            "current_password": "DevSeed2026!#",
            "new_password": "NewCoordPass2026!#",
        },
    )
    assert change_res.status_code == 200

    # Device 1 is now invalidated (401)
    assert client1.get("/api/v1/me").status_code == 401

    # Device 2 remains authenticated
    assert client2.get("/api/v1/me").status_code == 200

    # Revert password back for idempotency
    client2.post(
        "/api/v1/auth/change-password",
        headers={"X-CSRF-Token": csrf2},
        json={
            "current_password": "NewCoordPass2026!#",
            "new_password": "DevSeed2026!#",
        },
    )


# ==============================================================================
# 9. Session Inspection & Revocation
# ==============================================================================

def test_session_inspection_and_revocation(client):
    login_res = client.post("/api/v1/auth/login", json={
        "institution_code": "APEX",
        "identifier": "exam@apex.edu",
        "password": "DevSeed2026!#",
    })
    csrf_token = login_res.json()["csrf_token"]

    # List active sessions
    sessions_res = client.get("/api/v1/me/sessions")
    assert sessions_res.status_code == 200
    sessions_list = sessions_res.json()
    assert len(sessions_list) >= 1
    current_sess = [s for s in sessions_list if s["is_current"]][0]

    # Revoke session
    del_res = client.delete(
        f"/api/v1/me/sessions/{current_sess['id']}",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert del_res.status_code == 200

    # Now unauthenticated
    assert client.get("/api/v1/me").status_code == 401


# ==============================================================================
# 10. Audit Logging Verification (Zero Secrets Logged)
# ==============================================================================

def test_audit_logging_does_not_record_secrets(client, seeded_db):
    pwd_attempt = "SecretPlainPasswordNotToBeLogged!"
    client.post("/api/v1/auth/login", json={
        "institution_code": "APEX",
        "identifier": "admin@apex.edu",
        "password": pwd_attempt,
    })

    # Query recent audit events
    recent_audits = seeded_db.query(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(10).all()
    assert len(recent_audits) > 0

    for a in recent_audits:
        # Verify plaintext password was never recorded anywhere in audit event
        payload_str = str(a.payload)
        assert pwd_attempt not in payload_str
        assert "password" not in a.payload or a.payload.get("password") is None
        assert "raw_token" not in payload_str
