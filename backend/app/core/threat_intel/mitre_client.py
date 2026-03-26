"""MITRE ATT&CK STIX client - Phase 12"""
import httpx
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

MITRE_ENTERPRISE_URL = (
    "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"
)

TACTIC_MAP = {
    "reconnaissance":       "Reconnaissance",
    "resource-development": "Resource Development",
    "initial-access":       "Initial Access",
    "execution":            "Execution",
    "persistence":          "Persistence",
    "privilege-escalation": "Privilege Escalation",
    "defense-evasion":      "Defense Evasion",
    "credential-access":    "Credential Access",
    "discovery":            "Discovery",
    "lateral-movement":     "Lateral Movement",
    "collection":           "Collection",
    "command-and-control":  "Command and Control",
    "exfiltration":         "Exfiltration",
    "impact":               "Impact",
}


class MITREClient:

    def fetch_techniques(self) -> List[Dict]:
        """Download and parse all Enterprise ATT&CK techniques."""
        try:
            resp = httpx.get(MITRE_ENTERPRISE_URL, timeout=60)
            if resp.status_code != 200:
                return []
            bundle = resp.json()
            return self._parse_techniques(bundle)
        except Exception as e:
            logger.error(f"MITRE fetch failed: {e}")
            return []

    def _parse_techniques(self, bundle: Dict) -> List[Dict]:
        techniques = []
        objects = bundle.get("objects", [])

        for obj in objects:
            if obj.get("type") != "attack-pattern":
                continue
            if obj.get("revoked") or obj.get("x_mitre_deprecated"):
                continue

            ext_refs = obj.get("external_references", [])
            tech_id = next(
                (r.get("external_id") for r in ext_refs if r.get("source_name") == "mitre-attack"),
                None,
            )
            if not tech_id:
                continue

            url = next(
                (r.get("url") for r in ext_refs if r.get("source_name") == "mitre-attack"),
                None,
            )

            kill_chain = obj.get("kill_chain_phases", [])
            tactic = kill_chain[0].get("phase_name") if kill_chain else None
            tactic_name = TACTIC_MAP.get(tactic, tactic)

            is_sub = "." in tech_id
            parent_id = tech_id.split(".")[0] if is_sub else None
            platforms = obj.get("x_mitre_platforms", [])

            techniques.append({
                "technique_id":    tech_id,
                "name":            obj.get("name", ""),
                "tactic":          tactic,
                "tactic_name":     tactic_name,
                "description":     (obj.get("description", "") or "")[:2000],
                "is_subtechnique": is_sub,
                "parent_id":       parent_id,
                "platforms":       platforms,
                "detection":       (obj.get("x_mitre_detection", "") or "")[:1000],
                "url":             url,
            })

        return techniques
