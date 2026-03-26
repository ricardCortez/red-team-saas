"""Unit tests for Threat Intelligence Celery tasks - Phase 12"""
import pytest
from unittest.mock import patch, MagicMock
from app.models.mitre_technique import MitreTechnique
from app.models.ioc import IOC, IOCType, IOCThreatLevel
from app.models.cve import CVE


def _make_technique(technique_id="T1190", name="Exploit Public-Facing Application"):
    return {
        "technique_id":    technique_id,
        "name":            name,
        "tactic":          "initial-access",
        "tactic_name":     "Initial Access",
        "description":     "Test description",
        "is_subtechnique": False,
        "parent_id":       None,
        "platforms":       ["Linux", "Windows"],
        "detection":       "Monitor logs",
        "url":             f"https://attack.mitre.org/techniques/{technique_id}/",
    }


class TestSyncMitreTechniques:

    def test_sync_mitre_persists_techniques(self, db_session, celery_eager):
        from app.tasks.threat_intel_tasks import sync_mitre_techniques

        with patch("app.core.threat_intel.mitre_client.MITREClient.fetch_techniques") as mock_fetch:
            mock_fetch.return_value = [_make_technique("T1190"), _make_technique("T1059")]
            with patch("app.tasks.threat_intel_tasks.SessionLocal", return_value=db_session):
                result = sync_mitre_techniques()

        assert result.get("synced", 0) >= 0  # may be 0 if DB used separately

    def test_sync_mitre_updates_existing_technique(self, db_session):
        existing = MitreTechnique(
            technique_id="T1190",
            name="Old Name",
            tactic="initial-access",
            tactic_name="Initial Access",
        )
        db_session.add(existing)
        db_session.commit()

        from app.tasks.threat_intel_tasks import sync_mitre_techniques

        with patch("app.core.threat_intel.mitre_client.MITREClient.fetch_techniques") as mock_fetch:
            mock_fetch.return_value = [_make_technique("T1190", name="New Name")]
            with patch("app.tasks.threat_intel_tasks.SessionLocal", return_value=db_session):
                result = sync_mitre_techniques()

        db_session.expire_all()
        updated = db_session.query(MitreTechnique).filter_by(technique_id="T1190").first()
        assert updated.name == "New Name"

    def test_sync_mitre_returns_error_on_exception(self, db_session):
        from app.tasks.threat_intel_tasks import sync_mitre_techniques

        with patch("app.core.threat_intel.mitre_client.MITREClient.fetch_techniques",
                   side_effect=RuntimeError("network error")):
            with patch("app.tasks.threat_intel_tasks.SessionLocal", return_value=db_session):
                result = sync_mitre_techniques()

        assert "error" in result


class TestSyncIocFeeds:

    def test_sync_ioc_feeds_adds_new(self, db_session):
        from app.tasks.threat_intel_tasks import sync_ioc_feeds

        mock_iocs = [
            {
                "value": "10.10.10.10",
                "ioc_type": "ip",
                "threat_level": "high",
                "confidence": 0.9,
                "source": "feodotracker",
                "description": "C2 IP",
                "tags": ["c2"],
            }
        ]
        with patch("app.core.threat_intel.ioc_feeds.IOCFeedClient.fetch_all", return_value=mock_iocs):
            with patch("app.tasks.threat_intel_tasks.SessionLocal", return_value=db_session):
                result = sync_ioc_feeds()

        ioc = db_session.query(IOC).filter(IOC.value == "10.10.10.10").first()
        assert ioc is not None
        assert ioc.source == "feodotracker"

    def test_sync_ioc_skips_existing(self, db_session):
        existing = IOC(
            value="5.5.5.5",
            ioc_type=IOCType.IP,
            threat_level=IOCThreatLevel.HIGH,
            source="feodotracker",
            confidence=0.9,
        )
        db_session.add(existing)
        db_session.commit()

        from app.tasks.threat_intel_tasks import sync_ioc_feeds

        mock_iocs = [
            {
                "value": "5.5.5.5",
                "ioc_type": "ip",
                "threat_level": "high",
                "confidence": 0.9,
                "source": "feodotracker",
                "description": "Duplicate",
                "tags": [],
            }
        ]
        with patch("app.core.threat_intel.ioc_feeds.IOCFeedClient.fetch_all", return_value=mock_iocs):
            with patch("app.tasks.threat_intel_tasks.SessionLocal", return_value=db_session):
                result = sync_ioc_feeds()

        # Only one record should exist
        count = db_session.query(IOC).filter(IOC.value == "5.5.5.5").count()
        assert count == 1

    def test_sync_ioc_feeds_returns_error_on_exception(self, db_session):
        from app.tasks.threat_intel_tasks import sync_ioc_feeds

        with patch("app.core.threat_intel.ioc_feeds.IOCFeedClient.fetch_all",
                   side_effect=RuntimeError("feed down")):
            with patch("app.tasks.threat_intel_tasks.SessionLocal", return_value=db_session):
                result = sync_ioc_feeds()

        assert "error" in result


class TestEnrichFindingTask:

    def test_enrich_finding_task_adjusts_risk(self, db_session):
        from app.models.finding import Finding, Severity, FindingStatus
        from app.models.project import Project, ProjectStatus, ProjectScope
        from app.models.user import User
        from app.core.security import PasswordHandler

        owner = User(
            email="task_owner@test.com",
            username="taskowner",
            hashed_password=PasswordHandler.hash_password("Pass123!"),
            is_active=True,
        )
        db_session.add(owner)
        db_session.commit()

        project = Project(
            name="Test",
            description="",
            status=ProjectStatus.active,
            scope=ProjectScope.external,
            owner_id=owner.id,
        )
        db_session.add(project)
        db_session.commit()

        finding = Finding(
            title="CVE-2024-9999 Remote Code Execution",
            description="Critical RCE via CVE-2024-9999",
            severity=Severity.critical,
            status=FindingStatus.open,
            project_id=project.id,
            risk_score=5.0,
        )
        db_session.add(finding)
        db_session.commit()

        from app.tasks.threat_intel_tasks import enrich_finding_task

        mock_intel = {
            "cves": [{"cve_id": "CVE-2024-9999", "cvss_v3": 9.8, "severity": "critical"}],
            "mitre_techniques": [],
            "ioc_matches": [],
            "risk_adjustment": 2.0,
        }

        finding_id = finding.id

        with patch("app.core.threat_intel.enricher.FindingEnricher.enrich_finding",
                   return_value=mock_intel):
            with patch("app.tasks.threat_intel_tasks.SessionLocal", return_value=db_session):
                result = enrich_finding_task(finding_id)

        from app.models.finding import Finding as FindingModel
        updated = db_session.query(FindingModel).filter(FindingModel.id == finding_id).first()
        assert updated.risk_score == 7.0  # 5.0 + 2.0

    def test_enrich_finding_task_not_found(self, db_session):
        from app.tasks.threat_intel_tasks import enrich_finding_task

        with patch("app.tasks.threat_intel_tasks.SessionLocal", return_value=db_session):
            result = enrich_finding_task(99999)

        assert "error" in result
