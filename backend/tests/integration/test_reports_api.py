"""Integration tests for Phase 6 Report API endpoints"""
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock

from app.models.report import Report, ReportType, ReportFormat, ReportStatus, ReportClassification
from app.models.user import User, UserRoleEnum
from app.models.project import Project


# ── helpers ────────────────────────────────────────────────────────────────────

def _register_and_login(client, email="r@test.com", username="reporter",
                        password="Test123!", role=UserRoleEnum.pentester):
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "username": username, "password": password, "full_name": "R"},
    )
    resp = client.post(
        "/api/v1/auth/login",
        params={"email": email, "password": password},
    )
    return resp.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _create_project(db_session, owner_id: int) -> Project:
    project = Project(
        owner_id=owner_id,
        name="Test Project",
        target="10.0.0.0/24",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


def _create_report(db_session, project_id: int, user_id: int,
                   status=ReportStatus.pending) -> Report:
    r = Report(
        project_id=project_id,
        created_by=user_id,
        title="My Report",
        report_type=ReportType.technical,
        report_format=ReportFormat.html,
        classification=ReportClassification.confidential,
        status=status,
    )
    db_session.add(r)
    db_session.commit()
    db_session.refresh(r)
    return r


# ── POST /api/v1/reports/ ──────────────────────────────────────────────────────

class TestCreateReport:

    def test_create_report_enqueues_task(self, client, db_session):
        token = _register_and_login(client)
        user = db_session.query(User).filter(User.email == "r@test.com").first()
        project = _create_project(db_session, user.id)

        with patch("app.api.v1.endpoints.reports.generate_report") as mock_task:
            mock_job = MagicMock()
            mock_job.id = "celery-task-123"
            mock_task.apply_async.return_value = mock_job

            resp = client.post(
                "/api/v1/reports/",
                json={
                    "project_id": project.id,
                    "title": "Pentest Q1 2026",
                    "report_type": "technical",
                    "report_format": "html",
                },
                headers=_auth(token),
            )

        assert resp.status_code == 202
        data = resp.json()
        assert data["title"] == "Pentest Q1 2026"
        assert data["status"] == "pending"
        mock_task.apply_async.assert_called_once()

    def test_viewer_cannot_create_report(self, client, db_session):
        # Register a viewer user
        client.post(
            "/api/v1/auth/register",
            json={"email": "viewer@test.com", "username": "viewer1",
                  "password": "Test123!", "full_name": "V"},
        )
        # Downgrade role to viewer in DB
        viewer = db_session.query(User).filter(User.email == "viewer@test.com").first()
        viewer.role = UserRoleEnum.viewer
        db_session.commit()

        resp_login = client.post(
            "/api/v1/auth/login",
            params={"email": "viewer@test.com", "password": "Test123!"},
        )
        token = resp_login.json()["access_token"]

        resp = client.post(
            "/api/v1/reports/",
            json={"project_id": 1, "title": "X", "report_type": "technical"},
            headers=_auth(token),
        )
        assert resp.status_code == 403

    def test_create_report_with_all_fields(self, client, db_session):
        token = _register_and_login(client, email="full@test.com", username="full_user")
        user = db_session.query(User).filter(User.email == "full@test.com").first()
        project = _create_project(db_session, user.id)

        with patch("app.api.v1.endpoints.reports.generate_report") as mock_task:
            mock_task.apply_async.return_value = MagicMock(id="x")
            resp = client.post(
                "/api/v1/reports/",
                json={
                    "project_id": project.id,
                    "title": "Full Report",
                    "report_type": "executive",
                    "report_format": "pdf",
                    "classification": "restricted",
                    "scope_description": "External IPs only",
                    "executive_summary": "Critical findings found",
                    "recommendations": "Patch immediately",
                },
                headers=_auth(token),
            )

        assert resp.status_code == 202
        data = resp.json()
        assert data["classification"] == "restricted"
        assert data["report_type"] == "executive"


# ── GET /api/v1/reports/ ───────────────────────────────────────────────────────

class TestListReports:

    def test_list_reports_paginated(self, client, db_session):
        token = _register_and_login(client, email="list@test.com", username="list_user")
        user = db_session.query(User).filter(User.email == "list@test.com").first()
        project = _create_project(db_session, user.id)

        for i in range(5):
            _create_report(db_session, project.id, user.id)

        resp = client.get("/api/v1/reports/?limit=3", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 3

    def test_list_reports_filter_by_status(self, client, db_session):
        token = _register_and_login(client, email="filt@test.com", username="filt_user")
        user = db_session.query(User).filter(User.email == "filt@test.com").first()
        project = _create_project(db_session, user.id)

        _create_report(db_session, project.id, user.id, status=ReportStatus.ready)
        _create_report(db_session, project.id, user.id, status=ReportStatus.pending)

        resp = client.get("/api/v1/reports/?status=ready", headers=_auth(token))
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(i["status"] == "ready" for i in items)

    def test_list_reports_only_own(self, client, db_session):
        """Users should only see their own reports."""
        t1 = _register_and_login(client, email="own1@test.com", username="own1")
        t2 = _register_and_login(client, email="own2@test.com", username="own2")
        u1 = db_session.query(User).filter(User.email == "own1@test.com").first()
        u2 = db_session.query(User).filter(User.email == "own2@test.com").first()
        p1 = _create_project(db_session, u1.id)
        p2 = _create_project(db_session, u2.id)
        _create_report(db_session, p1.id, u1.id)
        _create_report(db_session, p2.id, u2.id)

        resp1 = client.get("/api/v1/reports/", headers=_auth(t1))
        resp2 = client.get("/api/v1/reports/", headers=_auth(t2))
        assert resp1.json()["total"] == 1
        assert resp2.json()["total"] == 1


# ── GET /api/v1/reports/{id} ───────────────────────────────────────────────────

class TestGetReport:

    def test_get_report_detail(self, client, db_session):
        token = _register_and_login(client, email="get@test.com", username="get_user")
        user = db_session.query(User).filter(User.email == "get@test.com").first()
        project = _create_project(db_session, user.id)
        report = _create_report(db_session, project.id, user.id)

        resp = client.get(f"/api/v1/reports/{report.id}", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["id"] == report.id

    def test_get_report_not_found(self, client):
        token = _register_and_login(client, email="nf@test.com", username="nf_user")
        resp = client.get("/api/v1/reports/99999", headers=_auth(token))
        assert resp.status_code == 404

    def test_get_report_forbidden_other_user(self, client, db_session):
        t1 = _register_and_login(client, email="fo1@test.com", username="fo1")
        t2 = _register_and_login(client, email="fo2@test.com", username="fo2")
        u1 = db_session.query(User).filter(User.email == "fo1@test.com").first()
        project = _create_project(db_session, u1.id)
        report = _create_report(db_session, project.id, u1.id)

        resp = client.get(f"/api/v1/reports/{report.id}", headers=_auth(t2))
        assert resp.status_code == 403


# ── GET /api/v1/reports/{id}/download ─────────────────────────────────────────

class TestDownloadReport:

    def test_download_report_ready(self, client, db_session, tmp_path):
        token = _register_and_login(client, email="dl@test.com", username="dl_user")
        user = db_session.query(User).filter(User.email == "dl@test.com").first()
        project = _create_project(db_session, user.id)
        report = _create_report(db_session, project.id, user.id, status=ReportStatus.ready)

        # Create a real temp file
        report_file = tmp_path / "report_1_technical.html"
        report_file.write_bytes(b"<html>content</html>")
        report.file_path = str(report_file)
        report.report_format = ReportFormat.html
        db_session.commit()

        resp = client.get(f"/api/v1/reports/{report.id}/download", headers=_auth(token))
        assert resp.status_code == 200
        assert b"<html>" in resp.content

    def test_download_report_not_ready_fails(self, client, db_session):
        token = _register_and_login(client, email="nr@test.com", username="nr_user")
        user = db_session.query(User).filter(User.email == "nr@test.com").first()
        project = _create_project(db_session, user.id)
        report = _create_report(db_session, project.id, user.id, status=ReportStatus.pending)

        resp = client.get(f"/api/v1/reports/{report.id}/download", headers=_auth(token))
        assert resp.status_code == 400
        assert "not ready" in resp.json()["detail"].lower()

    def test_download_report_audit_log_created(self, client, db_session, tmp_path):
        token = _register_and_login(client, email="al@test.com", username="al_user")
        user = db_session.query(User).filter(User.email == "al@test.com").first()
        project = _create_project(db_session, user.id)
        report = _create_report(db_session, project.id, user.id, status=ReportStatus.ready)

        report_file = tmp_path / "report_1.html"
        report_file.write_bytes(b"<html>audit</html>")
        report.file_path = str(report_file)
        report.report_format = ReportFormat.html
        db_session.commit()

        from app.models.audit_log import AuditLog
        before = db_session.query(AuditLog).count()
        client.get(f"/api/v1/reports/{report.id}/download", headers=_auth(token))
        after = db_session.query(AuditLog).count()
        assert after > before


# ── DELETE /api/v1/reports/{id} ───────────────────────────────────────────────

class TestDeleteReport:

    def test_delete_report_removes_db_row(self, client, db_session):
        token = _register_and_login(client, email="del@test.com", username="del_user")
        user = db_session.query(User).filter(User.email == "del@test.com").first()
        project = _create_project(db_session, user.id)
        report = _create_report(db_session, project.id, user.id)

        resp = client.delete(f"/api/v1/reports/{report.id}", headers=_auth(token))
        assert resp.status_code == 204

        gone = db_session.query(Report).filter(Report.id == report.id).first()
        assert gone is None

    def test_delete_report_removes_file(self, client, db_session, tmp_path):
        token = _register_and_login(client, email="delf@test.com", username="delf_user")
        user = db_session.query(User).filter(User.email == "delf@test.com").first()
        project = _create_project(db_session, user.id)
        report = _create_report(db_session, project.id, user.id, status=ReportStatus.ready)

        report_file = tmp_path / "to_delete.html"
        report_file.write_bytes(b"<html></html>")
        report.file_path = str(report_file)
        db_session.commit()

        assert report_file.exists()
        client.delete(f"/api/v1/reports/{report.id}", headers=_auth(token))
        assert not report_file.exists()

    def test_delete_report_forbidden_other_user(self, client, db_session):
        t1 = _register_and_login(client, email="df1@test.com", username="df1")
        t2 = _register_and_login(client, email="df2@test.com", username="df2")
        u1 = db_session.query(User).filter(User.email == "df1@test.com").first()
        project = _create_project(db_session, u1.id)
        report = _create_report(db_session, project.id, u1.id)

        resp = client.delete(f"/api/v1/reports/{report.id}", headers=_auth(t2))
        assert resp.status_code == 403
