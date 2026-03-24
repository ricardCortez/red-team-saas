"""HTML renderer using Jinja2 templates"""
import os
from typing import Dict, Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.reporting.base_renderer import BaseRenderer
from app.models.report import ReportType

TEMPLATE_MAP = {
    ReportType.executive: "executive_summary.html",
    ReportType.technical: "technical_report.html",
    ReportType.compliance: "compliance_report.html",
}

# templates/ lives at backend/templates/ (3 levels up from this file)
_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "templates")


class HTMLRenderer(BaseRenderer):

    def __init__(self, templates_dir: str = None):
        tdir = templates_dir or _TEMPLATES_DIR
        self.env = Environment(
            loader=FileSystemLoader(os.path.abspath(tdir)),
            autoescape=select_autoescape(["html"]),
        )

    def render(self, data: Dict[str, Any], report) -> bytes:
        template_name = TEMPLATE_MAP.get(report.report_type, "technical_report.html")
        template = self.env.get_template(template_name)
        html = template.render(
            report=report,
            data=data,
            findings=data["findings"],
            stats=data["stats"],
            top_risks=data["top_risks"],
            hosts=data["hosts_affected"],
            tools=data["tools_used"],
        )
        return html.encode("utf-8")

    def content_type(self) -> str:
        return "text/html"

    def extension(self) -> str:
        return "html"
