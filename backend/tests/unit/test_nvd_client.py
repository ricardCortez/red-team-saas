"""Unit tests for NVD client - Phase 12"""
import pytest
from unittest.mock import patch, MagicMock
from app.core.threat_intel.nvd_client import NVDClient


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_vuln(cve_id="CVE-2024-1234", score=9.8, severity="CRITICAL", cwe="CWE-89"):
    return {
        "cve": {
            "id": cve_id,
            "descriptions": [{"lang": "en", "value": f"Test description for {cve_id}"}],
            "metrics": {
                "cvssMetricV31": [{
                    "cvssData": {
                        "baseScore": score,
                        "vectorString": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
                        "baseSeverity": severity,
                    }
                }]
            },
            "weaknesses": [{"description": [{"value": cwe}]}],
            "configurations": [
                {"nodes": [{"cpeMatch": [{"vulnerable": True, "criteria": "cpe:2.3:a:vendor:product:1.0:*:*:*:*:*:*:*"}]}]}
            ],
            "references": [{"url": "https://example.com/advisory"}],
            "published": "2024-01-01T00:00:00.000",
            "lastModified": "2024-01-02T00:00:00.000",
        }
    }


class TestNVDClientParseCve:

    def test_parse_cve_extracts_cvss_v3(self):
        client = NVDClient()
        vuln = _make_vuln(score=9.8, severity="CRITICAL")
        result = client._parse_cve(vuln)
        assert result["cvss_v3_score"] == 9.8
        assert result["cvss_v3_vector"] == "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
        assert result["severity"] == "critical"

    def test_parse_cve_extracts_cwe(self):
        client = NVDClient()
        vuln = _make_vuln(cwe="CWE-79")
        result = client._parse_cve(vuln)
        assert "CWE-79" in result["cwe_ids"]

    def test_parse_cve_extracts_affected_products(self):
        client = NVDClient()
        vuln = _make_vuln()
        result = client._parse_cve(vuln)
        assert len(result["affected_products"]) == 1
        assert "cpe:2.3:a:vendor:product" in result["affected_products"][0]

    def test_parse_cve_extracts_description(self):
        client = NVDClient()
        vuln = _make_vuln(cve_id="CVE-2024-9999")
        result = client._parse_cve(vuln)
        assert "CVE-2024-9999" in result["description"]

    def test_parse_cve_uses_cvss_v30_fallback(self):
        client = NVDClient()
        vuln = {
            "cve": {
                "id": "CVE-2020-0001",
                "descriptions": [{"lang": "en", "value": "Old CVE"}],
                "metrics": {
                    "cvssMetricV30": [{
                        "cvssData": {"baseScore": 7.5, "baseSeverity": "HIGH"}
                    }]
                },
                "weaknesses": [],
                "configurations": [],
                "references": [],
                "published": "2020-01-01T00:00:00.000",
                "lastModified": "2020-01-02T00:00:00.000",
            }
        }
        result = client._parse_cve(vuln)
        assert result["cvss_v3_score"] == 7.5
        assert result["severity"] == "high"

    def test_parse_cve_extracts_references(self):
        client = NVDClient()
        vuln = _make_vuln()
        result = client._parse_cve(vuln)
        assert "https://example.com/advisory" in result["references"]


class TestNVDClientHttp:

    def test_get_cve_mock_http(self):
        client = NVDClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "vulnerabilities": [_make_vuln("CVE-2024-1234")]
        }
        with patch("app.core.threat_intel.nvd_client.httpx.get", return_value=mock_resp):
            with patch("app.core.threat_intel.nvd_client.time.sleep"):
                result = client.get_cve("CVE-2024-1234")
        assert result is not None
        assert result["cve_id"] == "CVE-2024-1234"
        assert result["cvss_v3_score"] == 9.8

    def test_get_cve_returns_none_on_404(self):
        client = NVDClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        with patch("app.core.threat_intel.nvd_client.httpx.get", return_value=mock_resp):
            with patch("app.core.threat_intel.nvd_client.time.sleep"):
                result = client.get_cve("CVE-9999-9999")
        assert result is None

    def test_get_cve_returns_none_on_exception(self):
        client = NVDClient()
        with patch("app.core.threat_intel.nvd_client.httpx.get", side_effect=Exception("network error")):
            result = client.get_cve("CVE-2024-0001")
        assert result is None

    def test_search_by_keyword_mock_http(self):
        client = NVDClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "vulnerabilities": [_make_vuln("CVE-2024-0001"), _make_vuln("CVE-2024-0002")]
        }
        with patch("app.core.threat_intel.nvd_client.httpx.get", return_value=mock_resp):
            with patch("app.core.threat_intel.nvd_client.time.sleep"):
                results = client.search_by_keyword("apache", limit=10)
        assert len(results) == 2

    def test_search_by_keyword_returns_empty_on_error(self):
        client = NVDClient()
        with patch("app.core.threat_intel.nvd_client.httpx.get", side_effect=Exception("timeout")):
            results = client.search_by_keyword("apache")
        assert results == []

    def test_rate_limit_delay_with_api_key(self):
        client = NVDClient(api_key="test-key")
        assert client.rate_limit_delay == 0.6

    def test_rate_limit_delay_without_api_key(self):
        client = NVDClient()
        assert client.rate_limit_delay == 6.0
