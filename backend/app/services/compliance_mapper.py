"""Compliance mapping engine - Phase 13

Maps project findings against compliance framework requirements and produces
an immutable ComplianceMappingResult with evidence logs.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.crud.compliance import ComplianceCRUD
from app.models.compliance import (
    ComplianceEvidenceLog,
    ComplianceMappingResult,
    ComplianceRequirement,
    ComplianceStatus,
    EvidenceStatus,
)
from app.models.finding import Finding

logger = logging.getLogger(__name__)


class ComplianceMapper:

    def __init__(self, db: Session):
        self.db = db

    # ── Public API ─────────────────────────────────────────────────────────────

    def assess_project(
        self,
        project_id: int,
        framework_type: str,
        findings: List[Finding],
        assessment_period: Optional[str] = None,
    ) -> ComplianceMappingResult:
        """
        Map findings against a compliance framework.
        Returns a persisted ComplianceMappingResult.
        """
        framework = ComplianceCRUD.get_framework_by_type(self.db, framework_type)
        if not framework:
            raise ValueError(f"Framework '{framework_type}' not found. "
                             "Run seed_compliance_frameworks() first.")

        requirements = ComplianceCRUD.get_requirements_by_framework(self.db, framework.id)

        evaluation: Dict[str, Any] = {
            "total": len(requirements),
            "met": 0,
            "non_met": 0,
            "partial": 0,
            "not_applicable": 0,
            "evidence": [],
        }

        for req in requirements:
            status, matched = self._evaluate_requirement(req, findings)
            evaluation["evidence"].append({
                "requirement_id": req.requirement_id,
                "status":         status,
                "findings":       matched,
            })
            if status == EvidenceStatus.MET:
                evaluation["met"] += 1
            elif status == EvidenceStatus.NON_MET:
                evaluation["non_met"] += 1
            elif status == EvidenceStatus.PARTIAL:
                evaluation["partial"] += 1
            else:
                evaluation["not_applicable"] += 1

        score  = self._calculate_compliance_score(evaluation)
        status = self._determine_compliance_status(score)

        mapping_result = ComplianceMappingResult(
            project_id              = project_id,
            framework_id            = framework.id,
            assessment_period       = assessment_period,
            total_requirements      = evaluation["total"],
            met_requirements        = evaluation["met"],
            non_met_requirements    = evaluation["non_met"],
            partial_met_requirements = evaluation["partial"],
            not_applicable          = evaluation["not_applicable"],
            compliance_score        = score,
            compliance_status       = status,
            audit_findings          = [
                {
                    "requirement_id": e["requirement_id"],
                    "status":         e["status"].value if hasattr(e["status"], "value") else e["status"],
                    "finding_count":  len(e["findings"]),
                }
                for e in evaluation["evidence"]
            ],
            evidence_metadata = {
                "assessment_tool":   "compliance_engine",
                "framework_version": framework.version,
                "total_findings":    len(findings),
            },
        )
        self.db.add(mapping_result)
        self.db.commit()
        self.db.refresh(mapping_result)

        self._create_evidence_logs(mapping_result, evaluation)
        return mapping_result

    # ── Score / Status helpers ─────────────────────────────────────────────────

    def _calculate_compliance_score(self, evaluation: Dict[str, Any]) -> int:
        """Score 0-100: met/total minus penalty for non_met."""
        total = evaluation["total"]
        if total == 0:
            return 100
        base    = (evaluation["met"] / total) * 100
        penalty = (evaluation["non_met"] / total) * 30
        return max(0, int(base - penalty))

    def _determine_compliance_status(self, score: int) -> ComplianceStatus:
        if score >= 85:
            return ComplianceStatus.COMPLIANT
        elif score >= 50:
            return ComplianceStatus.PARTIAL
        return ComplianceStatus.NON_COMPLIANT

    # ── Requirement evaluation ─────────────────────────────────────────────────

    def _evaluate_requirement(
        self, requirement: ComplianceRequirement, findings: List[Finding]
    ) -> Tuple[EvidenceStatus, List[Finding]]:
        """
        Evaluate a single requirement against the finding list.
        Returns (EvidenceStatus, matched_findings).
        """
        related: List[Finding] = []

        patterns = requirement.related_cve_patterns or []
        tool_map = requirement.tool_mappings or {}

        for finding in findings:
            # Check CVE/CWE patterns
            for cve_id in self._extract_cve_ids(finding):
                for pattern in patterns:
                    if self._matches_pattern(cve_id, pattern):
                        if finding not in related:
                            related.append(finding)
                        break

            # Check tool mappings
            finding_tool = finding.tool or finding.tool_name or ""
            if finding_tool in tool_map:
                # We match on tool presence; issue_type not available on model
                if finding not in related:
                    related.append(finding)

        if not related:
            return EvidenceStatus.NOT_APPLICABLE, []

        # Findings with critical/high severity → NON_MET
        severe = [
            f for f in related
            if hasattr(f.severity, "value") and f.severity.value in ("critical", "high")
            or (isinstance(f.severity, str) and f.severity.lower() in ("critical", "high"))
        ]
        if severe:
            return EvidenceStatus.NON_MET, related
        if len(related) > 3:
            return EvidenceStatus.PARTIAL, related
        return EvidenceStatus.MET, related

    def _extract_cve_ids(self, finding: Finding) -> List[str]:
        """Parse the cve_ids JSON text field into a list of strings."""
        if not finding.cve_ids:
            return []
        try:
            parsed = json.loads(finding.cve_ids)
            if isinstance(parsed, list):
                return [str(c) for c in parsed]
            return [str(parsed)]
        except (json.JSONDecodeError, TypeError):
            return [str(finding.cve_ids)]

    def _matches_pattern(self, cve_id: str, pattern: str) -> bool:
        """Simple prefix match; '*' is treated as wildcard suffix."""
        if not cve_id:
            return False
        prefix = pattern.rstrip("*")
        return cve_id.startswith(prefix)

    # ── Evidence log creation ──────────────────────────────────────────────────

    def _create_evidence_logs(
        self,
        mapping_result: ComplianceMappingResult,
        evaluation: Dict[str, Any],
    ) -> None:
        """Persist evidence logs for each requirement/finding pair."""
        for entry in evaluation["evidence"]:
            req_id  = entry["requirement_id"]
            status  = entry["status"]
            matched = entry["findings"]

            if not matched:
                # Create a single NOT_APPLICABLE entry without a finding
                log = ComplianceEvidenceLog(
                    mapping_result_id   = mapping_result.id,
                    requirement_id      = req_id,
                    finding_id          = None,
                    status              = status,
                    evidence_text       = "No related findings identified.",
                    proof_of_compliance = {},
                )
                self.db.add(log)
                continue

            for finding in matched:
                log = ComplianceEvidenceLog(
                    mapping_result_id   = mapping_result.id,
                    requirement_id      = req_id,
                    finding_id          = finding.id,
                    status              = status,
                    evidence_text       = (
                        f"Finding: {finding.title} "
                        f"(Severity: {finding.severity.value if hasattr(finding.severity, 'value') else finding.severity})"
                    ),
                    proof_of_compliance = {
                        "tool":           finding.tool or finding.tool_name,
                        "timestamp":      finding.created_at.isoformat() if finding.created_at else None,
                        "output_snippet": (finding.description or "")[:200],
                    },
                )
                self.db.add(log)

        self.db.commit()
