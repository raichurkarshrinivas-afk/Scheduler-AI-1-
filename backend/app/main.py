from app.core.logging_config import setup_logging
setup_logging()
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
import app.models  # Ensure all SQLAlchemy models are registered
from app.api.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.timetable_drafts import router as timetable_drafts_router
from app.api.v1.exams import router as exams_router
from app.api.v1.publications import router as publications_router
from app.api.v1.student import router as student_router
from app.api.v1.communication import router as communication_router
from app.api.v1.feedback import router as feedback_router
from app.api.v1.ai import router as ai_router


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health endpoints available at both /health/... and /api/health/...
app.include_router(health_router)
app.include_router(health_router, prefix="/api")

# Phase 3 Auth and Authorisation router
app.include_router(auth_router, prefix=settings.API_V1_STR)

# Phase 6 Background Jobs router
app.include_router(jobs_router, prefix=settings.API_V1_STR)

# Phase 7 Timetable Drafts router
app.include_router(timetable_drafts_router, prefix=settings.API_V1_STR)

# Phase 9 Exam Logistics router
app.include_router(exams_router, prefix=settings.API_V1_STR)

# Phase 10 Controlled Publication router
app.include_router(publications_router, prefix=settings.API_V1_STR)

# Phase 10 Student Portal router
app.include_router(student_router, prefix=settings.API_V1_STR)

# Phase 11 Communication & Outbox router
app.include_router(communication_router, prefix=f"{settings.API_V1_STR}/communication", tags=["communication"])

# Phase 12 Feedback & Contact router
app.include_router(feedback_router, prefix=f"{settings.API_V1_STR}/feedback", tags=["feedback"])
app.include_router(ai_router, prefix=settings.API_V1_STR)

