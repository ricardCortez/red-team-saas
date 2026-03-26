"""Unit tests for FindingEnricher - Phase 12"""
import pytest
from unittest.mock import MagicMock, patch
from app.core.threat_intel.enricher import FindingEnricher, CVE_PATTERN
from app.models.cve import CVE
from app.models.mitre_technique import MitreTechnique
from app.models.ioc import IOC, IOCType, IOCThreatLevel


def _make_finding(title="Test Finding", description="", host=None, risk_score=5.0):
    f = MagicMock()
    f.title = title
    f.description = description
    f.host = host
    f.risk_score = risk_score
    return f


def _make_cve(cve_id="CVE-2024-1234", cvss=7.5, severity="high", is_kev=False, mitre=None):
    cve = MagicMock(spec=CVE)
    cve.cve_id = cve_id
    cve.cvss_v3_score = cvss
    cve.severity = severity
    cve.is_kev = is_kev
    cve.description = f"Description of {cve_id}"
    cve.mitre_techniques = mitre or []
    return cve


class TestFindingEnricher:

    def test_enrich_finding_with_cve_in_description(self, db_session):
        finding = _make_finding(
            title="SQL Injection",
            description="This relates to CVE-2024-1234 in Apache.",
        )
        cve = _make_cve("CVE-2024-1234", cvss=7.5, severity="high")

        enricher = FindingEnricher(db_session)
        with patch.object(enricher, "_get_or_fetch_cve", return_value=cve):
            intel = enricher.enrich_finding(finding)

        assert len(intel["cves"]) == 1
        assert intel["cves"][0]["cve_id"] == "CVE-2024-1234"

    def test_enrich_finding_no_cve_returns_empty(self, db_session):
        finding = _make_finding(title="Generic Finding", description="No CVE here")
        enricher = FindingEnricher(db_session)
        intel = enricher.enrich_finding(finding)
        assert intel["cves"] == []
        assert intel["mitre_techniques"] == []
        assert intel["ioc_matches"] == []
        assert intel["risk_adjustment"] == 0.0

    def test_enrich_finding_ioc_host_match(self, db_session):
        finding = _make_finding(host="192.168.1.100")
        ioc = MagicMock(spec=IOC)
        ioc.value = "192.168.1.100"
        ioc.ioc_type = IOCType.IP
        ioc.threat_level = IOCThreatLevel.HIGH
        ioc.source = "feodotracker"
        ioc.confidence = 0.9
        ioc.is_active = True

        enricher = FindingEnricher(db_session)
        # Mock the IOC query
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = ioc
        db_session.query = MagicMock(return_value=mock_query)

        with patch.object(enricher, "_get_or_fetch_cve", return_value=None):
            # Patch CVE_PATTERN to return empty (no CVEs in text)
            with patch("app.core.threat_intel.enricher.CVE_PATTERN") as mock_pattern:
                mock_pattern.findall.return_value = []
                intel = enricher.enrich_finding(finding)

        assert len(intel["ioc_matches"]) == 1
        assert intel["ioc_matches"][0]["value"] == "192.168.1.100"
        assert intel["risk_adjustment"] >= 1.0

    def test_risk_adjustment_critical_cvss(self, db_session):
        finding = _make_finding(
            title="RCE via CVE-2024-9999",
            description="Remote code execution CVE-2024-9999",
        )
        cve = _make_cve("CVE-2024-9999", cvss=9.8, severity="critical", is_kev=False)

        enricher = FindingEnricher(db_session)
        with patch.object(enricher, "_get_or_fetch_cve", return_value=cve):
            intel = enricher.enrich_finding(finding)

        assert intel["risk_adjustment"] >= 1.5

    def test_risk_adjustment_kev(self, db_session):
        finding = _make_finding(
            title="KEV vulnerability CVE-2024-8888",
            description="CISA KEV entry CVE-2024-8888",
        )
        cve = _make_cve("CVE-2024-8888", cvss=7.0, severity="high", is_kev=True)

        enricher = FindingEnricher(db_session)
        with patch.object(enricher, "_get_or_fetch_cve", return_value=cve):
            intel = enricher.enrich_finding(finding)

        assert intel["risk_adjustment"] >= 2.0

    def test_get_or_fetch_cve_uses_cache(self, db_session):
        """Should return cached CVE without calling NVD."""
        from app.models.cve import CVE as CVEModel
        cve = CVEModel(
            cve_id="CVE-2023-0001",
            description="Cached CVE",
            cvss_v3_score=6.5,
            severity="medium",
        )
        db_session.add(cve)
        db_session.commit()

        enricher = FindingEnricher(db_session)
        with patch.object(enricher.nvd, "get_cve") as mock_nvd:
            result = enricher._get_or_fetch_cve("CVE-2023-0001")
            mock_nvd.assert_not_called()

        assert result is not None
        assert result.cve_id == "CVE-2023-0001"

    def test_get_or_fetch_cve_fetches_from_nvd_on_miss(self, db_session):
        """Should call NVD when CVE not in local DB."""
        nvd_data = {
            "cve_id": "CVE-2024-5555",
            "description": "New CVE from NVD",
            "cvss_v3_score": 8.0,
            "cvss_v3_vector": None,
            "cvss_v2_score": None,
            "severity": "high",
            "cwe_ids": [],
            "affected_products": [],
            "references": [],
            "published_at": None,
            "modified_at": None,
        }
        enricher = FindingEnricher(db_session)
        with patch.object(enricher.nvd, "get_cve", return_value=nvd_data):
            result = enricher._get_or_fetch_cve("CVE-2024-5555")

        assert result is not None
        assert result.cve_id == "CVE-2024-5555"

    def test_get_or_fetch_cve_returns_none_when_nvd_misses(self, db_session):
        enricher = FindingEnricher(db_session)
        with patch.object(enricher.nvd, "get_cve", return_value=None):
            result = enricher._get_or_fetch_cve("CVE-9999-9999")
        assert result is None

    def test_cve_pattern_extracts_ids(self):
        text = "Multiple CVEs: CVE-2024-1234, CVE-2023-99999 and cve-2021-44228"
        matches = CVE_PATTERN.findall(text)
        assert len(matches) == 3

    def test_enrich_finding_with_mitre_from_cve(self, db_session):
        tech = MitreTechnique(
            technique_id="T1190",
            name="Exploit Public-Facing Application",
            tactic="initial-access",
            tactic_name="Initial Access",
        )
        db_session.add(tech)
        db_session.commit()

        finding = _make_finding(
            title="Finding with CVE-2024-0100",
            description="Relates to CVE-2024-0100",
        )
        cve = _make_cve("CVE-2024-0100", cvss=8.5, mitre=["T1190"])

        enricher = FindingEnricher(db_session)
        with patch.object(enricher, "_get_or_fetch_cve", return_value=cve):
            intel = enricher.enrich_finding(finding)

        assert len(intel["mitre_techniques"]) == 1
        assert intel["mitre_techniques"][0]["technique_id"] == "T1190"
