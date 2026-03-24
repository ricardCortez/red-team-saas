"""Data aggregation layer for report generation"""
from typing import Dict, Any, List

from sqlalchemy.orm import Session

from app.models.finding import Finding, Severity, FindingStatus
from app.models.result import Result
from app.models.task import Task


class ReportDataAggregator:

    def __init__(self, db: Session, project_id: int):
        self.db = db
        self.project_id = project_id

    def aggregate(self) -> Dict[str, Any]:
        findings = self._get_findings()
        results = self._get_results()
        stats = self._compute_stats(findings)
        return {
            "findings": findings,
            "results_summary": results,
            "stats": stats,
            "top_risks": self._top_risks(findings),
            "hosts_affected": self._hosts_affected(findings),
            "tools_used": self._tools_used(results),
        }

    # ── private helpers ────────────────────────────────────────────────────────

    def _get_findings(self) -> List[Dict]:
        rows = (
            self.db.query(Finding)
            .filter(
                Finding.project_id == self.project_id,
                Finding.is_duplicate == False,  # noqa: E712
                Finding.status != FindingStatus.false_positive,
            )
            .order_by(Finding.severity, Finding.risk_score.desc())
            .all()
        )
        return [
            {
                "id": f.id,
                "title": f.title,
                "description": f.description,
                "severity": f.severity.value,
                "status": f.status.value,
                "host": f.host,
                "port": f.port,
                "service": f.service,
                "tool": f.tool_name,
                "risk_score": f.risk_score or 0.0,
            }
            for f in rows
        ]

    def _get_results(self) -> List[Dict]:
        rows = (
            self.db.query(Result)
            .join(Task, Result.task_id == Task.id)
            .filter(Task.project_id == self.project_id)
            .all()
        )
        return [
            {
                "tool": r.tool_name or r.tool,
                "target": r.target,
                "success": r.success,
                "risk": r.risk_score,
                "duration": r.duration_seconds,
            }
            for r in rows
        ]

    def _compute_stats(self, findings: List[Dict]) -> Dict:
        counts: Dict[str, int] = {s.value: 0 for s in Severity}
        for f in findings:
            sev = f["severity"]
            counts[sev] = counts.get(sev, 0) + 1

        risk_scores = [f["risk_score"] for f in findings if f["risk_score"] > 0]
        overall = max(risk_scores) if risk_scores else 0.0

        return {
            "total": len(findings),
            "critical": counts.get("critical", 0),
            "high": counts.get("high", 0),
            "medium": counts.get("medium", 0),
            "low": counts.get("low", 0),
            "info": counts.get("info", 0),
            "overall_risk": round(overall, 2),
        }

    def _top_risks(self, findings: List[Dict], n: int = 10) -> List[Dict]:
        return sorted(findings, key=lambda x: x["risk_score"], reverse=True)[:n]

    def _hosts_affected(self, findings: List[Dict]) -> List[str]:
        return list({f["host"] for f in findings if f["host"]})

    def _tools_used(self, results: List[Dict]) -> List[str]:
        return list({r["tool"] for r in results if r["tool"]})
