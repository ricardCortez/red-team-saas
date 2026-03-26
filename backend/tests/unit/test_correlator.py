"""Unit tests for ThreatCorrelator - Phase 12"""
import pytest
from app.core.threat_intel.correlator import ThreatCorrelator
from app.models.cve import CVE
from app.models.mitre_technique import MitreTechnique
from app.models.ioc import IOC, IOCType, IOCThreatLevel


def _create_cve(db, cve_id, cvss=7.5, severity="high", is_kev=False, mitre=None):
    cve = CVE(
        cve_id=cve_id,
        description=f"Test description for {cve_id}",
        cvss_v3_score=cvss,
        severity=severity,
        is_kev=is_kev,
        mitre_techniques=mitre or [],
    )
    db.add(cve)
    db.commit()
    db.refresh(cve)
    return cve


def _create_technique(db, technique_id, name, tactic="initial-access", tactic_name="Initial Access"):
    tech = MitreTechnique(
        technique_id=technique_id,
        name=name,
        tactic=tactic,
        tactic_name=tactic_name,
    )
    db.add(tech)
    db.commit()
    db.refresh(tech)
    return tech


def _create_ioc(db, value, ioc_type=IOCType.IP, threat_level=IOCThreatLevel.HIGH,
                source="feodotracker", confidence=0.9, is_active=True):
    ioc = IOC(
        value=value,
        ioc_type=ioc_type,
        threat_level=threat_level,
        source=source,
        confidence=confidence,
        is_active=is_active,
        tags=["c2"],
    )
    db.add(ioc)
    db.commit()
    db.refresh(ioc)
    return ioc


class TestThreatCorrelator:

    def test_cve_to_mitre_returns_techniques(self, db_session):
        _create_technique(db_session, "T1190", "Exploit Public-Facing Application")
        _create_cve(db_session, "CVE-2024-0001", mitre=["T1190"])

        correlator = ThreatCorrelator(db_session)
        result = correlator.cve_to_mitre("CVE-2024-0001")

        assert len(result) == 1
        assert result[0]["technique_id"] == "T1190"
        assert result[0]["name"] == "Exploit Public-Facing Application"

    def test_cve_to_mitre_returns_empty_for_unknown_cve(self, db_session):
        correlator = ThreatCorrelator(db_session)
        result = correlator.cve_to_mitre("CVE-9999-9999")
        assert result == []

    def test_cve_to_mitre_returns_empty_when_no_techniques(self, db_session):
        _create_cve(db_session, "CVE-2024-0002", mitre=[])
        correlator = ThreatCorrelator(db_session)
        result = correlator.cve_to_mitre("CVE-2024-0002")
        assert result == []

    def test_mitre_to_cves_ordered_by_cvss(self, db_session):
        _create_cve(db_session, "CVE-2024-LOW",  cvss=4.0, mitre=["T1059"])
        _create_cve(db_session, "CVE-2024-HIGH", cvss=9.8, mitre=["T1059"])
        _create_cve(db_session, "CVE-2024-MED",  cvss=6.5, mitre=["T1059"])

        correlator = ThreatCorrelator(db_session)
        result = correlator.mitre_to_cves("T1059")

        assert len(result) == 3
        scores = [r["cvss_v3"] for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_mitre_to_cves_returns_empty_for_unknown_technique(self, db_session):
        correlator = ThreatCorrelator(db_session)
        result = correlator.mitre_to_cves("T9999")
        assert result == []

    def test_check_ioc_found(self, db_session):
        _create_ioc(db_session, "10.0.0.1", confidence=0.95)

        correlator = ThreatCorrelator(db_session)
        result = correlator.check_ioc("10.0.0.1")

        assert result is not None
        assert result["value"] == "10.0.0.1"
        assert result["type"] == "ip"
        assert result["threat_level"] == "high"
        assert result["confidence"] == 0.95

    def test_check_ioc_not_found(self, db_session):
        correlator = ThreatCorrelator(db_session)
        result = correlator.check_ioc("8.8.8.8")
        assert result is None

    def test_check_ioc_inactive_not_returned(self, db_session):
        _create_ioc(db_session, "1.2.3.4", is_active=False)

        correlator = ThreatCorrelator(db_session)
        result = correlator.check_ioc("1.2.3.4")
        assert result is None

    def test_project_threat_profile_counts(self, db_session):
        from app.models.finding import Finding, Severity, FindingStatus
        from app.models.project import Project, ProjectStatus, ProjectScope
        from app.models.user import User
        from app.core.security import PasswordHandler

        owner = User(
            email="owner@test.com",
            username="owneruser",
            hashed_password=PasswordHandler.hash_password("Pass123!"),
            is_active=True,
        )
        db_session.add(owner)
        db_session.commit()

        project = Project(
            name="Test Project",
            description="Test",
            status=ProjectStatus.active,
            scope=ProjectScope.external,
            owner_id=owner.id,
        )
        db_session.add(project)
        db_session.commit()

        finding = Finding(
            title="SQL Injection via CVE-2024-1234",
            description="Critical vuln related to CVE-2024-1234",
            severity=Severity.critical,
            status=FindingStatus.open,
            project_id=project.id,
            is_duplicate=False,
        )
        db_session.add(finding)

        _create_cve(db_session, "CVE-2024-1234", cvss=9.8, is_kev=True, mitre=["T1190"])
        _create_technique(db_session, "T1190", "Exploit Public-Facing Application")
        db_session.commit()

        correlator = ThreatCorrelator(db_session)
        profile = correlator.project_threat_profile(project.id)

        assert profile["total_cves"] >= 1
        assert profile["kev_count"] >= 1
        assert profile["critical_cves"] >= 1
        assert isinstance(profile["tactics_coverage"], dict)

    def test_project_threat_profile_empty_project(self, db_session):
        correlator = ThreatCorrelator(db_session)
        profile = correlator.project_threat_profile(99999)

        assert profile["total_cves"] == 0
        assert profile["kev_count"] == 0
        assert profile["critical_cves"] == 0
        assert profile["mitre_techniques"] == 0
        assert profile["tactics_coverage"] == {}
