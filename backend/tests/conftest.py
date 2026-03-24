"""
Global test configuration.

Strategy
--------
`app/database.py` calls `create_engine(settings.DATABASE_URL, pool_size=10, ...)` at
module-load time.  Those pool kwargs are incompatible with SQLite's
SingletonThreadPool.  To avoid patching the source, we intercept
`sqlalchemy.create_engine` *before* `app.database` is imported so the module
ends up using our in-memory SQLite engine instead.
"""
import os

# ── MUST come before every app import ────────────────────────────────────────
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-purposes-32chars!"
os.environ["ENCRYPTION_KEY"] = "test-encryption-key-for-testing-only-1234567"
os.environ["DEBUG"] = "True"
# ─────────────────────────────────────────────────────────────────────────────

import pytest
import sqlalchemy as _sa
from sqlalchemy import create_engine as _real_create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# ── Build the real test engine ───────────────────────────────────────────────
test_engine = _real_create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# ── Patch sqlalchemy.create_engine so app.database picks up test_engine ──────
# When database.py does `from sqlalchemy import create_engine` it reads the
# attribute from the already-imported sqlalchemy module – which is now our stub.
_sa.create_engine = lambda *a, **kw: test_engine

# ── Import app.database (triggers module-level create_engine call) ────────────
import app.database as _db  # noqa: E402

# Restore so nothing else is affected
_sa.create_engine = _real_create_engine

# ── SessionLocal in app.database is now bound to test_engine ─────────────────
# (the stub returned test_engine, so SessionLocal = sessionmaker(bind=test_engine))
# We also expose TestingSessionLocal for fixtures that want a direct session.

# ── Now import the app (triggers model registration with Base.metadata) ───────
from app.main import app  # noqa: E402
from app.database import Base, get_db  # noqa: E402

# Create all tables once (init_db also calls this during lifespan, which is fine)
Base.metadata.create_all(bind=test_engine)


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_tables():
    """Drop and recreate every table before each test for full isolation."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield


@pytest.fixture
def db_session():
    """Raw SQLAlchemy session for unit/service tests that need DB access."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    """FastAPI TestClient backed by the in-memory test database."""

    def _override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "TestPass123!",
        "full_name": "Test User",
    }


@pytest.fixture
def registered_user(client, test_user_data):
    resp = client.post("/api/v1/auth/register", json=test_user_data)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture
def auth_token(client, test_user_data, registered_user):
    resp = client.post(
        "/api/v1/auth/login",
        params={"email": test_user_data["email"], "password": test_user_data["password"]},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture
def refresh_token_value(client, test_user_data, registered_user):
    resp = client.post(
        "/api/v1/auth/login",
        params={"email": test_user_data["email"], "password": test_user_data["password"]},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["refresh_token"]
