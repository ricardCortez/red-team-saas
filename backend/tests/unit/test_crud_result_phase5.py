"""Unit tests for app.crud.exec_result (Phase 5)"""
import pytest
from datetime import datetime, timezone

from app.crud.exec_result import crud_exec_result
from app.models.result import Result
from app.models.task import Task, TaskStatusEnum
from app.models.user import User, UserRoleEnum
from app.schemas.result import ResultFilter
from app.core.security import PasswordHandler


def _create_user(db, email="u@example.com", username="user1") -> User:
    user = User(
        email=email,
        username=username,
        hashed_password=PasswordHandler.hash_password("Pass123!"),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_workspace(db, owner_id: int):
    from app.models.workspace import Workspace
    ws = Workspace(name="Test WS", owner_id=owner_id)
    db.add(ws)
    db.commit()
    db.refresh(ws)
    return ws


def _create_task(db, user_id: int, project_id=None) -> Task:
    task = Task(
        user_id=user_id,
        status=TaskStatusEnum.completed,
        tool_name="nmap",
        target="192.168.1.1",
        project_id=project_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def _create_result(db, task_id: int, **kwargs) -> Result:
    defaults = dict(
        task_id=task_id,
        tool_name="nmap",
        target="192.168.1.1",
        success=True,
        risk_score=5.0,
        exit_code=0,
        duration_seconds=2.0,
        findings=[],
    )
    defaults.update(kwargs)
    r = Result(**defaults)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


class TestGetMultiFiltered:

    def test_filter_by_tool(self, db_session):
        user = _create_user(db_session)
        task1 = _create_task(db_session, user.id)
        task2 = _create_task(db_session, user.id)
        _create_result(db_session, task1.id, tool_name="nmap")
        _create_result(db_session, task2.id, tool_name="nikto")

        filters = ResultFilter(tool_name="nmap")
        items, total = crud_exec_result.get_multi_filtered(
            db_session, user_id=user.id, filters=filters
        )
        assert total == 1
        assert items[0].tool_name == "nmap"

    def test_filter_by_success(self, db_session):
        user = _create_user(db_session)
        task = _create_task(db_session, user.id)
        _create_result(db_session, task.id, success=True)
        _create_result(db_session, task.id, success=False)

        filters = ResultFilter(success=True)
        items, total = crud_exec_result.get_multi_filtered(
            db_session, user_id=user.id, filters=filters
        )
        assert total == 1
        assert items[0].success is True

    def test_filter_by_risk_score(self, db_session):
        user = _create_user(db_session)
        task = _create_task(db_session, user.id)
        _create_result(db_session, task.id, risk_score=2.0)
        _create_result(db_session, task.id, risk_score=9.0)

        filters = ResultFilter(min_risk_score=5.0)
        items, total = crud_exec_result.get_multi_filtered(
            db_session, user_id=user.id, filters=filters
        )
        assert total == 1
        assert items[0].risk_score == 9.0

    def test_filter_by_target(self, db_session):
        user = _create_user(db_session)
        task = _create_task(db_session, user.id)
        _create_result(db_session, task.id, target="192.168.1.1")
        _create_result(db_session, task.id, target="10.0.0.1")

        filters = ResultFilter(target="192.168")
        items, total = crud_exec_result.get_multi_filtered(
            db_session, user_id=user.id, filters=filters
        )
        assert total == 1
        assert "192.168" in items[0].target

    def test_user_isolation(self, db_session):
        user1 = _create_user(db_session, email="u1@x.com", username="u1")
        user2 = _create_user(db_session, email="u2@x.com", username="u2")
        task1 = _create_task(db_session, user1.id)
        task2 = _create_task(db_session, user2.id)
        _create_result(db_session, task1.id)
        _create_result(db_session, task2.id)

        filters = ResultFilter()
        _, total_u1 = crud_exec_result.get_multi_filtered(
            db_session, user_id=user1.id, filters=filters
        )
        assert total_u1 == 1

    def test_superuser_sees_all(self, db_session):
        user1 = _create_user(db_session, email="s1@x.com", username="s1")
        user2 = _create_user(db_session, email="s2@x.com", username="s2")
        task1 = _create_task(db_session, user1.id)
        task2 = _create_task(db_session, user2.id)
        _create_result(db_session, task1.id)
        _create_result(db_session, task2.id)

        filters = ResultFilter()
        _, total = crud_exec_result.get_multi_filtered(
            db_session, user_id=user1.id, filters=filters, is_superuser=True
        )
        assert total == 2


class TestProjectSummary:

    def test_project_summary_counts(self, db_session):
        user = _create_user(db_session)
        task1 = _create_task(db_session, user.id, project_id=99)
        task2 = _create_task(db_session, user.id, project_id=99)
        _create_result(db_session, task1.id, success=True, risk_score=8.0, tool_name="nmap")
        _create_result(db_session, task2.id, success=False, risk_score=4.0, tool_name="nmap")

        summary = crud_exec_result.get_summary_by_project(db_session, project_id=99)
        assert summary["total_scans"] == 2
        assert summary["successful"] == 1
        assert summary["failed"] == 1
        assert summary["avg_risk_score"] == 6.0
        assert "nmap" in summary["tools_used"]

    def test_empty_project_returns_zeros(self, db_session):
        summary = crud_exec_result.get_summary_by_project(db_session, project_id=9999)
        assert summary["total_scans"] == 0
        assert summary["avg_risk_score"] == 0.0
