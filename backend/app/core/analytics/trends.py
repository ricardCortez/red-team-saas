"""Time-series trend queries for the analytics layer."""
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.finding import Finding, Severity
from app.models.result import Result
from app.models.task import Task, TaskStatusEnum
from app.core.analytics.cache import cache_result
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class TrendsEngine:

    @staticmethod
    @cache_result(ttl=600, prefix="trends")
    def findings_over_time(
        db: Session,
        user_id: int,
        days: int = 30,
        project_id: Optional[int] = None,
    ) -> List[Dict]:
        """
        New findings per day for the last N days.
        Returns [{date, critical, high, medium, low, info, total}] with zeros for empty days.
        Uses func.date() for SQLite/PostgreSQL portability.
        """
        since = datetime.utcnow() - timedelta(days=days)
        date_col = func.date(Finding.created_at).label("date")

        q = (
            db.query(date_col, Finding.severity, func.count(Finding.id).label("count"))
            .join(Task, Finding.task_id == Task.id)
            .filter(
                Task.user_id == user_id,
                Finding.created_at >= since,
                Finding.is_duplicate == False,
            )
        )
        if project_id:
            q = q.filter(Finding.project_id == project_id)

        rows = q.group_by(date_col, Finding.severity).order_by(date_col).all()

        by_date: Dict[str, Dict] = {}
        for row in rows:
            d = str(row.date)
            if d not in by_date:
                by_date[d] = {
                    "date": d, "critical": 0, "high": 0,
                    "medium": 0, "low": 0, "info": 0, "total": 0,
                }
            by_date[d][row.severity.value] += row.count
            by_date[d]["total"] += row.count

        result = []
        for i in range(days):
            d = str((datetime.utcnow() - timedelta(days=days - 1 - i)).date())
            result.append(by_date.get(d, {
                "date": d, "critical": 0, "high": 0,
                "medium": 0, "low": 0, "info": 0, "total": 0,
            }))
        return result

    @staticmethod
    @cache_result(ttl=600, prefix="trends")
    def risk_score_trend(
        db: Session,
        user_id: int,
        days: int = 30,
        project_id: Optional[int] = None,
    ) -> List[Dict]:
        """
        Average and max risk score per day from successful scans.
        Returns [{date, avg_risk, max_risk, scan_count}] with zeros for empty days.
        """
        since = datetime.utcnow() - timedelta(days=days)
        date_col = func.date(Result.created_at).label("date")

        q = (
            db.query(
                date_col,
                func.avg(Result.risk_score).label("avg_risk"),
                func.max(Result.risk_score).label("max_risk"),
                func.count(Result.id).label("scan_count"),
            )
            .join(Task, Result.task_id == Task.id)
            .filter(
                Task.user_id == user_id,
                Result.created_at >= since,
                Result.success == True,
            )
        )
        if project_id:
            q = q.filter(Task.project_id == project_id)

        rows = q.group_by(date_col).order_by(date_col).all()

        by_date = {
            str(r.date): {
                "date": str(r.date),
                "avg_risk": round(float(r.avg_risk or 0), 2),
                "max_risk": round(float(r.max_risk or 0), 2),
                "scan_count": r.scan_count,
            }
            for r in rows
        }

        result = []
        for i in range(days):
            d = str((datetime.utcnow() - timedelta(days=days - 1 - i)).date())
            result.append(by_date.get(d, {
                "date": d, "avg_risk": 0.0, "max_risk": 0.0, "scan_count": 0,
            }))
        return result

    @staticmethod
    @cache_result(ttl=300, prefix="trends")
    def scan_activity(
        db: Session,
        user_id: int,
        days: int = 30,
    ) -> List[Dict]:
        """
        Tasks per day split by completed/failed.
        Returns [{date, completed, failed, total}] with zeros for empty days.
        """
        since = datetime.utcnow() - timedelta(days=days)
        date_col = func.date(Task.created_at).label("date")

        rows = (
            db.query(date_col, Task.status, func.count(Task.id).label("count"))
            .filter(Task.user_id == user_id, Task.created_at >= since)
            .group_by(date_col, Task.status)
            .order_by(date_col)
            .all()
        )

        by_date: Dict[str, Dict] = {}
        for row in rows:
            d = str(row.date)
            if d not in by_date:
                by_date[d] = {"date": d, "completed": 0, "failed": 0, "total": 0}
            status_val = row.status.value if hasattr(row.status, "value") else row.status
            if status_val == TaskStatusEnum.completed.value:
                by_date[d]["completed"] += row.count
            elif status_val == TaskStatusEnum.failed.value:
                by_date[d]["failed"] += row.count
            by_date[d]["total"] += row.count

        result = []
        for i in range(days):
            d = str((datetime.utcnow() - timedelta(days=days - 1 - i)).date())
            result.append(by_date.get(d, {"date": d, "completed": 0, "failed": 0, "total": 0}))
        return result
