"""Threat correlation: CVE ↔ MITRE ↔ IOC - Phase 12"""
import re
import logging
from typing import List, Dict, Optional

from sqlalchemy.orm import Session

from app.models.cve import CVE
from app.models.mitre_technique import MitreTechnique
from app.models.ioc import IOC

logger = logging.getLogger(__name__)

CVE_PATTERN = re.compile(r"CVE-\d{4}-\d{4,7}", re.IGNORECASE)


class ThreatCorrelator:

    def __init__(self, db: Session):
        self.db = db

    def cve_to_mitre(self, cve_id: str) -> List[Dict]:
        """Return MITRE techniques associated with a CVE."""
        cve = self.db.query(CVE).filter(CVE.cve_id == cve_id).first()
        if not cve or not cve.mitre_techniques:
            return []
        techs = self.db.query(MitreTechnique).filter(
            MitreTechnique.technique_id.in_(cve.mitre_techniques)
        ).all()
        return [
            {"technique_id": t.technique_id, "name": t.name, "tactic": t.tactic_name}
            for t in techs
        ]

    def mitre_to_cves(self, technique_id: str) -> List[Dict]:
        """CVEs that use this MITRE technique (Python-side filter for portability)."""
        candidates = self.db.query(CVE).filter(CVE.mitre_techniques.isnot(None)).all()
        matching = [
            c for c in candidates
            if technique_id in (c.mitre_techniques or [])
        ]
        matching.sort(key=lambda c: c.cvss_v3_score or 0.0, reverse=True)
        return [
            {"cve_id": c.cve_id, "cvss_v3": c.cvss_v3_score, "severity": c.severity}
            for c in matching[:20]
        ]

    def check_ioc(self, value: str) -> Optional[Dict]:
        """Check if a value is a known active IOC."""
        ioc = self.db.query(IOC).filter(
            IOC.value == value,
            IOC.is_active == True,  # noqa: E712
        ).first()
        if not ioc:
            return None
        return {
            "value":        ioc.value,
            "type":         ioc.ioc_type.value,
            "threat_level": ioc.threat_level.value,
            "source":       ioc.source,
            "confidence":   ioc.confidence,
            "description":  ioc.description,
            "tags":         ioc.tags,
        }

    def project_threat_profile(self, project_id: int) -> Dict:
        """Full threat profile for a project."""
        from app.models.finding import Finding, FindingStatus

        findings = self.db.query(Finding).filter(
            Finding.project_id == project_id,
            Finding.is_duplicate == False,  # noqa: E712
            Finding.status != FindingStatus.false_positive,
        ).all()

        # Collect unique CVE IDs across all findings
        all_cves: set = set()
        for f in findings:
            text = f"{f.title} {f.description or ''}"
            all_cves.update(CVE_PATTERN.findall(text))

        upper_cves = [c.upper() for c in all_cves]

        kev_count = self.db.query(CVE).filter(
            CVE.cve_id.in_(upper_cves),
            CVE.is_kev == True,  # noqa: E712
        ).count() if upper_cves else 0

        critical_cves = self.db.query(CVE).filter(
            CVE.cve_id.in_(upper_cves),
            CVE.cvss_v3_score >= 9.0,
        ).count() if upper_cves else 0

        # Collect MITRE techniques via cached CVE records
        all_techniques: set = set()
        if upper_cves:
            cve_records = self.db.query(CVE).filter(CVE.cve_id.in_(upper_cves)).all()
            for cve in cve_records:
                if cve.mitre_techniques:
                    all_techniques.update(cve.mitre_techniques)

        tactics: Dict[str, int] = {}
        for tid in all_techniques:
            tech = self.db.query(MitreTechnique).filter(
                MitreTechnique.technique_id == tid
            ).first()
            if tech and tech.tactic_name:
                tactics[tech.tactic_name] = tactics.get(tech.tactic_name, 0) + 1

        return {
            "total_cves":       len(all_cves),
            "kev_count":        kev_count,
            "critical_cves":    critical_cves,
            "mitre_techniques": len(all_techniques),
            "tactics_coverage": tactics,
        }
