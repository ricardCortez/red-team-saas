import pytest
from app.database import SessionLocal

@pytest.fixture
def session():
    session = SessionLocal()
    yield session
    session.close()
