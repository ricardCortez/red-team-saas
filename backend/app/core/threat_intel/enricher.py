"""Finding enricher with CVE, MITRE and IOC data - Phase 12"""
import re
import logging
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session

from app.models.finding import Finding
from app.models.cve import CVE
from app.models.mitre_technique import MitreTechnique
from app.models.ioc import IOC
from app.core.threat_intel.nvd_client import NVDClient
from app.core.config import settings

logger = logging.getLogger(__name__)

CVE_PATTERN = re.compile(r"CVE-\d{4}-\d{4,7}", re.IGNORECASE)


class FindingEnricher:

    def __init__(self, db: Session):
        self.db = db
        self.nvd = NVDClient(api_key=getattr(settings, "NVD_API_KEY", None))

    def enrich_finding(self, finding: Finding) -> Dict[str, Any]:
        """
        Enrich a finding with CVE, MITRE and IOC data.
        Returns dict with aggregated intel.
        """
        intel: Dict[str, Any] = {
            "cves":             [],
            "mitre_techniques": [],
            "ioc_matches":      [],
            "risk_adjustment":  0.0,
        }

        # 1. Extract CVE IDs from title/description
        text = f"{finding.title} {finding.description or ''}"
        cve_ids = list(set(CVE_PATTERN.findall(text)))

        for cve_id in cve_ids[:5]:
            cve = self._get_or_fetch_cve(cve_id.upper())
            if not cve:
                continue

            intel["cves"].append({
                "cve_id":      cve.cve_id,
                "cvss_v3":     cve.cvss_v3_score,
                "severity":    cve.severity,
                "is_kev":      cve.is_kev,
                "description": (cve.description or "")[:300],
            })

            # Adjust risk score for critical CVEs
            if cve.cvss_v3_score and cve.cvss_v3_score >= 9.0:
                intel["risk_adjustment"] = max(intel["risk_adjustment"], 1.5)
            if cve.is_kev:
                intel["risk_adjustment"] = max(intel["risk_adjustment"], 2.0)

            # Pull MITRE techniques linked to this CVE
            for tech_id in (cve.mitre_techniques or []):
                if tech_id in [t["technique_id"] for t in intel["mitre_techniques"]]:
                    continue
                tech = self.db.query(MitreTechnique).filter(
                    MitreTechnique.technique_id == tech_id
                ).first()
                if tech:
                    intel["mitre_techniques"].append({
                        "technique_id": tech.technique_id,
                        "name":         tech.name,
                        "tactic":       tech.tactic_name,
                    })

        # 2. Check IOC match on finding host
        if finding.host:
            ioc = self.db.query(IOC).filter(
                IOC.value == finding.host,
                IOC.is_active == True,  # noqa: E712
            ).first()
            if ioc:
                intel["ioc_matches"].append({
                    "value":        ioc.value,
                    "type":         ioc.ioc_type.value,
                    "threat_level": ioc.threat_level.value,
                    "source":       ioc.source,
                    "confidence":   ioc.confidence,
                })
                intel["risk_adjustment"] = max(intel["risk_adjustment"], 1.0)

        return intel

    def _get_or_fetch_cve(self, cve_id: str) -> Optional[CVE]:
        """Check local DB first, then fetch from NVD."""
        cve = self.db.query(CVE).filter(CVE.cve_id == cve_id).first()
        if cve:
            return cve

        data = self.nvd.get_cve(cve_id)
        if not data:
            return None

        cve = CVE(**{k: v for k, v in data.items() if hasattr(CVE, k)})
        self.db.add(cve)
        try:
            self.db.commit()
            self.db.refresh(cve)
        except Exception:
            self.db.rollback()
            cve = self.db.query(CVE).filter(CVE.cve_id == cve_id).first()
        return cve
