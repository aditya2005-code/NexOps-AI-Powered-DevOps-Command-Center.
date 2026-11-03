import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

import app.models  # Ensure all models are registered
from app.main import app as fastapi_app
from app.db.base import Base
from app.db.dependencies import get_db


@pytest.fixture
def client() -> TestClient:
    """Fixture providing a synchronous FastAPI TestClient."""
    with TestClient(fastapi_app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def db_engine():
    """Create a persistent in-memory SQLite engine for the test suite with foreign key checks."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()

    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    """Provide a clean transactional database session per test."""
    Base.metadata.create_all(bind=db_engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db_engine,
        expire_on_commit=False,
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=db_engine)


@pytest.fixture
def client_with_db(db_session: Session) -> Generator[TestClient, None, None]:
    """Provide a TestClient with get_db overridden to use the isolated test db_session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()
