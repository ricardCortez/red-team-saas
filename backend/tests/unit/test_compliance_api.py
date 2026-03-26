"""Unit tests for Compliance API endpoints - Phase 13"""
import pytest
from unittest.mock import patch, MagicMock
from app.models.compliance import (
    ComplianceFramework,
    ComplianceFrameworkType,
    ComplianceMappingResult,
    ComplianceStatus,
    ComplianceEvidenceLog,
    EvidenceStatus,
)
from app.schemas.compliance import ComplianceFrameworkCreate


# ── Helpers ───────────────────────────────────────────────────────────────────

def _register_and_login(client, email, username, password="Pass123!"):
    client.post("/api/v1/auth/register", json={
        "email": email, "username": username, "password": password, "full_name": "Test"
    })
    resp = client.post(
        "/api/v1/auth/login",
        params={"email": email, "password": password},
    )
    return resp.json()["access_token"]


def _make_admin(client, db_session, email="admin13@test.com", username="admin13"):
    token = _register_and_login(client, email, username)
    from app.database import SessionLocal
    from app.models.user import User, UserRoleEnum
    db = db_session
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.is_superuser = True
        user.role = UserRoleEnum.admin
        db.commit()
    return token


def _create_framework(db_session, fw_type=ComplianceFrameworkType.PCI_DSS_3_2_1):
    fw = ComplianceFramework(
        name=f"Framework {fw_type}",
        framework_type=fw_type,
        version="1.0",
        description="Test",
        total_requirements=3,
    )
    db_session.add(fw)
    db_session.commit()
    db_session.refresh(fw)
    return fw


def _create_project(db_session, owner_id):
    from app.models.project import Project, ProjectStatus, ProjectScope
    project = Project(
        name="Compliance API Project",
        status=ProjectStatus.active,
        scope=ProjectScope.external,
        owner_id=owner_id,
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


def _get_user_id(db_session, email):
    from app.models.user import User
    user = db_session.query(User).filter(User.email == email).first()
    return user.id if user else None


# ── Framework endpoints ───────────────────────────────────────────────────────

class TestComplianceFrameworkEndpoints:

    def test_list_frameworks_empty(self, client):
        token = _register_and_login(client, "fw_list@test.com", "fwlist")
        resp = client.get(
            "/api/v1/compliance/frameworks",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_frameworks_with_data(self, client, db_session):
        token = _register_and_login(client, "fw_list2@test.com", "fwlist2")
        _create_framework(db_session)

        resp = client.get(
            "/api/v1/compliance/frameworks",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_get_framework_by_type(self, client, db_session):
        token = _register_and_login(client, "fw_get@test.com", "fwget")
        _create_framework(db_session, ComplianceFrameworkType.HIPAA)

        resp = client.get(
            "/api/v1/compliance/frameworks/hipaa",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["framework_type"] == "hipaa"

    def test_get_framework_not_found(self, client):
        token = _register_and_login(client, "fw_nf@test.com", "fwnf")
        resp = client.get(
            "/api/v1/compliance/frameworks/nonexistent",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    def test_create_framework_admin_only(self, client, db_session):
        token = _make_admin(client, db_session, "admin_fw@test.com", "adminfwtest")
        resp = client.post(
            "/api/v1/compliance/frameworks",
            json={"name": "SOC2 Test", "framework_type": "soc2",
                  "version": "2017", "total_requirements": 5},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        assert resp.json()["framework_type"] == "soc2"

    def test_create_framework_rejects_non_admin(self, client):
        token = _register_and_login(client, "nonadmin_fw@test.com", "nonadminfwtest")
        resp = client.post(
            "/api/v1/compliance/frameworks",
            json={"name": "Test", "framework_type": "iso27001", "version": "2013", "total_requirements": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


# ── Assessment endpoints ──────────────────────────────────────────────────────

class TestComplianceAssessmentEndpoints:

    def test_assess_project_success(self, client, db_session):
        token = _register_and_login(client, "assess1@test.com", "assess1")
        user_id = _get_user_id(db_session, "assess1@test.com")
        project = _create_project(db_session, user_id)
        _create_framework(db_session, ComplianceFrameworkType.GDPR)

        from app.seeds.compliance_frameworks import seed_compliance_frameworks
        seed_compliance_frameworks(db_session)

        resp = client.post(
            f"/api/v1/compliance/assess/{project.id}",
            json={"framework_type": "gdpr"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "compliance_score" in data
        assert 0 <= data["compliance_score"] <= 100

    def test_assess_project_unknown_framework(self, client, db_session):
        token = _register_and_login(client, "assess2@test.com", "assess2")
        user_id = _get_user_id(db_session, "assess2@test.com")
        project = _create_project(db_session, user_id)

        resp = client.post(
            f"/api/v1/compliance/assess/{project.id}",
            json={"framework_type": "unknown_fw"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    def test_assess_project_forbidden_other_user(self, client, db_session):
        owner_token = _register_and_login(client, "owner_a@test.com", "ownera")
        other_token = _register_and_login(client, "other_a@test.com", "othera")
        owner_id = _get_user_id(db_session, "owner_a@test.com")
        project = _create_project(db_session, owner_id)

        resp = client.post(
            f"/api/v1/compliance/assess/{project.id}",
            json={"framework_type": "pci_dss_3.2.1"},
            headers={"Authorization": f"Bearer {other_token}"},
        )
        assert resp.status_code == 403

    def test_assess_project_not_found(self, client):
        token = _register_and_login(client, "assess_nf@test.com", "assessnf")
        resp = client.post(
            "/api/v1/compliance/assess/99999",
            json={"framework_type": "hipaa"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    def test_get_project_assessments(self, client, db_session):
        token = _register_and_login(client, "hist1@test.com", "hist1")
        user_id = _get_user_id(db_session, "hist1@test.com")
        project = _create_project(db_session, user_id)
        fw = _create_framework(db_session, ComplianceFrameworkType.SOC2)

        # Insert a mapping result directly
        mapping = ComplianceMappingResult(
            project_id=project.id,
            framework_id=fw.id,
            total_requirements=3,
            met_requirements=2,
            compliance_score=67,
            compliance_status=ComplianceStatus.PARTIAL,
            audit_findings=[],
        )
        db_session.add(mapping)
        db_session.commit()

        resp = client.get(
            f"/api/v1/compliance/assessments/{project.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_get_mapping_by_id(self, client, db_session):
        token = _register_and_login(client, "map_get@test.com", "mapget")
        user_id = _get_user_id(db_session, "map_get@test.com")
        project = _create_project(db_session, user_id)
        fw = _create_framework(db_session, ComplianceFrameworkType.ISO27001)

        mapping = ComplianceMappingResult(
            project_id=project.id,
            framework_id=fw.id,
            total_requirements=1,
            met_requirements=1,
            compliance_score=100,
            compliance_status=ComplianceStatus.COMPLIANT,
            audit_findings=[],
        )
        db_session.add(mapping)
        db_session.commit()

        resp = client.get(
            f"/api/v1/compliance/mapping/{mapping.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == mapping.id

    def test_async_assess_endpoint(self, client, db_session):
        token = _register_and_login(client, "async1@test.com", "async1")
        user_id = _get_user_id(db_session, "async1@test.com")
        project = _create_project(db_session, user_id)

        mock_job = MagicMock()
        mock_job.id = "task-async-123"

        with patch("app.tasks.compliance_tasks.assess_project_compliance_task.apply_async",
                   return_value=mock_job):
            resp = client.post(
                f"/api/v1/compliance/assess/{project.id}/async",
                json={"framework_type": "gdpr"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 202
        assert resp.json()["status"] == "queued"


# ── Evidence endpoints ────────────────────────────────────────────────────────

class TestComplianceEvidenceEndpoints:

    def _setup(self, client, db_session, email, username):
        token = _register_and_login(client, email, username)
        user_id = _get_user_id(db_session, email)
        project = _create_project(db_session, user_id)
        fw = _create_framework(db_session, ComplianceFrameworkType.PCI_DSS_4_0)
        mapping = ComplianceMappingResult(
            project_id=project.id,
            framework_id=fw.id,
            total_requirements=1,
            met_requirements=1,
            compliance_score=100,
            compliance_status=ComplianceStatus.COMPLIANT,
            audit_findings=[],
        )
        db_session.add(mapping)
        db_session.commit()
        db_session.refresh(mapping)
        return token, project, mapping

    def test_get_evidence_empty(self, client, db_session):
        token, _, mapping = self._setup(client, db_session, "ev1@test.com", "ev1")
        resp = client.get(
            f"/api/v1/compliance/evidence/{mapping.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_update_evidence_status_admin(self, client, db_session):
        _, _, mapping = self._setup(client, db_session, "ev_owner@test.com", "evowner")
        admin_token = _make_admin(client, db_session, "ev_admin@test.com", "evadmin")

        log = ComplianceEvidenceLog(
            mapping_result_id=mapping.id,
            requirement_id="1.1",
            status=EvidenceStatus.NON_MET,
        )
        db_session.add(log)
        db_session.commit()

        resp = client.patch(
            f"/api/v1/compliance/evidence/{log.id}/status"
            "?status=MET&notes=Remediated",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "MET"

    def test_update_evidence_status_non_admin_rejected(self, client, db_session):
        token, _, mapping = self._setup(client, db_session, "ev_reg@test.com", "evreg")

        log = ComplianceEvidenceLog(
            mapping_result_id=mapping.id,
            requirement_id="1.1",
            status=EvidenceStatus.NON_MET,
        )
        db_session.add(log)
        db_session.commit()

        resp = client.patch(
            f"/api/v1/compliance/evidence/{log.id}/status?status=MET",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


# ── Control matrix endpoints ──────────────────────────────────────────────────

class TestComplianceControlEndpoints:

    def test_get_controls_empty(self, client, db_session):
        token = _register_and_login(client, "ctrl1@test.com", "ctrl1")
        user_id = _get_user_id(db_session, "ctrl1@test.com")
        project = _create_project(db_session, user_id)

        resp = client.get(
            f"/api/v1/compliance/controls/{project.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_control(self, client, db_session):
        token = _register_and_login(client, "ctrl2@test.com", "ctrl2")
        user_id = _get_user_id(db_session, "ctrl2@test.com")
        project = _create_project(db_session, user_id)
        _create_framework(db_session, ComplianceFrameworkType.HIPAA)

        resp = client.post(
            f"/api/v1/compliance/controls/{project.id}"
            "?framework_type=hipaa",
            json={"requirement_id": "164.312(a)(1)", "control_description": "MFA enabled",
                  "control_owner": "CISO", "implementation_status": "IMPLEMENTED"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        assert resp.json()["requirement_id"] == "164.312(a)(1)"

    def test_add_control_test_result_admin(self, client, db_session):
        admin_token = _make_admin(client, db_session, "ctrl_admin@test.com", "ctrladmin")
        user_id = _get_user_id(db_session, "ctrl_admin@test.com")
        project = _create_project(db_session, user_id)
        fw = _create_framework(db_session, ComplianceFrameworkType.GDPR)

        from app.crud.compliance import ComplianceCRUD
        from app.schemas.compliance import ComplianceControlCreate
        ctrl = ComplianceCRUD.create_control(
            db_session, project.id, fw.id,
            ComplianceControlCreate(requirement_id="32"),
        )

        resp = client.patch(
            f"/api/v1/compliance/controls/{ctrl.id}/test-result"
            "?result=PASS&notes=All+good",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["test_results"]) == 1


# ── Report & Seed endpoints ───────────────────────────────────────────────────

class TestComplianceMiscEndpoints:

    def test_get_compliance_report(self, client, db_session):
        token = _register_and_login(client, "report1@test.com", "report1")
        user_id = _get_user_id(db_session, "report1@test.com")
        project = _create_project(db_session, user_id)
        fw = _create_framework(db_session, ComplianceFrameworkType.SOC2)

        mapping = ComplianceMappingResult(
            project_id=project.id,
            framework_id=fw.id,
            total_requirements=1,
            met_requirements=1,
            compliance_score=100,
            compliance_status=ComplianceStatus.COMPLIANT,
            audit_findings=[],
        )
        db_session.add(mapping)
        db_session.commit()

        resp = client.get(
            f"/api/v1/compliance/report/{mapping.id}?format=json",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["report_id"] == mapping.id
        assert data["score"] == 100

    def test_seed_endpoint_admin_only(self, client, db_session):
        admin_token = _make_admin(client, db_session, "seed_admin@test.com", "seadadmin")
        resp = client.post(
            "/api/v1/compliance/seed",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201
        assert "created" in resp.json()

    def test_seed_endpoint_non_admin_rejected(self, client):
        token = _register_and_login(client, "seed_reg@test.com", "seedreg")
        resp = client.post(
            "/api/v1/compliance/seed",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
