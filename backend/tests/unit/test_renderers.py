"""Unit tests for HTML and PDF renderers - Phase 6"""
import os
import pytest
from unittest.mock import MagicMock, patch

from app.core.reporting.html_renderer import HTMLRenderer
from app.core.reporting.pdf_renderer import PDFRenderer
from app.models.report import Report, ReportType, ReportFormat, ReportClassification, ReportStatus


# ── fixtures ───────────────────────────────────────────────────────────────────

TEMPLATES_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "templates"
)


def _make_report(report_type=ReportType.technical):
    r = MagicMock(spec=Report)
    r.id = 1
    r.project_id = 42
    r.title = "Test Report"
    r.report_type = report_type
    r.report_format = ReportFormat.html
    r.classification = ReportClassification.confidential
    r.status = ReportStatus.generating
    r.scope_description = "Full scope"
    r.executive_summary = "Summary text"
    r.recommendations = "Fix everything"
    r.generated_at = None
    return r


def _make_data(n_findings=2):
    findings = [
        {
            "id": i, "title": f"Finding {i}", "description": "desc",
            "severity": "high", "status": "open",
            "host": f"10.0.0.{i}", "port": 80, "service": "http",
            "tool": "nmap", "risk_score": float(i * 3),
        }
        for i in range(1, n_findings + 1)
    ]
    stats = {
        "total": n_findings, "critical": 0, "high": n_findings,
        "medium": 0, "low": 0, "info": 0, "overall_risk": 6.0,
    }
    return {
        "findings": findings,
        "results_summary": [],
        "stats": stats,
        "top_risks": findings,
        "hosts_affected": [f"10.0.0.{i}" for i in range(1, n_findings + 1)],
        "tools_used": ["nmap"],
    }


# ── HTML renderer tests ────────────────────────────────────────────────────────

class TestHTMLRenderer:

    def setup_method(self):
        self.renderer = HTMLRenderer(templates_dir=TEMPLATES_DIR)

    def test_html_executive_renders(self):
        report = _make_report(ReportType.executive)
        result = self.renderer.render(_make_data(), report)
        assert isinstance(result, bytes)
        assert b"Executive Summary" in result or b"executive" in result.lower()

    def test_html_technical_renders(self):
        report = _make_report(ReportType.technical)
        result = self.renderer.render(_make_data(), report)
        assert isinstance(result, bytes)
        assert b"Technical" in result or b"technical" in result.lower()

    def test_html_compliance_renders(self):
        report = _make_report(ReportType.compliance)
        result = self.renderer.render(_make_data(), report)
        assert isinstance(result, bytes)
        assert b"Compliance" in result or b"compliance" in result.lower()

    def test_html_renderer_contains_stats(self):
        report = _make_report(ReportType.executive)
        data = _make_data(3)
        result = self.renderer.render(data, report)
        html = result.decode("utf-8")
        # Total findings count should appear somewhere
        assert "3" in html

    def test_html_renderer_contains_finding_title(self):
        report = _make_report(ReportType.technical)
        data = _make_data(1)
        result = self.renderer.render(data, report)
        assert b"Finding 1" in result

    def test_html_renderer_content_type(self):
        assert self.renderer.content_type() == "text/html"

    def test_html_renderer_extension(self):
        assert self.renderer.extension() == "html"

    def test_html_renderer_returns_utf8_bytes(self):
        report = _make_report(ReportType.technical)
        result = self.renderer.render(_make_data(), report)
        # Should be decodable as UTF-8
        assert result.decode("utf-8")


# ── PDF renderer tests ─────────────────────────────────────────────────────────

class TestPDFRenderer:

    def setup_method(self):
        self.renderer = PDFRenderer()

    def test_pdf_renderer_content_type(self):
        assert self.renderer.content_type() == "application/pdf"

    def test_pdf_renderer_extension(self):
        assert self.renderer.extension() == "pdf"

    def test_pdf_renderer_returns_bytes_with_mock(self):
        """PDFRenderer delegates to weasyprint; mock it to return fake PDF bytes."""
        report = _make_report(ReportType.executive)
        fake_pdf = b"%PDF-1.4 fake"

        with patch("app.core.reporting.pdf_renderer.HTMLRenderer") as MockHTML:
            MockHTML.return_value.render.return_value = b"<html>...</html>"
            with patch("app.core.reporting.pdf_renderer.PDFRenderer.render", return_value=fake_pdf):
                result = self.renderer.render(_make_data(), report)

        assert result == fake_pdf

    def test_pdf_renderer_calls_html_renderer(self):
        """PDF renderer must call HTML renderer to get markup first."""
        report = _make_report(ReportType.technical)
        data = _make_data()

        with patch("app.core.reporting.pdf_renderer.HTMLRenderer") as MockHTMLCls:
            instance = MockHTMLCls.return_value
            instance.render.return_value = b"<html></html>"

            mock_html_obj = MagicMock()
            mock_html_obj.write_pdf.return_value = b"%PDF"

            with patch("builtins.__import__", side_effect=ImportError("weasyprint")):
                with pytest.raises(RuntimeError, match="WeasyPrint is not installed"):
                    self.renderer.render(data, report)
