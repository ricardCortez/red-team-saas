"""Unit tests for Compliance Engine models - Phase 13"""
import pytest
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


def _make_framework(db, fw_type=ComplianceFrameworkType.PCI_DSS_3_2_1):
    fw = ComplianceFramework(
        name=f"Test {fw_type}",
        framework_type=fw_type,
        version="1.0",
        description="Test framework",
        total_requirements=5,
    )
    db.add(fw)
    db.commit()
    db.refresh(fw)
    return fw


def _make_project_with_owner(db):
    from app.models.user import User
    from app.models.project import Project, ProjectStatus, ProjectScope
    from app.core.security import PasswordHandler

    owner = User(
        email="comp_owner@test.com",
        username="compowner",
        hashed_password=PasswordHandler.hash_password("Pass123!"),
        is_active=True,
    )
    db.add(owner)
    db.commit()

    project = Project(
        name="Compliance Test Project",
        description="",
        status=ProjectStatus.active,
        scope=ProjectScope.external,
        owner_id=owner.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project, owner


class TestComplianceFrameworkModel:

    def test_create_framework(self, db_session):
        fw = _make_framework(db_session)
        assert fw.id is not None
        assert fw.framework_type == ComplianceFrameworkType.PCI_DSS_3_2_1
        assert fw.version == "1.0"

    def test_framework_unique_type(self, db_session):
        _make_framework(db_session, ComplianceFrameworkType.HIPAA)
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(Exception):
            _make_framework(db_session, ComplianceFrameworkType.HIPAA)

    def test_framework_repr(self, db_session):
        fw = _make_framework(db_session)
        assert "ComplianceFramework" in repr(fw)

    def test_framework_type_values(self):
        assert ComplianceFrameworkType.PCI_DSS_3_2_1 == "pci_dss_3.2.1"
        assert ComplianceFrameworkType.HIPAA == "hipaa"
        assert ComplianceFrameworkType.GDPR == "gdpr"
        assert ComplianceFrameworkType.SOC2 == "soc2"
        assert ComplianceFrameworkType.ISO27001 == "iso27001"


class TestComplianceRequirementModel:

    def test_create_requirement(self, db_session):
        fw = _make_framework(db_session)
        req = ComplianceRequirement(
            framework_id=fw.id,
            requirement_id="1.1",
            requirement_text="Establish firewall standards",
            control_objective="Network security",
            severity="CRITICAL",
            related_cve_patterns=["CWE-200"],
            tool_mappings={"nmap": ["open-port"]},
        )
        db_session.add(req)
        db_session.commit()
        db_session.refresh(req)

        assert req.id is not None
        assert req.framework_id == fw.id
        assert req.requirement_id == "1.1"

    def test_requirement_cve_patterns_json(self, db_session):
        fw = _make_framework(db_session)
        req = ComplianceRequirement(
            framework_id=fw.id,
            requirement_id="2.1",
            requirement_text="Test requirement",
            related_cve_patterns=["CWE-89", "CWE-78"],
        )
        db_session.add(req)
        db_session.commit()
        db_session.refresh(req)
        assert isinstance(req.related_cve_patterns, list)
        assert "CWE-89" in req.related_cve_patterns

    def test_requirement_tool_mappings_json(self, db_session):
        fw = _make_framework(db_session)
        req = ComplianceRequirement(
            framework_id=fw.id,
            requirement_id="3.1",
            requirement_text="Test",
            tool_mappings={"nmap": ["scan"], "hydra": ["brute"]},
        )
        db_session.add(req)
        db_session.commit()
        db_session.refresh(req)
        assert "nmap" in req.tool_mappings


class TestComplianceMappingResultModel:

    def test_create_mapping_result(self, db_session):
        project, _ = _make_project_with_owner(db_session)
        fw = _make_framework(db_session)

        result = ComplianceMappingResult(
            project_id=project.id,
            framework_id=fw.id,
            total_requirements=5,
            met_requirements=3,
            non_met_requirements=2,
            partial_met_requirements=0,
            not_applicable=0,
            compliance_score=60,
            compliance_status=ComplianceStatus.PARTIAL,
            audit_findings=[],
        )
        db_session.add(result)
        db_session.commit()
        db_session.refresh(result)

        assert result.id is not None
        assert result.compliance_score == 60
        assert result.compliance_status == ComplianceStatus.PARTIAL

    def test_compliance_status_values(self):
        assert ComplianceStatus.COMPLIANT == "COMPLIANT"
        assert ComplianceStatus.PARTIAL == "PARTIAL"
        assert ComplianceStatus.NON_COMPLIANT == "NON_COMPLIANT"


class TestComplianceEvidenceLogModel:

    def test_create_evidence_log(self, db_session):
        project, _ = _make_project_with_owner(db_session)
        fw = _make_framework(db_session)

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

        log = ComplianceEvidenceLog(
            mapping_result_id=mapping.id,
            requirement_id="1.1",
            status=EvidenceStatus.MET,
            evidence_text="No issues found",
            proof_of_compliance={"tool": "nmap"},
        )
        db_session.add(log)
        db_session.commit()
        db_session.refresh(log)

        assert log.id is not None
        assert log.status == EvidenceStatus.MET

    def test_evidence_status_values(self):
        assert EvidenceStatus.MET == "MET"
        assert EvidenceStatus.NON_MET == "NON_MET"
        assert EvidenceStatus.PARTIAL == "PARTIAL"
        assert EvidenceStatus.NOT_APPLICABLE == "NOT_APPLICABLE"


class TestComplianceControlMatrixModel:

    def test_create_control_matrix(self, db_session):
        project, _ = _make_project_with_owner(db_session)
        fw = _make_framework(db_session)

        ctrl = ComplianceControlMatrix(
            project_id=project.id,
            framework_id=fw.id,
            requirement_id="1.1",
            control_description="Firewall configured",
            control_owner="Security Team",
            implementation_status=ControlImplementationStatus.IMPLEMENTED,
        )
        db_session.add(ctrl)
        db_session.commit()
        db_session.refresh(ctrl)

        assert ctrl.id is not None
        assert ctrl.implementation_status == ControlImplementationStatus.IMPLEMENTED

    def test_control_implementation_status_values(self):
        assert ControlImplementationStatus.PLANNED == "PLANNED"
        assert ControlImplementationStatus.IN_PROGRESS == "IN_PROGRESS"
        assert ControlImplementationStatus.IMPLEMENTED == "IMPLEMENTED"
        assert ControlImplementationStatus.TESTED == "TESTED"
