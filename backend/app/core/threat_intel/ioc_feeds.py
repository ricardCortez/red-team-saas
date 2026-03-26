"""Public IOC feed clients - Phase 12"""
import httpx
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

URLHAUS_URL    = "https://urlhaus-api.abuse.ch/v1/urls/recent/"
FEODO_IP_URL   = "https://feodotracker.abuse.ch/downloads/ipblocklist.txt"


class IOCFeedClient:

    def fetch_urlhaus(self, limit: int = 100) -> List[Dict]:
        """Recent malicious URLs from URLhaus."""
        try:
            resp = httpx.post(
                URLHAUS_URL,
                data={"query": "get_urls", "limit": limit},
                timeout=15,
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            iocs = []
            for url_data in data.get("urls", []):
                if url_data.get("url_status") != "online":
                    continue
                iocs.append({
                    "value":        url_data.get("url"),
                    "ioc_type":     "url",
                    "threat_level": "high",
                    "confidence":   0.85,
                    "source":       "urlhaus",
                    "description":  url_data.get("threat", ""),
                    "tags":         url_data.get("tags", []) or [],
                    "first_seen":   url_data.get("date_added"),
                })
            return iocs
        except Exception as e:
            logger.error(f"URLhaus fetch failed: {e}")
            return []

    def fetch_feodo_ips(self) -> List[Dict]:
        """Botnet C2 IPs from Feodo Tracker."""
        try:
            resp = httpx.get(FEODO_IP_URL, timeout=15)
            if resp.status_code != 200:
                return []
            iocs = []
            for line in resp.text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                iocs.append({
                    "value":        line,
                    "ioc_type":     "ip",
                    "threat_level": "high",
                    "confidence":   0.90,
                    "source":       "feodotracker",
                    "description":  "Known C2 botnet IP",
                    "tags":         ["c2", "botnet"],
                })
            return iocs
        except Exception as e:
            logger.error(f"Feodo fetch failed: {e}")
            return []

    def fetch_all(self) -> List[Dict]:
        iocs: List[Dict] = []
        iocs.extend(self.fetch_feodo_ips())
        iocs.extend(self.fetch_urlhaus(limit=200))
        return iocs
