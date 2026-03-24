"""Unit tests for report_tasks Celery task - Phase 6"""
import pytest
from unittest.mock import MagicMock, patch

from app.models.report import Report, ReportFormat, ReportStatus, ReportType, ReportClassification


# ── constants ──────────────────────────────────────────────────────────────────

FAKE_STATS = {
    "total": 5, "critical": 1, "high": 2,
    "medium": 1, "low": 1, "info": 0, "overall_risk": 8.5,
}
FAKE_DATA = {
    "findings": [],
    "results_summary": [],
    "stats": FAKE_STATS,
    "top_risks": [],
    "hosts_affected": [],
    "tools_used": [],
}


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_report_obj(report_id=1, fmt=ReportFormat.html, rtype=ReportType.technical):
    r = MagicMock(spec=Report)
    r.id = report_id
    r.project_id = 10
    r.report_format = fmt
    r.report_type = rtype
    r.classification = ReportClassification.confidential
    r.title = "Test Report"
    r.status = ReportStatus.pending
    r.celery_task_id = None
    r.file_path = None
    r.file_size_bytes = None
    r.generated_at = None
    r.total_findings = 0
    r.critical_count = 0
    r.high_count = 0
    r.medium_count = 0
    r.low_count = 0
    r.overall_risk = 0.0
    return r


def _run_task_eager(report_id, report=None, content=b"<html>ok</html>", fail_agg=False):
    """Run generate_report through Celery eager mode with mocked externals."""
    from app.tasks.report_tasks import generate_report
    from app.tasks.celery_app import celery_app

    if report is None:
        report = _make_report_obj(report_id)

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = report

    mock_agg = MagicMock()
    if fail_agg:
        mock_agg.aggregate.side_effect = RuntimeError("aggregation failed")
    else:
        mock_agg.aggregate.return_value = FAKE_DATA

    mock_renderer = MagicMock()
    mock_renderer.render.return_value = content
    mock_renderer.extension.return_value = "html"

    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = False
    try:
        with patch("app.tasks.report_tasks.SessionLocal", return_value=mock_db), \
             patch("app.tasks.report_tasks.ReportDataAggregator", return_value=mock_agg), \
             patch("app.tasks.report_tasks.HTMLRenderer", return_value=mock_renderer), \
             patch("app.tasks.report_tasks.PDFRenderer", return_value=mock_renderer), \
             patch("app.tasks.report_tasks.os.makedirs"), \
             patch("builtins.open", MagicMock()), \
             patch("app.tasks.report_tasks.STORAGE_DIR", "/tmp/test_reports"):
            async_result = generate_report.apply(args=[report_id])
    finally:
        celery_app.conf.task_always_eager = False

    return async_result, report, mock_db


# ── tests ──────────────────────────────────────────────────────────────────────

class TestGenerateReportTask:

    def test_generate_report_success_returns_dict(self):
        result, _, _ = _run_task_eager(1)
        assert result.result["report_id"] == 1
        assert "file" in result.result
        assert "size" in result.result

    def test_generate_report_updates_status_ready(self):
        _, report, _ = _run_task_eager(1)
        assert report.status == ReportStatus.ready

    def test_generate_report_snapshots_stats(self):
        _, report, _ = _run_task_eager(1)
        assert report.total_findings == FAKE_STATS["total"]
        assert report.critical_count == FAKE_STATS["critical"]
        assert report.high_count == FAKE_STATS["high"]
        assert report.medium_count == FAKE_STATS["medium"]
        assert report.low_count == FAKE_STATS["low"]
        assert report.overall_risk == FAKE_STATS["overall_risk"]

    def test_generate_report_sets_generating_first(self):
        """Status must be set to GENERATING before rendering completes."""
        status_sequence = []

        def track_commit(report):
            def _commit():
                status_sequence.append(report.status)
            return _commit

        from app.tasks.report_tasks import generate_report
        from app.tasks.celery_app import celery_app

        report = _make_report_obj()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = report
        mock_db.commit.side_effect = lambda: status_sequence.append(report.status)

        mock_agg = MagicMock()
        mock_agg.aggregate.return_value = FAKE_DATA
        mock_renderer = MagicMock()
        mock_renderer.render.return_value = b"<html></html>"
        mock_renderer.extension.return_value = "html"

        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagates = False
        try:
            with patch("app.tasks.report_tasks.SessionLocal", return_value=mock_db), \
                 patch("app.tasks.report_tasks.ReportDataAggregator", return_value=mock_agg), \
                 patch("app.tasks.report_tasks.HTMLRenderer", return_value=mock_renderer), \
                 patch("app.tasks.report_tasks.PDFRenderer", return_value=mock_renderer), \
                 patch("app.tasks.report_tasks.os.makedirs"), \
                 patch("builtins.open", MagicMock()), \
                 patch("app.tasks.report_tasks.STORAGE_DIR", "/tmp"):
                generate_report.apply(args=[1])
        finally:
            celery_app.conf.task_always_eager = False

        assert ReportStatus.generating in status_sequence

    def test_generate_report_on_failure_marks_failed(self):
        result, report, _ = _run_task_eager(1, fail_agg=True)
        assert report.status == ReportStatus.failed
        assert "aggregation failed" in report.error_message

    def test_generate_report_not_found_raises(self):
        from app.tasks.report_tasks import generate_report
        from app.tasks.celery_app import celery_app

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagates = True
        try:
            with patch("app.tasks.report_tasks.SessionLocal", return_value=mock_db):
                with pytest.raises(Exception):
                    generate_report.apply(args=[999])
        finally:
            celery_app.conf.task_always_eager = False
            celery_app.conf.task_eager_propagates = False
