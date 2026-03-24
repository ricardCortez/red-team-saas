"""Integration tests – database operations"""
import pytest
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.core.security import PasswordHandler


class TestDatabaseConnection:
    def test_session_is_usable(self, db_session):
        # Simple query to verify session works
        result = db_session.execute(
            __import__("sqlalchemy").text("SELECT 1")
        ).scalar()
        assert result == 1

    def test_tables_exist(self, db_session):
        from sqlalchemy import inspect
        from app.database import Base
        inspector = inspect(db_session.bind)
        tables = inspector.get_table_names()
        assert "users" in tables

    def test_all_expected_tables_present(self, db_session):
        from sqlalchemy import inspect
        inspector = inspect(db_session.bind)
        tables = set(inspector.get_table_names())
        expected = {
            "users", "tasks", "results", "audit_logs",
            "brute_force_configs", "brute_force_results",
            "generic_tool_configs", "tool_executions",
            "plugins", "plugin_executions",
        }
        missing = expected - tables
        assert not missing, f"Missing tables: {missing}"


class TestCRUDOperations:
    def test_create_and_read_user(self, db_session):
        user = User(
            email="crud@example.com",
            username="cruduser",
            hashed_password=PasswordHandler.hash_password("pass"),
        )
        db_session.add(user)
        db_session.commit()

        found = db_session.query(User).filter(User.email == "crud@example.com").first()
        assert found is not None
        assert found.username == "cruduser"

    def test_update_user(self, db_session):
        user = User(email="upd@example.com", username="upduser", hashed_password="h")
        db_session.add(user)
        db_session.commit()

        user.full_name = "Updated Name"
        db_session.commit()
        db_session.refresh(user)
        assert user.full_name == "Updated Name"

    def test_delete_user(self, db_session):
        user = User(email="del@example.com", username="deluser", hashed_password="h")
        db_session.add(user)
        db_session.commit()

        db_session.delete(user)
        db_session.commit()

        found = db_session.query(User).filter(User.email == "del@example.com").first()
        assert found is None

    def test_query_returns_all_users(self, db_session):
        for i in range(3):
            db_session.add(
                User(email=f"u{i}@example.com", username=f"user{i}", hashed_password="h")
            )
        db_session.commit()
        assert db_session.query(User).count() == 3


class TestTransactions:
    def test_rollback_on_error(self, db_session):
        user = User(email="rollback@example.com", username="rollbackuser", hashed_password="h")
        db_session.add(user)
        db_session.flush()  # push to DB without committing

        db_session.rollback()

        found = db_session.query(User).filter(User.email == "rollback@example.com").first()
        assert found is None

    def test_unique_constraint_triggers_rollback(self, db_session):
        u1 = User(email="dup2@example.com", username="dupuser2a", hashed_password="h")
        db_session.add(u1)
        db_session.commit()

        u2 = User(email="dup2@example.com", username="dupuser2b", hashed_password="h")
        db_session.add(u2)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

        # Confirm only original record exists
        count = db_session.query(User).filter(User.email == "dup2@example.com").count()
        assert count == 1
