"""Aggregated metrics queries for the analytics layer."""
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case
from app.models.finding import Finding, Severity, FindingStatus
from app.models.result import Result
from app.models.task import Task, TaskStatusEnum
from app.models.report import Report, ReportStatus
from app.core.analytics.cache import cache_result
from typing import Optional


class MetricsEngine:

    @staticmethod
    @cache_result(ttl=120, prefix="analytics")
    def global_summary(db: Session, user_id: int) -> dict:
        """Global summary counts for the authenticated user."""
        base_task = db.query(Task).filter(Task.user_id == user_id)
        base_finding = (
            db.query(Finding)
            .join(Task, Finding.task_id == Task.id)
            .filter(Task.user_id == user_id)
        )

        return {
            "total_scans": base_task.count(),
            "scans_running": base_task.filter(Task.status == TaskStatusEnum.running).count(),
            "scans_completed": base_task.filter(Task.status == TaskStatusEnum.completed).count(),
            "scans_failed": base_task.filter(Task.status == TaskStatusEnum.failed).count(),
            "total_findings": base_finding.filter(Finding.is_duplicate == False).count(),
            "open_findings": base_finding.filter(
                Finding.status == FindingStatus.open,
                Finding.is_duplicate == False,
            ).count(),
            "critical_findings": base_finding.filter(
                Finding.severity == Severity.critical,
                Finding.is_duplicate == False,
            ).count(),
            "high_findings": base_finding.filter(
                Finding.severity == Severity.high,
                Finding.is_duplicate == False,
            ).count(),
            "total_reports": db.query(Report).filter(Report.created_by == user_id).count(),
            "reports_ready": db.query(Report).filter(
                Report.created_by == user_id,
                Report.status == ReportStatus.ready,
            ).count(),
        }

    @staticmethod
    @cache_result(ttl=120, prefix="analytics")
    def project_summary(db: Session, project_id: int) -> dict:
        """Detailed metrics for a single project."""
        findings_q = db.query(Finding).filter(
            Finding.project_id == project_id,
            Finding.is_duplicate == False,
        )
        results_q = db.query(Result).join(Task).filter(Task.project_id == project_id)

        by_severity = {sev.value: findings_q.filter(Finding.severity == sev).count() for sev in Severity}
        by_status = {st.value: findings_q.filter(Finding.status == st).count() for st in FindingStatus}

        avg_risk = results_q.with_entities(func.avg(Result.risk_score)).scalar() or 0.0
        max_risk = results_q.with_entities(func.max(Result.risk_score)).scalar() or 0.0
        avg_duration = results_q.with_entities(func.avg(Result.duration_seconds)).scalar() or 0.0

        return {
            "findings_by_severity": by_severity,
            "findings_by_status": by_status,
            "total_findings": findings_q.count(),
            "false_positives": findings_q.filter(Finding.status == FindingStatus.false_positive).count(),
            "avg_risk_score": round(float(avg_risk), 2),
            "max_risk_score": round(float(max_risk), 2),
            "avg_scan_duration_s": round(float(avg_duration), 2),
            "total_scans": results_q.count(),
            "successful_scans": results_q.filter(Result.success == True).count(),
        }

    @staticmethod
    @cache_result(ttl=300, prefix="analytics")
    def top_targets(db: Session, user_id: int, limit: int = 10) -> list:
        """Hosts with most findings (excluding FP and duplicates), ordered by count."""
        rows = (
            db.query(
                Finding.host,
                func.count(Finding.id).label("count"),
                func.max(Finding.risk_score).label("max_risk"),
            )
            .join(Task, Finding.task_id == Task.id)
            .filter(
                Task.user_id == user_id,
                Finding.is_duplicate == False,
                Finding.status != FindingStatus.false_positive,
                Finding.host.isnot(None),
            )
            .group_by(Finding.host)
            .order_by(desc("count"))
            .limit(limit)
            .all()
        )
        return [
            {"host": r.host, "findings": r.count, "max_risk": round(float(r.max_risk or 0), 2)}
            for r in rows
        ]

    @staticmethod
    @cache_result(ttl=300, prefix="analytics")
    def top_tools(db: Session, user_id: int) -> list:
        """Tools with total runs, success count, avg risk, and avg duration."""
        rows = (
            db.query(
                Result.tool_name,
                func.count(Result.id).label("total"),
                func.sum(case((Result.success == True, 1), else_=0)).label("successful"),
                func.avg(Result.risk_score).label("avg_risk"),
                func.avg(Result.duration_seconds).label("avg_duration"),
            )
            .join(Task, Result.task_id == Task.id)
            .filter(Task.user_id == user_id)
            .group_by(Result.tool_name)
            .order_by(desc("total"))
            .all()
        )
        return [
            {
                "tool": r.tool_name,
                "total_runs": r.total,
                "successful": int(r.successful or 0),
                "avg_risk": round(float(r.avg_risk or 0), 2),
                "avg_duration": round(float(r.avg_duration or 0), 2),
            }
            for r in rows
        ]

    @staticmethod
    @cache_result(ttl=300, prefix="analytics")
    def severity_heatmap(db: Session, project_id: int) -> list:
        """
        Heatmap: host × severity → count.
        Returns list of {host, critical, high, medium, low, info}.
        """
        rows = (
            db.query(
                Finding.host,
                Finding.severity,
                func.count(Finding.id).label("count"),
            )
            .filter(
                Finding.project_id == project_id,
                Finding.is_duplicate == False,
                Finding.status != FindingStatus.false_positive,
                Finding.host.isnot(None),
            )
            .group_by(Finding.host, Finding.severity)
            .all()
        )

        pivot: dict = {}
        for row in rows:
            if row.host not in pivot:
                pivot[row.host] = {s.value: 0 for s in Severity}
                pivot[row.host]["host"] = row.host
            pivot[row.host][row.severity.value] = row.count

        return sorted(
            pivot.values(),
            key=lambda x: x.get("critical", 0) + x.get("high", 0),
            reverse=True,
        )
