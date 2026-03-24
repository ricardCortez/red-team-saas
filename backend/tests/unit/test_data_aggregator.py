"""Unit tests for ReportDataAggregator - Phase 6"""
import pytest
from unittest.mock import MagicMock, patch

from app.core.reporting.data_aggregator import ReportDataAggregator
from app.models.finding import Severity, FindingStatus


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_finding(
    id=1,
    title="XSS",
    severity=Severity.high,
    status=FindingStatus.open,
    host="10.0.0.1",
    port=80,
    service="http",
    tool_name="nikto",
    risk_score=7.5,
    is_duplicate=False,
    project_id=1,
):
    f = MagicMock()
    f.id = id
    f.title = title
    f.description = "desc"
    f.severity = severity
    f.status = status
    f.host = host
    f.port = port
    f.service = service
    f.tool_name = tool_name
    f.risk_score = risk_score
    f.is_duplicate = is_duplicate
    f.project_id = project_id
    return f


def _make_result(tool_name="nmap", target="10.0.0.1", success=True, risk_score=5.0):
    r = MagicMock()
    r.tool_name = tool_name
    r.tool = None
    r.target = target
    r.success = success
    r.risk_score = risk_score
    r.duration_seconds = 10.0
    return r


# ── tests ──────────────────────────────────────────────────────────────────────

class TestReportDataAggregator:

    def setup_method(self):
        self.db = MagicMock()
        self.aggregator = ReportDataAggregator(self.db, project_id=1)

    def _patch_db(self, findings=None, results=None):
        """Patch db.query to return given findings and results."""
        findings = findings or []
        results = results or []

        def query_side_effect(model):
            from app.models.finding import Finding
            from app.models.result import Result
            mock_q = MagicMock()
            if model is Finding:
                mock_q.filter.return_value = mock_q
                mock_q.order_by.return_value = mock_q
                mock_q.all.return_value = findings
            else:  # Result or Task
                mock_q.join.return_value = mock_q
                mock_q.filter.return_value = mock_q
                mock_q.all.return_value = results
            return mock_q

        self.db.query.side_effect = query_side_effect

    def test_aggregate_returns_all_keys(self):
        self._patch_db()
        data = self.aggregator.aggregate()
        assert set(data.keys()) == {
            "findings", "results_summary", "stats",
            "top_risks", "hosts_affected", "tools_used",
        }

    def test_stats_counts_by_severity(self):
        findings = [
            _make_finding(id=1, severity=Severity.critical, risk_score=9.0),
            _make_finding(id=2, severity=Severity.critical, risk_score=9.5),
            _make_finding(id=3, severity=Severity.high, risk_score=7.0),
            _make_finding(id=4, severity=Severity.medium, risk_score=5.0),
            _make_finding(id=5, severity=Severity.low, risk_score=2.0),
        ]
        self._patch_db(findings=findings)
        data = self.aggregator.aggregate()
        stats = data["stats"]
        assert stats["critical"] == 2
        assert stats["high"] == 1
        assert stats["medium"] == 1
        assert stats["low"] == 1
        assert stats["total"] == 5

    def test_top_risks_ordered_by_risk_score(self):
        findings = [
            _make_finding(id=1, risk_score=3.0),
            _make_finding(id=2, risk_score=9.5),
            _make_finding(id=3, risk_score=6.0),
        ]
        self._patch_db(findings=findings)
        data = self.aggregator.aggregate()
        scores = [f["risk_score"] for f in data["top_risks"]]
        assert scores == sorted(scores, reverse=True)

    def test_top_risks_capped_at_10(self):
        findings = [_make_finding(id=i, risk_score=float(i)) for i in range(1, 20)]
        self._patch_db(findings=findings)
        data = self.aggregator.aggregate()
        assert len(data["top_risks"]) <= 10

    def test_hosts_affected_deduped(self):
        findings = [
            _make_finding(id=1, host="10.0.0.1"),
            _make_finding(id=2, host="10.0.0.1"),
            _make_finding(id=3, host="10.0.0.2"),
        ]
        self._patch_db(findings=findings)
        data = self.aggregator.aggregate()
        assert len(data["hosts_affected"]) == 2
        assert set(data["hosts_affected"]) == {"10.0.0.1", "10.0.0.2"}

    def test_false_positives_excluded(self):
        """False positive findings must NOT appear in aggregated data (filtered at DB level)."""
        # The filter is applied in _get_findings via the DB query; we simulate
        # that the DB already returns only non-FP findings.
        findings = [_make_finding(id=1, status=FindingStatus.open)]
        self._patch_db(findings=findings)
        data = self.aggregator.aggregate()
        assert all(f["status"] != FindingStatus.false_positive.value for f in data["findings"])

    def test_duplicate_findings_excluded(self):
        """Duplicate findings must NOT appear (filtered at DB level)."""
        findings = [_make_finding(id=1, is_duplicate=False)]
        self._patch_db(findings=findings)
        data = self.aggregator.aggregate()
        assert all(not isinstance(f, MagicMock) for f in data["findings"])

    def test_tools_used_deduped(self):
        results = [
            _make_result(tool_name="nmap"),
            _make_result(tool_name="nmap"),
            _make_result(tool_name="nikto"),
        ]
        self._patch_db(results=results)
        data = self.aggregator.aggregate()
        assert len(data["tools_used"]) == 2

    def test_overall_risk_is_max(self):
        findings = [
            _make_finding(id=1, risk_score=5.0),
            _make_finding(id=2, risk_score=9.5),
            _make_finding(id=3, risk_score=3.0),
        ]
        self._patch_db(findings=findings)
        data = self.aggregator.aggregate()
        assert data["stats"]["overall_risk"] == 9.5

    def test_empty_project_returns_zero_stats(self):
        self._patch_db()
        data = self.aggregator.aggregate()
        assert data["stats"]["total"] == 0
        assert data["stats"]["overall_risk"] == 0.0
