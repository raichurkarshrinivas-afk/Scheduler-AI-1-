from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine

router = APIRouter(tags=["Health"])


@router.get("/health/live")
def liveness():
    """Liveness probe.
    Does NOT require database connectivity.
    Returns 200 OK as long as the application process is running.
    """
    return {
        "status": "ok",
        "live": True,
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }


@router.get("/health/ready")
def readiness():
    """Readiness probe.
    MUST check database connectivity.
    Returns 200 OK if the database connection succeeds,
    or 503 Service Unavailable if unreachable.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "ready": True,
            "database": "connected",
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
        }
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unavailable",
                "ready": False,
                "database": "disconnected",
                "detail": str(exc),
                "service": settings.PROJECT_NAME,
                "version": settings.VERSION,
            },
        )


@router.get("/health")
def health_overview():
    """General health check summary."""
    ready_status = True
    db_status = "connected"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        ready_status = False
        db_status = "disconnected"

    return {
        "status": "ok" if ready_status else "degraded",
        "live": True,
        "ready": ready_status,
        "database": db_status,
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }
