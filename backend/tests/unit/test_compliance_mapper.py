"""Unit tests for ComplianceMapper service - Phase 13"""
import json
import pytest
from unittest.mock import patch, MagicMock
from app.services.compliance_mapper import ComplianceMapper
from app.models.compliance import (
    ComplianceFramework,
    ComplianceRequirement,
    ComplianceMappingResult,
    ComplianceFrameworkType,
    ComplianceStatus,
    EvidenceStatus,
)
from app.models.finding import Finding, Severity, FindingStatus


def _make_framework(db, fw_type=ComplianceFrameworkType.PCI_DSS_3_2_1):
    fw = ComplianceFramework(
        name=f"Test {fw_type}",
        framework_type=fw_type,
        version="1.0",
        description="Test",
        total_requirements=3,
    )
    db.add(fw)
    db.flush()
    return fw


def _make_requirement(db, fw_id, req_id="1.1", cwe_patterns=None, tool_map=None):
    req = ComplianceRequirement(
        framework_id=fw_id,
        requirement_id=req_id,
        requirement_text=f"Requirement {req_id}",
        severity="HIGH",
        related_cve_patterns=cwe_patterns or ["CWE-200"],
        tool_mappings=tool_map or {"nmap": ["open-port"]},
    )
    db.add(req)
    db.flush()
    return req


def _make_finding(db, project_id, title="Test Finding", severity=Severity.low,
                  cve_ids=None, tool="nmap"):
    f = Finding(
        title=title,
        description="Test",
        severity=severity,
        status=FindingStatus.open,
        project_id=project_id,
        cve_ids=json.dumps(cve_ids or []),
        tool=tool,
    )
    db.add(f)
    db.flush()
    return f


def _project_owner(db):
    from app.models.user import User
    from app.models.project import Project, ProjectStatus, ProjectScope
    from app.core.security import PasswordHandler

    owner = User(
        email="mapper_owner@test.com",
        username="mapperowner",
        hashed_password=PasswordHandler.hash_password("Pass123!"),
        is_active=True,
    )
    db.add(owner)
    db.flush()

    project = Project(
        name="Mapper Project",
        status=ProjectStatus.active,
        scope=ProjectScope.external,
        owner_id=owner.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


class TestComplianceMapperHelpers:

    def test_calculate_compliance_score_all_met(self):
        mapper = ComplianceMapper(None)
        score = mapper._calculate_compliance_score({
            "total": 10, "met": 10, "non_met": 0, "partial": 0, "not_applicable": 0
        })
        assert score == 100

    def test_calculate_compliance_score_none_met(self):
        mapper = ComplianceMapper(None)
        score = mapper._calculate_compliance_score({
            "total": 10, "met": 0, "non_met": 10, "partial": 0, "not_applicable": 0
        })
        assert score == 0

    def test_calculate_compliance_score_mixed(self):
        mapper = ComplianceMapper(None)
        score = mapper._calculate_compliance_score({
            "total": 5, "met": 3, "non_met": 2, "partial": 0, "not_applicable": 0
        })
        # (3/5)*100 = 60, penalty = (2/5)*30 = 12, score = 48
        assert score == 48

    def test_calculate_compliance_score_empty(self):
        mapper = ComplianceMapper(None)
        score = mapper._calculate_compliance_score({
            "total": 0, "met": 0, "non_met": 0, "partial": 0, "not_applicable": 0
        })
        assert score == 100

    def test_determine_compliance_status_compliant(self):
        mapper = ComplianceMapper(None)
        assert mapper._determine_compliance_status(90) == ComplianceStatus.COMPLIANT
        assert mapper._determine_compliance_status(85) == ComplianceStatus.COMPLIANT

    def test_determine_compliance_status_partial(self):
        mapper = ComplianceMapper(None)
        assert mapper._determine_compliance_status(70) == ComplianceStatus.PARTIAL
        assert mapper._determine_compliance_status(50) == ComplianceStatus.PARTIAL

    def test_determine_compliance_status_non_compliant(self):
        mapper = ComplianceMapper(None)
        assert mapper._determine_compliance_status(49) == ComplianceStatus.NON_COMPLIANT
        assert mapper._determine_compliance_status(0) == ComplianceStatus.NON_COMPLIANT

    def test_matches_pattern_exact(self):
        mapper = ComplianceMapper(None)
        assert mapper._matches_pattern("CWE-200", "CWE-200") is True
        assert mapper._matches_pattern("CWE-200", "CWE-201") is False

    def test_matches_pattern_wildcard(self):
        mapper = ComplianceMapper(None)
        assert mapper._matches_pattern("CWE-200", "CWE-*") is True
        assert mapper._matches_pattern("CVE-2024-1234", "CVE-*") is True

    def test_matches_pattern_empty_cve(self):
        mapper = ComplianceMapper(None)
        assert mapper._matches_pattern("", "CWE-*") is False
        assert mapper._matches_pattern(None, "CWE-*") is False

    def test_extract_cve_ids_json_list(self):
        mapper = ComplianceMapper(None)
        f = MagicMock()
        f.cve_ids = '["CWE-200", "CVE-2024-1234"]'
        ids = mapper._extract_cve_ids(f)
        assert "CWE-200" in ids
        assert "CVE-2024-1234" in ids

    def test_extract_cve_ids_null(self):
        mapper = ComplianceMapper(None)
        f = MagicMock()
        f.cve_ids = None
        assert mapper._extract_cve_ids(f) == []

    def test_extract_cve_ids_invalid_json(self):
        mapper = ComplianceMapper(None)
        f = MagicMock()
        f.cve_ids = "CWE-200"  # not JSON list
        ids = mapper._extract_cve_ids(f)
        assert "CWE-200" in ids


class TestEvaluateRequirement:

    def test_not_applicable_when_no_findings(self, db_session):
        fw = _make_framework(db_session)
        req = _make_requirement(db_session, fw.id, cwe_patterns=["CWE-999"])
        db_session.commit()

        mapper = ComplianceMapper(db_session)
        status, matched = mapper._evaluate_requirement(req, [])
        assert status == EvidenceStatus.NOT_APPLICABLE
        assert matched == []

    def test_non_met_for_critical_finding(self, db_session):
        project = _project_owner(db_session)
        fw = _make_framework(db_session)
        req = _make_requirement(db_session, fw.id, cwe_patterns=["CWE-200"])
        db_session.commit()

        finding = _make_finding(
            db_session, project.id,
            severity=Severity.critical,
            cve_ids=["CWE-200"],
        )
        db_session.commit()

        mapper = ComplianceMapper(db_session)
        status, matched = mapper._evaluate_requirement(req, [finding])
        assert status == EvidenceStatus.NON_MET

    def test_non_met_for_high_finding(self, db_session):
        project = _project_owner(db_session)
        fw = _make_framework(db_session)
        req = _make_requirement(db_session, fw.id, cwe_patterns=["CWE-200"])
        db_session.commit()

        finding = _make_finding(
            db_session, project.id,
            severity=Severity.high,
            cve_ids=["CWE-200"],
        )
        db_session.commit()

        mapper = ComplianceMapper(db_session)
        status, matched = mapper._evaluate_requirement(req, [finding])
        assert status == EvidenceStatus.NON_MET

    def test_met_for_low_finding(self, db_session):
        project = _project_owner(db_session)
        fw = _make_framework(db_session)
        req = _make_requirement(db_session, fw.id, cwe_patterns=["CWE-200"])
        db_session.commit()

        finding = _make_finding(
            db_session, project.id,
            severity=Severity.low,
            cve_ids=["CWE-200"],
        )
        db_session.commit()

        mapper = ComplianceMapper(db_session)
        status, matched = mapper._evaluate_requirement(req, [finding])
        assert status == EvidenceStatus.MET
        assert finding in matched

    def test_partial_for_many_low_findings(self, db_session):
        project = _project_owner(db_session)
        fw = _make_framework(db_session)
        req = _make_requirement(db_session, fw.id, cwe_patterns=["CWE-200"])
        db_session.commit()

        findings = [
            _make_finding(db_session, project.id, severity=Severity.low, cve_ids=["CWE-200"])
            for _ in range(5)
        ]
        db_session.commit()

        mapper = ComplianceMapper(db_session)
        status, matched = mapper._evaluate_requirement(req, findings)
        assert status == EvidenceStatus.PARTIAL

    def test_tool_mapping_match(self, db_session):
        project = _project_owner(db_session)
        fw = _make_framework(db_session)
        req = _make_requirement(db_session, fw.id, cwe_patterns=[], tool_map={"nmap": ["scan"]})
        db_session.commit()

        finding = _make_finding(db_session, project.id, severity=Severity.info, tool="nmap")
        db_session.commit()

        mapper = ComplianceMapper(db_session)
        status, matched = mapper._evaluate_requirement(req, [finding])
        assert finding in matched


class TestAssessProject:

    def test_assess_project_success(self, db_session):
        project = _project_owner(db_session)
        fw = _make_framework(db_session)
        _make_requirement(db_session, fw.id, "1.1", cwe_patterns=["CWE-999"])
        db_session.commit()

        mapper = ComplianceMapper(db_session)
        result = mapper.assess_project(project.id, "pci_dss_3.2.1", [])

        assert result.id is not None
        assert result.project_id == project.id
        assert 0 <= result.compliance_score <= 100

    def test_assess_project_not_found_raises(self, db_session):
        mapper = ComplianceMapper(db_session)
        with pytest.raises(ValueError, match="not found"):
            mapper.assess_project(1, "nonexistent_framework", [])

    def test_assess_project_creates_evidence_logs(self, db_session):
        project = _project_owner(db_session)
        fw = _make_framework(db_session)
        _make_requirement(db_session, fw.id, "1.1", cwe_patterns=["CWE-200"])
        db_session.commit()

        finding = _make_finding(
            db_session, project.id,
            severity=Severity.critical,
            cve_ids=["CWE-200"],
        )
        db_session.commit()

        mapper = ComplianceMapper(db_session)
        result = mapper.assess_project(project.id, "pci_dss_3.2.1", [finding])

        from app.crud.compliance import ComplianceCRUD
        logs = ComplianceCRUD.get_evidence_by_mapping(db_session, result.id)
        assert len(logs) >= 1
