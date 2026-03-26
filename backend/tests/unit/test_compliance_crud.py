"""Unit tests for Compliance CRUD - Phase 13"""
import pytest
from app.crud.compliance import ComplianceCRUD
from app.models.compliance import (
    ComplianceFramework,
    ComplianceRequirement,
    ComplianceMappingResult,
    ComplianceEvidenceLog,
    ComplianceControlMatrix,
    ComplianceFrameworkType,
    ComplianceStatus,
    EvidenceStatus,
    ControlImplementationStatus,
)
from app.schemas.compliance import (
    ComplianceFrameworkCreate,
    ComplianceEvidenceCreate,
    ComplianceControlCreate,
)


def _project_and_owner(db):
    from app.models.user import User
    from app.models.project import Project, ProjectStatus, ProjectScope
    from app.core.security import PasswordHandler

    owner = User(
        email="crud_owner@test.com",
        username="crudowner",
        hashed_password=PasswordHandler.hash_password("Pass123!"),
        is_active=True,
    )
    db.add(owner)
    db.commit()

    project = Project(
        name="CRUD Test Project",
        status=ProjectStatus.active,
        scope=ProjectScope.external,
        owner_id=owner.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project, owner


def _make_framework(db, fw_type=ComplianceFrameworkType.PCI_DSS_3_2_1, name=None):
    schema = ComplianceFrameworkCreate(
        name=name or f"Framework {fw_type}",
        framework_type=fw_type,
        version="1.0",
        description="Test",
        total_requirements=3,
    )
    return ComplianceCRUD.create_framework(db, schema)


class TestFrameworkCRUD:

    def test_create_and_get_framework(self, db_session):
        fw = _make_framework(db_session)
        assert fw.id is not None

        retrieved = ComplianceCRUD.get_framework_by_type(db_session, "pci_dss_3.2.1")
        assert retrieved is not None
        assert retrieved.id == fw.id

    def test_get_framework_by_type_not_found(self, db_session):
        result = ComplianceCRUD.get_framework_by_type(db_session, "nonexistent")
        assert result is None

    def test_get_framework_by_id(self, db_session):
        fw = _make_framework(db_session)
        retrieved = ComplianceCRUD.get_framework_by_id(db_session, fw.id)
        assert retrieved is not None
        assert retrieved.id == fw.id

    def test_list_frameworks(self, db_session):
        _make_framework(db_session, ComplianceFrameworkType.PCI_DSS_3_2_1, "PCI")
        _make_framework(db_session, ComplianceFrameworkType.HIPAA, "HIPAA")
        frameworks = ComplianceCRUD.list_frameworks(db_session)
        assert len(frameworks) >= 2

    def test_list_frameworks_pagination(self, db_session):
        _make_framework(db_session, ComplianceFrameworkType.GDPR, "GDPR")
        page = ComplianceCRUD.list_frameworks(db_session, skip=0, limit=1)
        assert len(page) == 1


class TestRequirementCRUD:

    def test_get_requirements_by_framework(self, db_session):
        fw = _make_framework(db_session)
        for i in range(3):
            req = ComplianceRequirement(
                framework_id=fw.id,
                requirement_id=f"{i+1}.1",
                requirement_text=f"Req {i+1}",
            )
            db_session.add(req)
        db_session.commit()

        reqs = ComplianceCRUD.get_requirements_by_framework(db_session, fw.id)
        assert len(reqs) == 3

    def test_get_requirements_empty(self, db_session):
        fw = _make_framework(db_session)
        reqs = ComplianceCRUD.get_requirements_by_framework(db_session, fw.id)
        assert reqs == []


class TestMappingResultCRUD:

    def test_create_and_get_mapping_result(self, db_session):
        project, _ = _project_and_owner(db_session)
        fw = _make_framework(db_session)

        obj = ComplianceMappingResult(
            project_id=project.id,
            framework_id=fw.id,
            total_requirements=5,
            met_requirements=4,
            compliance_score=80,
            compliance_status=ComplianceStatus.COMPLIANT,
            audit_findings=[],
        )
        result = ComplianceCRUD.create_mapping_result(db_session, obj)
        assert result.id is not None

        retrieved = ComplianceCRUD.get_mapping_by_id(db_session, result.id)
        assert retrieved.compliance_score == 80

    def test_get_mapping_by_project_framework(self, db_session):
        project, _ = _project_and_owner(db_session)
        fw = _make_framework(db_session)

        obj = ComplianceMappingResult(
            project_id=project.id,
            framework_id=fw.id,
            total_requirements=3,
            met_requirements=2,
            compliance_score=67,
            compliance_status=ComplianceStatus.PARTIAL,
            audit_findings=[],
        )
        db_session.add(obj)
        db_session.commit()

        latest = ComplianceCRUD.get_mapping_by_project_framework(db_session, project.id, fw.id)
        assert latest is not None
        assert latest.project_id == project.id

    def test_get_latest_mappings(self, db_session):
        project, _ = _project_and_owner(db_session)
        fw = _make_framework(db_session)

        for _ in range(3):
            obj = ComplianceMappingResult(
                project_id=project.id,
                framework_id=fw.id,
                total_requirements=1,
                met_requirements=1,
                compliance_score=100,
                compliance_status=ComplianceStatus.COMPLIANT,
                audit_findings=[],
            )
            db_session.add(obj)
        db_session.commit()

        mappings = ComplianceCRUD.get_latest_mappings(db_session, project.id, limit=2)
        assert len(mappings) == 2


class TestEvidenceCRUD:

    def _make_mapping(self, db):
        project, _ = _project_and_owner(db)
        fw = _make_framework(db, ComplianceFrameworkType.SOC2, "SOC2")
        obj = ComplianceMappingResult(
            project_id=project.id,
            framework_id=fw.id,
            total_requirements=1,
            met_requirements=1,
            compliance_score=100,
            compliance_status=ComplianceStatus.COMPLIANT,
            audit_findings=[],
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def test_create_evidence_log(self, db_session):
        mapping = self._make_mapping(db_session)
        schema = ComplianceEvidenceCreate(
            mapping_result_id=mapping.id,
            requirement_id="1.1",
            status="MET",
            evidence_text="Control verified",
        )
        log = ComplianceCRUD.create_evidence_log(db_session, schema)
        assert log.id is not None

    def test_get_evidence_by_mapping(self, db_session):
        mapping = self._make_mapping(db_session)
        for req_id in ["1.1", "2.1", "3.1"]:
            schema = ComplianceEvidenceCreate(
                mapping_result_id=mapping.id,
                requirement_id=req_id,
                status="NOT_APPLICABLE",
            )
            ComplianceCRUD.create_evidence_log(db_session, schema)

        logs = ComplianceCRUD.get_evidence_by_mapping(db_session, mapping.id)
        assert len(logs) == 3

    def test_update_evidence_status(self, db_session):
        mapping = self._make_mapping(db_session)
        schema = ComplianceEvidenceCreate(
            mapping_result_id=mapping.id,
            requirement_id="1.1",
            status="NON_MET",
        )
        log = ComplianceCRUD.create_evidence_log(db_session, schema)

        updated = ComplianceCRUD.update_evidence_status(
            db_session, log.id, "MET", notes="Remediated"
        )
        assert updated.status == EvidenceStatus.MET
        assert updated.reviewer_notes == "Remediated"
        assert updated.reviewed_at is not None


class TestControlMatrixCRUD:

    def test_create_and_get_control(self, db_session):
        project, _ = _project_and_owner(db_session)
        fw = _make_framework(db_session, ComplianceFrameworkType.ISO27001, "ISO27001")

        ctrl = ComplianceCRUD.create_control(
            db_session,
            project.id,
            fw.id,
            ComplianceControlCreate(
                requirement_id="A.9.1",
                control_description="Access policy",
                control_owner="CISO",
                implementation_status="IMPLEMENTED",
            ),
        )
        assert ctrl.id is not None
        assert ctrl.implementation_status == ControlImplementationStatus.IMPLEMENTED

    def test_get_controls_by_project(self, db_session):
        project, _ = _project_and_owner(db_session)
        fw = _make_framework(db_session, ComplianceFrameworkType.PCI_DSS_4_0, "PCI 4.0")

        for req_id in ["1.1", "2.1"]:
            ComplianceCRUD.create_control(
                db_session, project.id, fw.id,
                ComplianceControlCreate(requirement_id=req_id),
            )

        controls = ComplianceCRUD.get_controls_by_project(db_session, project.id)
        assert len(controls) == 2

    def test_update_control_test_result(self, db_session):
        project, _ = _project_and_owner(db_session)
        fw = _make_framework(db_session, ComplianceFrameworkType.GDPR, "GDPR Test")

        ctrl = ComplianceCRUD.create_control(
            db_session, project.id, fw.id,
            ComplianceControlCreate(requirement_id="32"),
        )
        updated = ComplianceCRUD.update_control_test_result(
            db_session, ctrl.id, {"result": "PASS", "notes": "All good"}
        )
        assert len(updated.test_results) == 1
        assert updated.test_results[0]["result"] == "PASS"
        assert updated.last_tested is not None

    def test_update_control_not_found(self, db_session):
        result = ComplianceCRUD.update_control_test_result(db_session, 99999, {"result": "PASS"})
        assert result is None
