"""Report Generator Service — Phase 14

Orchestrates multi-format report rendering (PDF, HTML, Excel) using
Jinja2 templates and existing renderer infrastructure.
"""
import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session

from app.models.compliance import ComplianceMappingResult
from app.models.finding import Finding, FindingStatus
from app.models.report import (
    ReportTemplate,
    ReportV2,
    ReportStatusV2,
    ReportTypeV2,
)

logger = logging.getLogger(__name__)

# Templates live at backend/templates/reports/
import os
_TEMPLATES_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "templates", "reports"
)


class ReportGenerator:
    """Creates ReportV2 records and renders PDF/HTML/Excel content."""

    def __init__(self, db: Session, templates_dir: str = None):
        self.db = db
        tdir = os.path.abspath(templates_dir or _TEMPLATES_DIR)
        self.env = Environment(
            loader=FileSystemLoader(tdir),
            autoescape=select_autoescape(["html"]),
        )

    # ── Public API ──────────────────────────────────────────────────────────

    def generate_report(
        self,
        project_id: int,
        report_type: str,
        title: str,
        generated_by: Optional[int],
        template_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        compliance_mapping_id: Optional[int] = None,
        custom_variables: Optional[Dict] = None,
    ) -> ReportV2:
        """Create a ReportV2 record with summary metadata."""
        from app.models.project import Project

        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        template = None
        if template_id:
            template = self.db.query(ReportTemplate).filter(
                ReportTemplate.id == template_id
            ).first()

        findings = self._query_findings(project_id, start_date, end_date)
        summary = self._calculate_summary(findings, compliance_mapping_id)

        report = ReportV2(
            project_id=project_id,
            template_id=template_id,
            title=title,
            report_type=report_type,
            generated_by=generated_by,
            start_date=start_date or project.created_at,
            end_date=end_date or datetime.utcnow(),
            findings_count=len(findings),
            compliance_mapping_id=compliance_mapping_id,
            summary_metadata=summary,
            status=ReportStatusV2.draft,
            included_sections=self._get_included_sections(template, findings),
        )

        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def render_pdf(
        self,
        report: ReportV2,
        findings: List[Finding],
        custom_variables: Optional[Dict] = None,
    ) -> bytes:
        """Render report to PDF via WeasyPrint."""
        try:
            from weasyprint import HTML as WPHtml
        except ImportError:
            raise RuntimeError(
                "WeasyPrint not installed. Run: pip install weasyprint"
            )

        html_str = self._render_html_str(report, findings, custom_variables, include_charts=False)
        return WPHtml(string=html_str).write_pdf()

    def render_html(
        self,
        report: ReportV2,
        findings: List[Finding],
        custom_variables: Optional[Dict] = None,
        include_charts: bool = True,
    ) -> bytes:
        """Render report to HTML with optional Chart.js charts."""
        html = self._render_html_str(report, findings, custom_variables, include_charts)
        return html.encode("utf-8")

    def render_excel(
        self,
        report: ReportV2,
        findings: List[Finding],
        custom_variables: Optional[Dict] = None,
    ) -> bytes:
        """Render report to Excel (.xlsx) with multiple sheets."""
        from app.core.reporting.excel_renderer import ExcelRenderer
        renderer = ExcelRenderer()
        return renderer.render(report, findings)

    # ── Private helpers ─────────────────────────────────────────────────────

    def _render_html_str(
        self,
        report: ReportV2,
        findings: List[Finding],
        custom_variables: Optional[Dict],
        include_charts: bool,
    ) -> str:
        try:
            template_obj = self.env.get_template("report_base.html")
        except Exception:
            # Fallback to inline minimal template if file not found
            return self._fallback_html(report, findings)

        compliance_data: Dict[str, Any] = {}
        if report.compliance_mapping:
            compliance_data = {
                "score": report.compliance_mapping.compliance_score,
                "status": report.compliance_mapping.compliance_status,
            }

        context = {
            "report": {
                "title": report.title,
                "description": report.description or "",
                "generated_at": report.generated_at.isoformat() if report.generated_at else "",
                "project": report.project.name if report.project else str(report.project_id),
                "findings_count": report.findings_count,
            },
            "summary": report.summary_metadata or {},
            "findings": self._format_findings(findings),
            "compliance": compliance_data,
            "charts_enabled": include_charts,
            **(custom_variables or {}),
        }
        return template_obj.render(context)

    def _fallback_html(self, report: ReportV2, findings: List[Finding]) -> str:
        rows = "".join(
            f"<tr><td>{f.title}</td><td>{f.severity.value if hasattr(f.severity,'value') else f.severity}</td></tr>"
            for f in findings
        )
        return (
            f"<html><body><h1>{report.title}</h1>"
            f"<p>Findings: {report.findings_count}</p>"
            f"<table><tr><th>Title</th><th>Severity</th></tr>{rows}</table>"
            f"</body></html>"
        )

    def _query_findings(
        self,
        project_id: int,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
    ) -> List[Finding]:
        q = self.db.query(Finding).filter(
            Finding.project_id == project_id,
            Finding.is_duplicate == False,  # noqa: E712
            Finding.status != FindingStatus.false_positive,
        )
        return q.order_by(Finding.severity).all()

    def _calculate_summary(
        self, findings: List[Finding], compliance_mapping_id: Optional[int]
    ) -> Dict[str, Any]:
        severity_counts: Dict[str, int] = {
            "critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0
        }
        by_tool: Dict[str, int] = {}

        for f in findings:
            sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
            tool = f.tool_name or "unknown"
            by_tool[tool] = by_tool.get(tool, 0) + 1

        summary: Dict[str, Any] = {
            "total_findings": len(findings),
            **severity_counts,
            "by_tool": by_tool,
        }

        if compliance_mapping_id:
            result = self.db.query(ComplianceMappingResult).filter(
                ComplianceMappingResult.id == compliance_mapping_id
            ).first()
            if result:
                summary["compliance_score"] = result.compliance_score
                summary["compliance_status"] = result.compliance_status.value if hasattr(result.compliance_status, "value") else str(result.compliance_status)
                summary["compliance_met"] = result.met_requirements
                summary["compliance_total"] = result.total_requirements

        return summary

    def _get_included_sections(
        self, template: Optional[ReportTemplate], findings: List[Finding]
    ) -> List[Dict]:
        if not template or not template.sections:
            return [
                {"name": "Executive Summary", "items_count": 1},
                {"name": "Findings", "items_count": len(findings)},
            ]
        included = []
        for section in template.sections:
            if section.get("include_by_default", True):
                count = len(findings) if section.get("name") == "Findings" else 1
                included.append({"name": section["name"], "items_count": count})
        return included

    def _format_findings(self, findings: List[Finding]) -> List[Dict]:
        result = []
        for f in findings:
            result.append({
                "title": f.title,
                "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                "cve_ids": getattr(f, "cve_ids", None),
                "description": f.description or "",
                "remediation": getattr(f, "remediation", "") or "",
                "tool": f.tool_name or "",
                "host": f.host or "",
                "risk_score": f.risk_score or 0.0,
            })
        return result
