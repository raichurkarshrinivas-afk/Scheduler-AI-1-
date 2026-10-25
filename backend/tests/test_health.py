import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from app.main import app

client = TestClient(app)


def test_health_live_endpoint():
    """Liveness probe must return 200 OK and live: true without requiring DB."""
    response = client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["live"] is True
    assert "service" in data
    assert "version" in data


def test_health_ready_endpoint_success():
    """Readiness probe returns 200 OK and ready: true when DB is connected."""
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["ready"] is True
    assert data["database"] == "connected"


def test_health_ready_endpoint_db_failure():
    """Readiness probe returns 503 Service Unavailable when DB is disconnected."""
    with patch("app.api.health.engine.connect", side_effect=OperationalError("connection failed", None, None)):
        response = client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unavailable"
        assert data["ready"] is False
        assert data["database"] == "disconnected"
        assert "detail" in data


def test_api_prefixed_health_endpoints():
    """Verify that same-origin proxy paths (/api/health/live and /api/health/ready) work."""
    live_resp = client.get("/api/health/live")
    assert live_resp.status_code == 200
    assert live_resp.json()["live"] is True

    ready_resp = client.get("/api/health/ready")
    assert ready_resp.status_code == 200
    assert ready_resp.json()["ready"] is True


def test_general_health_overview():
    """Verify general /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["live"] is True
    assert data["ready"] is True
