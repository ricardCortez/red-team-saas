"""Unit tests for MITRE ATT&CK client - Phase 12"""
import pytest
from unittest.mock import patch, MagicMock
from app.core.threat_intel.mitre_client import MITREClient, TACTIC_MAP


def _make_attack_pattern(
    tech_id="T1190",
    name="Exploit Public-Facing Application",
    tactic="initial-access",
    revoked=False,
    deprecated=False,
    is_sub=False,
    platforms=None,
):
    if platforms is None:
        platforms = ["Windows", "Linux", "macOS"]
    external_id = tech_id
    obj = {
        "type": "attack-pattern",
        "id": f"attack-pattern--{tech_id}",
        "name": name,
        "description": f"Description of {name}",
        "x_mitre_deprecated": deprecated,
        "revoked": revoked,
        "external_references": [
            {
                "source_name": "mitre-attack",
                "external_id": external_id,
                "url": f"https://attack.mitre.org/techniques/{external_id}/",
            }
        ],
        "kill_chain_phases": [{"kill_chain_name": "mitre-attack", "phase_name": tactic}],
        "x_mitre_platforms": platforms,
        "x_mitre_detection": "Monitor network traffic",
    }
    return obj


class TestMITREClientParseTechniques:

    def _bundle(self, objects):
        return {"type": "bundle", "objects": objects}

    def test_parse_techniques_filters_revoked(self):
        client = MITREClient()
        bundle = self._bundle([
            _make_attack_pattern("T1190", revoked=False),
            _make_attack_pattern("T1191", revoked=True),
        ])
        result = client._parse_techniques(bundle)
        ids = [t["technique_id"] for t in result]
        assert "T1190" in ids
        assert "T1191" not in ids

    def test_parse_techniques_filters_deprecated(self):
        client = MITREClient()
        bundle = self._bundle([
            _make_attack_pattern("T1190", deprecated=False),
            _make_attack_pattern("T1088", deprecated=True),
        ])
        result = client._parse_techniques(bundle)
        ids = [t["technique_id"] for t in result]
        assert "T1190" in ids
        assert "T1088" not in ids

    def test_parse_techniques_extracts_tactic(self):
        client = MITREClient()
        bundle = self._bundle([_make_attack_pattern("T1190", tactic="initial-access")])
        result = client._parse_techniques(bundle)
        assert result[0]["tactic"] == "initial-access"
        assert result[0]["tactic_name"] == "Initial Access"

    def test_parse_techniques_subtechnique_parent(self):
        client = MITREClient()
        bundle = self._bundle([
            {
                "type": "attack-pattern",
                "id": "attack-pattern--T1059.001",
                "name": "PowerShell",
                "description": "PowerShell sub-technique",
                "revoked": False,
                "x_mitre_deprecated": False,
                "external_references": [
                    {
                        "source_name": "mitre-attack",
                        "external_id": "T1059.001",
                        "url": "https://attack.mitre.org/techniques/T1059/001/",
                    }
                ],
                "kill_chain_phases": [{"kill_chain_name": "mitre-attack", "phase_name": "execution"}],
                "x_mitre_platforms": ["Windows"],
            }
        ])
        result = client._parse_techniques(bundle)
        assert len(result) == 1
        t = result[0]
        assert t["is_subtechnique"] is True
        assert t["parent_id"] == "T1059"
        assert t["technique_id"] == "T1059.001"

    def test_parse_techniques_platforms(self):
        client = MITREClient()
        platforms = ["Windows", "Linux"]
        bundle = self._bundle([_make_attack_pattern("T1190", platforms=platforms)])
        result = client._parse_techniques(bundle)
        assert result[0]["platforms"] == platforms

    def test_parse_techniques_skips_non_attack_patterns(self):
        client = MITREClient()
        bundle = self._bundle([
            {"type": "identity", "id": "identity--1"},
            {"type": "relationship", "id": "relationship--1"},
            _make_attack_pattern("T1190"),
        ])
        result = client._parse_techniques(bundle)
        assert len(result) == 1

    def test_parse_techniques_tactic_map_coverage(self):
        for tactic_key, tactic_name in TACTIC_MAP.items():
            assert isinstance(tactic_key, str)
            assert isinstance(tactic_name, str)

    def test_fetch_techniques_mock_http(self):
        client = MITREClient()
        bundle = {
            "type": "bundle",
            "objects": [_make_attack_pattern("T1190")],
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = bundle
        with patch("app.core.threat_intel.mitre_client.httpx.get", return_value=mock_resp):
            result = client.fetch_techniques()
        assert len(result) == 1
        assert result[0]["technique_id"] == "T1190"

    def test_fetch_techniques_returns_empty_on_http_error(self):
        client = MITREClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        with patch("app.core.threat_intel.mitre_client.httpx.get", return_value=mock_resp):
            result = client.fetch_techniques()
        assert result == []
