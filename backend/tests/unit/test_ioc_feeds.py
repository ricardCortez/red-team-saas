"""Unit tests for IOC feed clients - Phase 12"""
import pytest
from unittest.mock import patch, MagicMock
from app.core.threat_intel.ioc_feeds import IOCFeedClient


class TestIOCFeedClient:

    def test_fetch_urlhaus_mock_http(self):
        client = IOCFeedClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "urls": [
                {
                    "url": "http://malicious.example.com/payload",
                    "url_status": "online",
                    "threat": "malware_download",
                    "tags": ["emotet"],
                    "date_added": "2024-01-01 10:00:00 UTC",
                },
                {
                    "url": "http://offline.example.com/old",
                    "url_status": "offline",  # should be filtered out
                    "threat": "phishing",
                    "tags": [],
                    "date_added": "2023-12-01 10:00:00 UTC",
                },
            ]
        }
        with patch("app.core.threat_intel.ioc_feeds.httpx.post", return_value=mock_resp):
            iocs = client.fetch_urlhaus(limit=10)

        assert len(iocs) == 1  # offline filtered out
        assert iocs[0]["value"] == "http://malicious.example.com/payload"
        assert iocs[0]["ioc_type"] == "url"
        assert iocs[0]["threat_level"] == "high"
        assert iocs[0]["source"] == "urlhaus"
        assert "emotet" in iocs[0]["tags"]

    def test_fetch_urlhaus_returns_empty_on_error(self):
        client = IOCFeedClient()
        with patch("app.core.threat_intel.ioc_feeds.httpx.post", side_effect=Exception("timeout")):
            iocs = client.fetch_urlhaus()
        assert iocs == []

    def test_fetch_urlhaus_returns_empty_on_http_error(self):
        client = IOCFeedClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        with patch("app.core.threat_intel.ioc_feeds.httpx.post", return_value=mock_resp):
            iocs = client.fetch_urlhaus()
        assert iocs == []

    def test_fetch_feodo_ips_parses_txt(self):
        client = IOCFeedClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = (
            "# Feodo Tracker - Blocklist\n"
            "# Generated 2024-01-01\n"
            "185.220.101.1\n"
            "192.168.1.100\n"
            "\n"  # empty line should be skipped
        )
        with patch("app.core.threat_intel.ioc_feeds.httpx.get", return_value=mock_resp):
            iocs = client.fetch_feodo_ips()

        assert len(iocs) == 2
        values = [ioc["value"] for ioc in iocs]
        assert "185.220.101.1" in values
        assert "192.168.1.100" in values
        for ioc in iocs:
            assert ioc["ioc_type"] == "ip"
            assert ioc["threat_level"] == "high"
            assert ioc["confidence"] == 0.90
            assert ioc["source"] == "feodotracker"
            assert "c2" in ioc["tags"]

    def test_fetch_feodo_ips_returns_empty_on_error(self):
        client = IOCFeedClient()
        with patch("app.core.threat_intel.ioc_feeds.httpx.get", side_effect=Exception("connect error")):
            iocs = client.fetch_feodo_ips()
        assert iocs == []

    def test_fetch_feodo_ips_returns_empty_on_http_error(self):
        client = IOCFeedClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        with patch("app.core.threat_intel.ioc_feeds.httpx.get", return_value=mock_resp):
            iocs = client.fetch_feodo_ips()
        assert iocs == []

    def test_fetch_all_combines_feeds(self):
        client = IOCFeedClient()
        feodo_iocs = [{"value": "1.2.3.4", "ioc_type": "ip", "threat_level": "high",
                       "confidence": 0.9, "source": "feodotracker", "description": "C2",
                       "tags": ["c2"]}]
        urlhaus_iocs = [{"value": "http://bad.example.com/x", "ioc_type": "url",
                         "threat_level": "high", "confidence": 0.85, "source": "urlhaus",
                         "description": "malware", "tags": []}]

        with patch.object(client, "fetch_feodo_ips", return_value=feodo_iocs):
            with patch.object(client, "fetch_urlhaus", return_value=urlhaus_iocs):
                all_iocs = client.fetch_all()

        assert len(all_iocs) == 2
        types = {ioc["ioc_type"] for ioc in all_iocs}
        assert "ip" in types
        assert "url" in types
