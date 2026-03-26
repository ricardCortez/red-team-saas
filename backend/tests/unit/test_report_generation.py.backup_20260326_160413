"""Unit tests for Phase 14 Report Generation Engine.

Tests cover:
- ReportGenerator: summary calculation, section detection, HTML/Excel rendering
- DigitalSignatureManager: self-signed cert generation, signing, verification
- CRUDReportV2: CRUD operations, audit logging, version management
- ExcelRenderer: workbook sheet structure
- ReportSchedule: cron dispatch logic
"""
import hashlib
import json
from datetime import datetime, timedelta
from io import BytesIO
from typing import List
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ── Fixtures ───────────────────────────────────────────────────────────────────

def _make_finding(
    title="SQL Injection",
    severity="critical",
    host="192.168.1.1",
    tool_name="sqlmap",
    risk_score=9.5,
    description="SQLi in login form",
    remediation="Use parameterised queries",
    is_duplicate=False,
    status="open",
):
    f = MagicMock()
    f.title = title
    f.severity = MagicMock()
    f.severity.value = severity
    f.host = host
    f.tool_name = tool_name
    f.risk_score = risk_score
    f.description = description
    f.remediation = remediation
    f.is_duplicate = is_duplicate
    f.status = MagicMock()
    f.status.value = status
    f.cve_ids = []
    f.port = 443
    f.service = "https"
    return f


def _make_report(
    id=1,
    project_id=10,
    title="Test Report",
    findings_count=3,
    summary_metadata=None,
    report_type="penetration_test",
    generated_at=None,
    status="draft",
    compliance_mapping=None,
    project_name="TestProject",
):
    r = MagicMock()
    r.id = id
    r.project_id = project_id
    r.title = title
    r.findings_count = findings_count
    r.summary_metadata = summary_metadata or {
        "total_findings": 3, "critical": 1, "high": 1, "medium": 1, "low": 0, "info": 0
    }
    r.report_type = report_type
    r.generated_at = generated_at or datetime(2026, 3, 26, 12, 0, 0)
    r.description = "Test description"
    r.status = status
    r.compliance_mapping = compliance_mapping
    r.project = MagicMock()
    r.project.name = project_name
    r.project.created_at = datetime(2026, 1, 1)
    return r


# ── ReportGenerator ────────────────────────────────────────────────────────────

class TestReportGeneratorSummary:

    def _make_generator(self):
        from app.services.report_generator import ReportGenerator
        db = MagicMock()
        gen = ReportGenerator.__new__(ReportGenerator)
        gen.db = db
        return gen

    def test_calculate_summary_counts_severities(self):
        from app.services.report_generator import ReportGenerator
        gen = self._make_generator()

        findings = [
            _make_finding(severity="critical"),
            _make_finding(severity="high"),
            _make_finding(severity="high"),
            _make_finding(severity="medium"),
            _make_finding(severity="low"),
        ]

        summary = gen._calculate_summary(findings, compliance_mapping_id=None)

        assert summary["total_findings"] == 5
        assert summary["critical"] == 1
        assert summary["high"] == 2
        assert summary["medium"] == 1
        assert summary["low"] == 1

    def test_calculate_summary_groups_by_tool(self):
        from app.services.report_generator import ReportGenerator
        gen = self._make_generator()

        findings = [
            _make_finding(tool_name="nmap"),
            _make_finding(tool_name="nmap"),
            _make_finding(tool_name="sqlmap"),
        ]
        summary = gen._calculate_summary(findings, None)
        assert summary["by_tool"]["nmap"] == 2
        assert summary["by_tool"]["sqlmap"] == 1

    def test_calculate_summary_empty_findings(self):
        from app.services.report_generator import ReportGenerator
        gen = self._make_generator()
        summary = gen._calculate_summary([], None)
        assert summary["total_findings"] == 0
        assert summary["critical"] == 0

    def test_calculate_summary_includes_compliance(self):
        from app.services.report_generator import ReportGenerator
        gen = self._make_generator()

        compliance_result = MagicMock()
        compliance_result.compliance_score = 72
        compliance_result.compliance_status = MagicMock()
        compliance_result.compliance_status.value = "PARTIAL"
        compliance_result.met_requirements = 36
        compliance_result.total_requirements = 50

        gen.db.query.return_value.filter.return_value.first.return_value = compliance_result

        summary = gen._calculate_summary([], compliance_mapping_id=99)
        assert summary["compliance_score"] == 72
        assert summary["compliance_status"] == "PARTIAL"
        assert summary["compliance_met"] == 36

    def test_get_included_sections_no_template(self):
        from app.services.report_generator import ReportGenerator
        gen = self._make_generator()
        findings = [_make_finding()] * 5
        sections = gen._get_included_sections(None, findings)
        names = [s["name"] for s in sections]
        assert "Findings" in names
        findings_section = next(s for s in sections if s["name"] == "Findings")
        assert findings_section["items_count"] == 5

    def test_get_included_sections_with_template(self):
        from app.services.report_generator import ReportGenerator
        gen = self._make_generator()
        template = MagicMock()
        template.sections = [
            {"name": "Executive Summary", "include_by_default": True, "order": 1},
            {"name": "Findings", "include_by_default": True, "order": 2},
            {"name": "Appendix", "include_by_default": False, "order": 3},
        ]
        sections = gen._get_included_sections(template, [_make_finding()] * 3)
        names = [s["name"] for s in sections]
        assert "Executive Summary" in names
        assert "Findings" in names
        assert "Appendix" not in names     # include_by_default=False

    def test_format_findings_serializes_fields(self):
        from app.services.report_generator import ReportGenerator
        gen = self._make_generator()
        findings = [_make_finding(title="XSS", severity="high", host="10.0.0.1")]
        formatted = gen._format_findings(findings)
        assert len(formatted) == 1
        assert formatted[0]["title"] == "XSS"
        assert formatted[0]["severity"] == "high"
        assert formatted[0]["host"] == "10.0.0.1"


class TestReportGeneratorRendering:

    def test_fallback_html_contains_title(self):
        from app.services.report_generator import ReportGenerator
        db = MagicMock()
        gen = ReportGenerator.__new__(ReportGenerator)
        gen.db = db
        report = _make_report(title="Fallback Test Report")
        findings = [_make_finding()]
        html = gen._fallback_html(report, findings)
        assert "Fallback Test Report" in html
        assert "<table" in html

    @patch("app.services.report_generator.Environment")
    def test_render_html_str_uses_template(self, mock_env_cls):
        from app.services.report_generator import ReportGenerator
        mock_env = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = "<html>rendered</html>"
        mock_env.get_template.return_value = mock_template
        mock_env_cls.return_value = mock_env

        db = MagicMock()
        gen = ReportGenerator(db)
        report = _make_report()
        html = gen._render_html_str(report, [], None, include_charts=False)
        assert html == "<html>rendered</html>"

    def test_render_html_str_falls_back_on_missing_template(self):
        from app.services.report_generator import ReportGenerator
        db = MagicMock()
        gen = ReportGenerator.__new__(ReportGenerator)
        gen.db = db
        mock_env = MagicMock()
        mock_env.get_template.side_effect = Exception("Template not found")
        gen.env = mock_env

        report = _make_report(title="Fallback")
        html = gen._render_html_str(report, [], None, include_charts=False)
        assert "Fallback" in html


# ── ExcelRenderer ──────────────────────────────────────────────────────────────

class TestExcelRenderer:

    def test_renders_bytes(self):
        pytest.importorskip("openpyxl")
        from app.core.reporting.excel_renderer import ExcelRenderer

        report = _make_report()
        findings = [_make_finding()]
        renderer = ExcelRenderer()
        output = renderer.render(report, findings)

        assert isinstance(output, bytes)
        assert len(output) > 0

    def test_output_is_valid_xlsx(self):
        pytest.importorskip("openpyxl")
        from openpyxl import load_workbook
        from app.core.reporting.excel_renderer import ExcelRenderer

        report = _make_report()
        findings = [_make_finding(), _make_finding(title="RCE", severity="critical")]
        output = ExcelRenderer().render(report, findings)

        wb = load_workbook(filename=BytesIO(output))
        sheet_names = wb.sheetnames
        assert "Executive Summary" in sheet_names
        assert "Findings" in sheet_names
        assert "Charts" in sheet_names

    def test_findings_sheet_has_correct_row_count(self):
        pytest.importorskip("openpyxl")
        from openpyxl import load_workbook
        from app.core.reporting.excel_renderer import ExcelRenderer

        report = _make_report()
        n_findings = 4
        findings = [_make_finding(title=f"Finding {i}") for i in range(n_findings)]
        output = ExcelRenderer().render(report, findings)
        wb = load_workbook(filename=BytesIO(output))
        ws = wb["Findings"]
        # row 1 = headers; rows 2..n+1 = data
        data_rows = [r for r in ws.iter_rows(min_row=2, values_only=True) if r[0]]
        assert len(data_rows) == n_findings

    def test_extension_and_content_type(self):
        pytest.importorskip("openpyxl")
        from app.core.reporting.excel_renderer import ExcelRenderer
        renderer = ExcelRenderer()
        assert renderer.extension() == "xlsx"
        assert "spreadsheetml" in renderer.content_type()


# ── DigitalSignatureManager ────────────────────────────────────────────────────

class TestDigitalSignatureManager:

    def test_generate_self_signed_cert_returns_pem(self):
        pytest.importorskip("cryptography")
        from app.services.digital_signature import DigitalSignatureManager
        db = MagicMock()
        manager = DigitalSignatureManager(db)
        cert_pem, key_pem = manager.generate_self_signed_cert(
            common_name="Test User", organization="Red Team", days_valid=1
        )
        assert cert_pem.startswith(b"-----BEGIN CERTIFICATE-----")
        assert key_pem.startswith(b"-----BEGIN PRIVATE KEY-----")

    def test_self_signed_cert_is_parsable(self):
        pytest.importorskip("cryptography")
        from cryptography import x509
        from app.services.digital_signature import DigitalSignatureManager
        db = MagicMock()
        manager = DigitalSignatureManager(db)
        cert_pem, _ = manager.generate_self_signed_cert("Tester")
        cert = x509.load_pem_x509_certificate(cert_pem)
        # Common name
        from cryptography.x509.oid import NameOID
        cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        assert cn == "Tester"

    def test_serialize_report_is_deterministic(self):
        pytest.importorskip("cryptography")
        from app.services.digital_signature import DigitalSignatureManager
        db = MagicMock()
        manager = DigitalSignatureManager(db)
        report = _make_report(id=7, project_id=3, title="Stable")
        s1 = manager._serialize_report(report)
        s2 = manager._serialize_report(report)
        assert s1 == s2
        data = json.loads(s1)
        assert data["id"] == 7
        assert data["title"] == "Stable"

    def test_sign_and_verify_round_trip(self):
        pytest.importorskip("cryptography")
        from app.services.digital_signature import DigitalSignatureManager
        from app.models.report import DigitalSignature, ReportV2, ReportStatusV2

        db = MagicMock()
        manager = DigitalSignatureManager(db)

        cert_pem, key_pem = manager.generate_self_signed_cert("Test Signer", days_valid=1)

        report = _make_report(id=42, project_id=5, title="Signed Report")
        report.signed_by = None
        report.signed_at = None
        report.signature_certificate_fingerprint = None
        report.signature_metadata = None
        report.status = "draft"

        # Mock DB query for sign_report
        db.query.return_value.filter.return_value.first.return_value = report
        db.add = MagicMock()
        db.commit = MagicMock()
        db.refresh = MagicMock()

        sig = manager.sign_report(
            report_id=42,
            signer_id=1,
            certificate_pem=cert_pem,
            private_key_pem=key_pem,
        )

        assert sig.signed_content_hash is not None
        assert len(sig.signed_content_hash) == 64  # SHA-256 hex
        assert sig.signature_algorithm == "RSA-SHA256"
        assert sig.is_valid is True

        # Now verify — mock sig.report to return same report
        sig.report = report
        db.query.return_value.filter.return_value.first.return_value = sig
        result = manager.verify_signature(sig.id)
        assert result["valid"] is True

    def test_verify_detects_content_modification(self):
        pytest.importorskip("cryptography")
        from app.services.digital_signature import DigitalSignatureManager

        db = MagicMock()
        manager = DigitalSignatureManager(db)
        cert_pem, key_pem = manager.generate_self_signed_cert("Tester", days_valid=1)

        sig = MagicMock()
        sig.certificate_pem = cert_pem
        sig.signed_content_hash = "0" * 64   # deliberately wrong hash
        sig.report = _make_report(title="Original")

        # Mock certificate validity
        from cryptography import x509
        cert = x509.load_pem_x509_certificate(cert_pem)
        sig.certificate_pem = cert_pem

        db.query.return_value.filter.return_value.first.return_value = sig
        result = manager.verify_signature(1)
        assert result["valid"] is False
        assert "modified" in result["reason"].lower()


# ── CRUDReportV2 ───────────────────────────────────────────────────────────────

class TestCRUDReportV2:

    def _make_db(self):
        return MagicMock()

    def test_log_action_creates_entry(self):
        from app.crud.report import CRUDReportV2
        crud = CRUDReportV2()
        db = self._make_db()

        entry = MagicMock()
        entry.id = 1
        db.refresh = MagicMock()
        db.add = MagicMock()
        db.commit = MagicMock()

        with patch("app.crud.report.ReportAuditLog", return_value=entry):
            result = crud.log_action(db, report_id=5, action="CREATED", action_by=1, details={"x": 1})

        db.add.assert_called_once_with(entry)
        db.commit.assert_called_once()

    def test_update_status_sets_reviewer_on_approval(self):
        from app.crud.report import CRUDReportV2
        from app.models.report import ReportStatusV2
        crud = CRUDReportV2()
        db = self._make_db()

        report = _make_report()
        report.status = "draft"
        report.reviewed_by = None
        report.reviewed_at = None
        report.review_notes = None

        db.query.return_value.filter.return_value.first.return_value = report

        result = crud.update_status(db, 1, ReportStatusV2.approved, reviewer_id=42, notes="LGTM")

        assert report.status == ReportStatusV2.approved
        assert report.reviewed_by == 42
        assert report.review_notes == "LGTM"

    def test_publish_sets_flags(self):
        from app.crud.report import CRUDReportV2
        from app.models.report import ReportStatusV2
        crud = CRUDReportV2()
        db = self._make_db()

        report = _make_report()
        report.is_published = False
        report.published_at = None

        db.query.return_value.filter.return_value.first.return_value = report

        crud.publish(db, 1)

        assert report.is_published is True
        assert report.published_at is not None
        assert report.status == ReportStatusV2.published

    def test_get_latest_version_returns_highest(self):
        from app.crud.report import CRUDReportV2
        crud = CRUDReportV2()
        db = self._make_db()

        v = MagicMock()
        v.version_number = 3
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = v

        result = crud.get_latest_version(db, report_id=1)
        assert result.version_number == 3

    def test_list_templates_filters_by_type(self):
        from app.crud.report import CRUDReportV2
        crud = CRUDReportV2()
        db = self._make_db()

        templates = [MagicMock(), MagicMock()]
        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = templates
        db.query.return_value.order_by.return_value.all.return_value = templates

        result = crud.list_templates(db, report_type="compliance")
        assert result == templates


# ── ReportSchedule dispatch ────────────────────────────────────────────────────

class TestReportScheduleDispatch:

    def test_dispatch_skips_disabled_schedule(self):
        """generate_scheduled_report_v2 returns 'skipped' for disabled schedules."""
        from app.tasks.report_tasks import generate_scheduled_report_v2

        db = MagicMock()
        schedule = MagicMock()
        schedule.is_enabled = False

        with patch("app.tasks.report_tasks.SessionLocal", return_value=db):
            db.query.return_value.filter.return_value.first.return_value = schedule
            # Call the underlying function (bypass Celery decorator)
            result = generate_scheduled_report_v2.__wrapped__(MagicMock(), schedule_id=99)

        assert result["status"] == "skipped"

    def test_dispatch_skips_not_found_schedule(self):
        from app.tasks.report_tasks import generate_scheduled_report_v2

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with patch("app.tasks.report_tasks.SessionLocal", return_value=db):
            result = generate_scheduled_report_v2.__wrapped__(MagicMock(), schedule_id=0)

        assert result["status"] == "skipped"


# ── S3ReportStorage (mocked) ───────────────────────────────────────────────────

class TestS3ReportStorage:

    def test_upload_report_returns_metadata(self):
        with patch("boto3.client") as mock_boto:
            mock_s3 = MagicMock()
            mock_boto.return_value = mock_s3
            mock_s3.put_object.return_value = {}
            mock_s3.generate_presigned_url.return_value = "https://s3.example.com/presigned"

            from app.services.s3_storage import S3ReportStorage
            storage = S3ReportStorage("test-bucket")

            content = b"PDF content bytes"
            result = storage.upload_report(report_id=1, content=content, fmt="pdf", version=1)

            assert result["s3_key"] == "reports/1/v1/report.pdf"
            assert result["file_size_bytes"] == len(content)
            assert result["checksum_sha256"] == hashlib.sha256(content).hexdigest()
            mock_s3.put_object.assert_called_once()

    def test_upload_uses_aes256_encryption(self):
        with patch("boto3.client") as mock_boto:
            mock_s3 = MagicMock()
            mock_boto.return_value = mock_s3
            mock_s3.generate_presigned_url.return_value = "https://s3.example.com/x"

            from app.services.s3_storage import S3ReportStorage
            storage = S3ReportStorage("my-bucket")
            storage.upload_report(1, b"data", "html", 2)

            call_kwargs = mock_s3.put_object.call_args.kwargs
            assert call_kwargs["ServerSideEncryption"] == "AES256"

    def test_download_url_returns_presigned(self):
        with patch("boto3.client") as mock_boto:
            mock_s3 = MagicMock()
            mock_boto.return_value = mock_s3
            mock_s3.generate_presigned_url.return_value = "https://s3.example.com/download"

            from app.services.s3_storage import S3ReportStorage
            storage = S3ReportStorage("bucket")
            result = storage.download_url("reports/1/v1/report.pdf", expires_in=1800)

            assert result["url"] == "https://s3.example.com/download"
            assert result["expires_in"] == 1800

    def test_delete_report_removes_all_objects(self):
        with patch("boto3.client") as mock_boto:
            mock_s3 = MagicMock()
            mock_boto.return_value = mock_s3
            mock_s3.list_objects_v2.return_value = {
                "Contents": [
                    {"Key": "reports/1/v1/report.pdf",  "Size": 100, "LastModified": datetime.utcnow()},
                    {"Key": "reports/1/v1/report.html", "Size": 200, "LastModified": datetime.utcnow()},
                ]
            }

            from app.services.s3_storage import S3ReportStorage
            storage = S3ReportStorage("bucket")
            count = storage.delete_report(report_id=1)

            assert count == 2
            assert mock_s3.delete_object.call_count == 2
