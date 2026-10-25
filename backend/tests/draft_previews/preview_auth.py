def test_register_institution_and_admin(client):
    response = client.post("/api/v1/auth/register", json={
        "institution_name": "Cambridge Academy",
        "institution_slug": "cambridge-acad",
        "admin_name": "Director Vance",
        "admin_email": "director@cambridge.edu",
        "password": "Password123!"
    })
    assert response.status_code == 201
    data = response.json()
    assert "institution_id" in data
    assert "admin_user_id" in data


def test_register_duplicate_slug_conflict(client, fixture_data):
    response = client.post("/api/v1/auth/register", json={
        "institution_name": "Another Alpha",
        "institution_slug": "alpha-inst",  # duplicate
        "admin_name": "Another Admin",
        "admin_email": "different@alpha.edu",
        "password": "Password123!"
    })
    assert response.status_code == 409


def test_login_success(client, fixture_data):
    response = client.post("/api/v1/auth/login", json={
        "email": "admin@alpha.edu",
        "password": "AlphaAdminPass123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "admin@alpha.edu"
    assert data["user"]["role"] == "ADMIN"
    assert data["user"]["institution_id"] == fixture_data["inst_a"].id


def test_login_invalid_password(client, fixture_data):
    response = client.post("/api/v1/auth/login", json={
        "email": "admin@alpha.edu",
        "password": "WrongPassword"
    })
    assert response.status_code == 401


def test_get_current_user_me(client, fixture_data):
    headers = {"Authorization": f"Bearer {fixture_data['token_admin_a']}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@alpha.edu"
    assert data["role"] == "ADMIN"


def test_unauthenticated_request_rejected(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
