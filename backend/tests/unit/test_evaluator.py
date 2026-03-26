"""Unit tests for AlertEvaluator - Phase 8"""
import pytest
from unittest.mock import MagicMock, patch
from app.models.alert_rule import AlertRule, AlertChannel, AlertTrigger
from app.models.finding import Finding, Severity
from app.models.task import Task, TaskStatusEnum
from app.models.notification import NotificationStatus
from app.core.notifications.evaluator import AlertEvaluator


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_finding(
    id=1,
    severity=Severity.critical,
    risk_score=9.0,
    tool_name="nmap",
    host="10.0.0.1",
    project_id=1,
    task_id=1,
    title="Test Finding",
    description="desc",
):
    f = MagicMock(spec=Finding)
    f.id = id
    f.severity = severity
    f.risk_score = risk_score
    f.tool_name = tool_name
    f.host = host
    f.project_id = project_id
    f.task_id = task_id
    f.title = title
    f.description = description
    return f


def make_task(
    id=10,
    user_id=1,
    project_id=1,
    status=TaskStatusEnum.completed,
    name="nmap scan",
    tool_name="nmap",
    target="10.0.0.1",
    error_message=None,
):
    t = MagicMock(spec=Task)
    t.id = id
    t.user_id = user_id
    t.project_id = project_id
    t.status = status
    t.name = name
    t.tool_name = tool_name
    t.target = target
    t.error_message = error_message
    return t


def make_rule(
    id=1,
    user_id=1,
    project_id=None,
    trigger=AlertTrigger.SEVERITY_THRESHOLD,
    channel=AlertChannel.WEBHOOK,
    conditions=None,
    is_active=True,
    rate_limit_minutes=0,
    channel_config=None,
):
    r = MagicMock(spec=AlertRule)
    r.id = id
    r.user_id = user_id
    r.project_id = project_id
    r.trigger = trigger
    r.channel = channel
    r.conditions = conditions or {}
    r.is_active = is_active
    r.rate_limit_minutes = rate_limit_minutes
    r.channel_config = channel_config or {"url": "https://webhook.example.com"}
    return r


def make_evaluator_with_rules(rules, db=None):
    db = db or MagicMock()
    db.query.return_value.filter.return_value.filter.return_value.all.return_value = rules
    db.add = MagicMock()
    db.commit = MagicMock()
    return AlertEvaluator(db)


# ── Severity threshold tests ───────────────────────────────────────────────────

class TestSeverityThreshold:
    def test_severity_threshold_matches(self):
        rule = make_rule(
            trigger=AlertTrigger.SEVERITY_THRESHOLD,
            conditions={"severity": ["critical", "high"]},
        )
        finding = make_finding(severity=Severity.critical)
        evaluator = make_evaluator_with_rules([rule])

        with patch("app.core.notifications.evaluator.is_rate_limited", return_value=False):
            with patch.object(evaluator, "_dispatch") as mock_dispatch:
                evaluator._matches_finding(rule, finding)
                # Directly test _matches_finding
                assert evaluator._matches_finding(rule, finding) is True

    def test_severity_threshold_no_match(self):
        rule = make_rule(
            trigger=AlertTrigger.SEVERITY_THRESHOLD,
            conditions={"severity": ["critical"]},
        )
        finding = make_finding(severity=Severity.low)
        evaluator = make_evaluator_with_rules([rule])
        assert evaluator._matches_finding(rule, finding) is False

    def test_severity_threshold_high_matches(self):
        rule = make_rule(
            trigger=AlertTrigger.SEVERITY_THRESHOLD,
            conditions={"severity": ["critical", "high"]},
        )
        finding = make_finding(severity=Severity.high)
        evaluator = make_evaluator_with_rules([rule])
        assert evaluator._matches_finding(rule, finding) is True


# ── Risk score threshold tests ─────────────────────────────────────────────────

class TestRiskScoreThreshold:
    def test_risk_score_threshold_matches(self):
        rule = make_rule(
            trigger=AlertTrigger.RISK_SCORE_THRESHOLD,
            conditions={"min_risk_score": 7.5},
        )
        finding = make_finding(risk_score=9.0)
        evaluator = make_evaluator_with_rules([rule])
        assert evaluator._matches_finding(rule, finding) is True

    def test_risk_score_threshold_no_match(self):
        rule = make_rule(
            trigger=AlertTrigger.RISK_SCORE_THRESHOLD,
            conditions={"min_risk_score": 7.5},
        )
        finding = make_finding(risk_score=5.0)
        evaluator = make_evaluator_with_rules([rule])
        assert evaluator._matches_finding(rule, finding) is False

    def test_risk_score_threshold_exact_match(self):
        rule = make_rule(
            trigger=AlertTrigger.RISK_SCORE_THRESHOLD,
            conditions={"min_risk_score": 9.0},
        )
        finding = make_finding(risk_score=9.0)
        evaluator = make_evaluator_with_rules([rule])
        assert evaluator._matches_finding(rule, finding) is True


# ── Finding created tests ──────────────────────────────────────────────────────

class TestFindingCreatedTrigger:
    def test_finding_created_no_filters(self):
        rule = make_rule(
            trigger=AlertTrigger.FINDING_CREATED,
            conditions={},
        )
        finding = make_finding()
        evaluator = make_evaluator_with_rules([rule])
        assert evaluator._matches_finding(rule, finding) is True

    def test_finding_created_with_tool_filter_matches(self):
        rule = make_rule(
            trigger=AlertTrigger.FINDING_CREATED,
            conditions={"tool_name": "nmap"},
        )
        finding = make_finding(tool_name="nmap")
        evaluator = make_evaluator_with_rules([rule])
        assert evaluator._matches_finding(rule, finding) is True

    def test_finding_created_with_tool_filter_no_match(self):
        rule = make_rule(
            trigger=AlertTrigger.FINDING_CREATED,
            conditions={"tool_name": "nmap"},
        )
        finding = make_finding(tool_name="gobuster")
        evaluator = make_evaluator_with_rules([rule])
        assert evaluator._matches_finding(rule, finding) is False

    def test_finding_created_with_severity_filter(self):
        rule = make_rule(
            trigger=AlertTrigger.FINDING_CREATED,
            conditions={"severity": ["critical"]},
        )
        finding = make_finding(severity=Severity.medium)
        evaluator = make_evaluator_with_rules([rule])
        assert evaluator._matches_finding(rule, finding) is False


# ── Scan trigger tests ─────────────────────────────────────────────────────────

class TestScanTriggers:
    def test_scan_failed_trigger_dispatches(self):
        rule = make_rule(trigger=AlertTrigger.SCAN_FAILED, rate_limit_minutes=0)
        task = make_task(status=TaskStatusEnum.failed, error_message="timeout")
        evaluator = make_evaluator_with_rules([rule])

        with patch("app.core.notifications.evaluator.is_rate_limited", return_value=False):
            channel_mock = MagicMock()
            channel_mock.send.return_value = True
            with patch.dict("app.core.notifications.evaluator.CHANNELS", {AlertChannel.WEBHOOK: channel_mock}):
                evaluator.evaluate_scan(task)

        channel_mock.send.assert_called_once()

    def test_scan_completed_trigger_dispatches(self):
        rule = make_rule(trigger=AlertTrigger.SCAN_COMPLETED, rate_limit_minutes=0)
        task = make_task(status=TaskStatusEnum.completed)
        evaluator = make_evaluator_with_rules([rule])

        with patch("app.core.notifications.evaluator.is_rate_limited", return_value=False):
            channel_mock = MagicMock()
            channel_mock.send.return_value = True
            with patch.dict("app.core.notifications.evaluator.CHANNELS", {AlertChannel.WEBHOOK: channel_mock}):
                evaluator.evaluate_scan(task)

        channel_mock.send.assert_called_once()

    def test_scan_completed_trigger_no_dispatch_on_failed(self):
        rule = make_rule(trigger=AlertTrigger.SCAN_COMPLETED, rate_limit_minutes=0)
        task = make_task(status=TaskStatusEnum.failed)
        evaluator = make_evaluator_with_rules([rule])

        with patch("app.core.notifications.evaluator.is_rate_limited", return_value=False):
            channel_mock = MagicMock()
            with patch.dict("app.core.notifications.evaluator.CHANNELS", {AlertChannel.WEBHOOK: channel_mock}):
                evaluator.evaluate_scan(task)

        channel_mock.send.assert_not_called()


# ── Rate limiting behavior ─────────────────────────────────────────────────────

class TestRateLimitingBehavior:
    def test_rate_limited_saves_skipped_notification(self):
        rule = make_rule(trigger=AlertTrigger.SEVERITY_THRESHOLD, conditions={"severity": ["critical"]})
        finding = make_finding(severity=Severity.critical)
        db = MagicMock()
        db.query.return_value.filter.return_value.filter.return_value.all.return_value = [rule]
        db.query.return_value.filter.return_value.first.return_value = make_task()
        evaluator = AlertEvaluator(db)

        with patch("app.core.notifications.evaluator.is_rate_limited", return_value=True):
            evaluator._dispatch(rule, finding=finding)

        db.add.assert_called_once()
        notification_saved = db.add.call_args[0][0]
        assert notification_saved.status == NotificationStatus.SKIPPED


# ── Global rule applies to all projects ───────────────────────────────────────

class TestGlobalRuleScope:
    def test_global_rule_project_id_none_included(self):
        """Rules with project_id=None should apply to all projects."""
        global_rule = make_rule(project_id=None, trigger=AlertTrigger.SEVERITY_THRESHOLD, conditions={"severity": ["critical"]})
        finding = make_finding(severity=Severity.critical, project_id=99)

        db = MagicMock()
        # Simulate the filter returning the global rule even for project_id=99
        db.query.return_value.filter.return_value.filter.return_value.all.return_value = [global_rule]
        db.query.return_value.filter.return_value.first.return_value = make_task(user_id=1)
        evaluator = AlertEvaluator(db)

        with patch("app.core.notifications.evaluator.is_rate_limited", return_value=False):
            channel_mock = MagicMock()
            channel_mock.send.return_value = True
            with patch.dict("app.core.notifications.evaluator.CHANNELS", {AlertChannel.WEBHOOK: channel_mock}):
                evaluator.evaluate_finding(finding)

        channel_mock.send.assert_called_once()

    def test_notification_failed_status_on_channel_error(self):
        rule = make_rule(trigger=AlertTrigger.SEVERITY_THRESHOLD, conditions={"severity": ["critical"]}, rate_limit_minutes=0)
        finding = make_finding(severity=Severity.critical)
        db = MagicMock()
        evaluator = AlertEvaluator(db)

        with patch("app.core.notifications.evaluator.is_rate_limited", return_value=False):
            channel_mock = MagicMock()
            channel_mock.send.return_value = False
            with patch.dict("app.core.notifications.evaluator.CHANNELS", {AlertChannel.WEBHOOK: channel_mock}):
                evaluator._dispatch(rule, finding=finding)

        db.add.assert_called_once()
        notification_saved = db.add.call_args[0][0]
        assert notification_saved.status == NotificationStatus.FAILED
