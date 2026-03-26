"""Unit tests for Compliance Celery tasks - Phase 13"""
import pytest
from unittest.mock import patch, MagicMock
from app.models.compliance import (
    ComplianceFramework,
    ComplianceMappingResult,
    ComplianceFrameworkType,
    ComplianceStatus,
)


def _project_owner(db):
    from app.models.user import User
    from app.models.project import Project, ProjectStatus, ProjectScope
    from app.core.security import PasswordHandler

    owner = User(
        email="task_comp_owner@test.com",
        username="taskcompowner",
        hashed_password=PasswordHandler.hash_password("Pass123!"),
        is_active=True,
    )
    db.add(owner)
    db.commit()

    project = Project(
        name="Task Project",
        status=ProjectStatus.active,
        scope=ProjectScope.external,
        owner_id=owner.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project, owner


class TestAssessProjectComplianceTask:

    def test_task_returns_success(self, db_session):
        project, _ = _project_owner(db_session)

        # Seed the framework first
        from app.seeds.compliance_frameworks import seed_compliance_frameworks
        seed_compliance_frameworks(db_session)

        from app.tasks.compliance_tasks import assess_project_compliance_task

        with patch("app.tasks.compliance_tasks.SessionLocal", return_value=db_session):
            result = assess_project_compliance_task(project.id, "pci_dss_3.2.1")

        assert result["status"] == "success"
        assert "mapping_id" in result
        assert "compliance_score" in result

    def test_task_returns_error_project_not_found(self, db_session):
        from app.tasks.compliance_tasks import assess_project_compliance_task

        with patch("app.tasks.compliance_tasks.SessionLocal", return_value=db_session):
            result = assess_project_compliance_task(99999, "pci_dss_3.2.1")

        assert result["status"] == "error"
        assert "99999" in result["message"]

    def test_task_returns_error_framework_not_found(self, db_session):
        project, _ = _project_owner(db_session)

        from app.tasks.compliance_tasks import assess_project_compliance_task

        with patch("app.tasks.compliance_tasks.SessionLocal", return_value=db_session):
            result = assess_project_compliance_task(project.id, "nonexistent_framework")

        assert result["status"] == "error"

    def test_task_includes_compliance_status(self, db_session):
        project, _ = _project_owner(db_session)
        from app.seeds.compliance_frameworks import seed_compliance_frameworks
        seed_compliance_frameworks(db_session)

        from app.tasks.compliance_tasks import assess_project_compliance_task

        with patch("app.tasks.compliance_tasks.SessionLocal", return_value=db_session):
            result = assess_project_compliance_task(project.id, "hipaa")

        assert result["status"] == "success"
        assert result["compliance_status"] in ("COMPLIANT", "PARTIAL", "NON_COMPLIANT")

    def test_celery_task_registered(self):
        from app.tasks.celery_app import celery_app
        assert "app.tasks.compliance_tasks" in celery_app.conf.include
