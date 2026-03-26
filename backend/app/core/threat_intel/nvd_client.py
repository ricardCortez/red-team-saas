"""NVD API v2 client - Phase 12"""
import httpx
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

NVD_BASE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"


class NVDClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        # Con API key: 50 req/30s. Sin key: 5 req/30s
        self.rate_limit_delay = 0.6 if api_key else 6.0

    def _headers(self) -> Dict:
        h = {"Accept": "application/json"}
        if self.api_key:
            h["apiKey"] = self.api_key
        return h

    def get_cve(self, cve_id: str) -> Optional[Dict]:
        """Fetch single CVE by ID."""
        try:
            resp = httpx.get(
                NVD_BASE_URL,
                params={"cveId": cve_id},
                headers=self._headers(),
                timeout=15,
            )
            time.sleep(self.rate_limit_delay)
            if resp.status_code != 200:
                return None
            data = resp.json()
            vulns = data.get("vulnerabilities", [])
            return self._parse_cve(vulns[0]) if vulns else None
        except Exception as e:
            logger.error(f"NVD fetch failed for {cve_id}: {e}")
            return None

    def search_by_keyword(self, keyword: str, limit: int = 10) -> List[Dict]:
        """Search CVEs by keyword (product, service)."""
        try:
            resp = httpx.get(
                NVD_BASE_URL,
                params={"keywordSearch": keyword, "resultsPerPage": limit},
                headers=self._headers(),
                timeout=15,
            )
            time.sleep(self.rate_limit_delay)
            if resp.status_code != 200:
                return []
            data = resp.json()
            return [self._parse_cve(v) for v in data.get("vulnerabilities", [])]
        except Exception as e:
            logger.error(f"NVD search failed for '{keyword}': {e}")
            return []

    def get_recent(self, days: int = 7, limit: int = 100) -> List[Dict]:
        """CVEs published in the last N days."""
        since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S.000")
        now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000")
        try:
            resp = httpx.get(
                NVD_BASE_URL,
                params={"pubStartDate": since, "pubEndDate": now, "resultsPerPage": limit},
                headers=self._headers(),
                timeout=30,
            )
            time.sleep(self.rate_limit_delay)
            if resp.status_code != 200:
                return []
            return [self._parse_cve(v) for v in resp.json().get("vulnerabilities", [])]
        except Exception as e:
            logger.error(f"NVD recent fetch failed: {e}")
            return []

    def _parse_cve(self, vuln: Dict) -> Dict:
        cve = vuln.get("cve", {})
        cve_id = cve.get("id", "")

        # Description in English
        desc = next(
            (d["value"] for d in cve.get("descriptions", []) if d.get("lang") == "en"),
            "",
        )

        # CVSS scores
        cvss_v3_score = None
        cvss_v3_vector = None
        cvss_v2_score = None
        severity = None

        metrics = cve.get("metrics", {})
        if "cvssMetricV31" in metrics:
            m = metrics["cvssMetricV31"][0]
            cvss_v3_score = m.get("cvssData", {}).get("baseScore")
            cvss_v3_vector = m.get("cvssData", {}).get("vectorString")
            severity = m.get("cvssData", {}).get("baseSeverity", "").lower()
        elif "cvssMetricV30" in metrics:
            m = metrics["cvssMetricV30"][0]
            cvss_v3_score = m.get("cvssData", {}).get("baseScore")
            severity = m.get("cvssData", {}).get("baseSeverity", "").lower()
        if "cvssMetricV2" in metrics:
            cvss_v2_score = metrics["cvssMetricV2"][0].get("cvssData", {}).get("baseScore")

        # CPEs (affected products)
        affected = []
        for config in cve.get("configurations", []):
            for node in config.get("nodes", []):
                for match in node.get("cpeMatch", []):
                    if match.get("vulnerable"):
                        affected.append(match.get("criteria", ""))

        # References
        refs = [r.get("url") for r in cve.get("references", []) if r.get("url")]

        # CWEs
        cwes = []
        for w in cve.get("weaknesses", []):
            descs = w.get("description", [])
            if descs:
                cwes.append(descs[0].get("value", ""))

        return {
            "cve_id":             cve_id,
            "description":        desc,
            "cvss_v3_score":      cvss_v3_score,
            "cvss_v3_vector":     cvss_v3_vector,
            "cvss_v2_score":      cvss_v2_score,
            "severity":           severity,
            "cwe_ids":            [c for c in cwes if c],
            "affected_products":  affected[:20],
            "references":         refs[:10],
            "published_at":       cve.get("published"),
            "modified_at":        cve.get("lastModified"),
        }
