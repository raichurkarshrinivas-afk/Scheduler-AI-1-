import os
import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.main import app
from app.models import (
    Institution,
    User,
    Membership,
    UserRole,
    Department,
    AcademicTerm,
    Subject,
    SubjectType,
    CourseOffering,
    Section,
    Enrolment,
    EnrolmentStatus,
    Teacher,
    Student,
    TeacherQualification,
    Building,
    Room,
    RoomType,
    Seat,
    Workstation,
    Session,
    SessionType,
    SessionStatus,
    AvailabilityRule,
    TargetType,
    CalendarException,
    CalendarExceptionType,
    ConstraintRule,
    ConstraintType,
    AuditEvent,
)

# In-memory SQLite for testing with StaticPool and Foreign Keys enabled
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(test_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()