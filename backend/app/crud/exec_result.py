"""Phase 5 Execution Result CRUD - filtered queries, export, project summaries"""
from typing import List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.result import Result
from app.models.task import Task
from app.schemas.result import ResultFilter


class CRUDExecResult:

    def get(self, db: Session, result_id: int) -> Result | None:
        return db.query(Result).filter(Result.id == result_id).first()

    def get_multi_filtered(
        self,
        db: Session,
        *,
        user_id: int,
        filters: ResultFilter,
        skip: int = 0,
        limit: int = 20,
        is_superuser: bool = False,
    ) -> Tuple[List[Result], int]:
        q = db.query(Result).join(Task, Result.task_id == Task.id)

        # Non-superusers only see results from their own tasks
        if not is_superuser:
            q = q.filter(Task.user_id == user_id)

        if filters.tool_name:
            q = q.filter(Result.tool_name == filters.tool_name)
        if filters.target:
            q = q.filter(Result.target.ilike(f"%{filters.target}%"))
        if filters.min_risk_score is not None:
            q = q.filter(Result.risk_score >= filters.min_risk_score)
        if filters.success is not None:
            q = q.filter(Result.success == filters.success)
        if filters.project_id is not None:
            q = q.filter(Task.project_id == filters.project_id)
        if filters.date_from:
            q = q.filter(Result.created_at >= filters.date_from)
        if filters.date_to:
            q = q.filter(Result.created_at <= filters.date_to)

        total = q.count()
        items = q.order_by(desc(Result.created_at)).offset(skip).limit(limit).all()
        return items, total

    def get_summary_by_project(self, db: Session, project_id: int) -> dict:
        base_q = db.query(Result).join(Task, Result.task_id == Task.id).filter(
            Task.project_id == project_id
        )
        total = base_q.count()
        successful = base_q.filter(Result.success == True).count()  # noqa: E712
        avg_risk = (
            db.query(func.avg(Result.risk_score))
            .join(Task, Result.task_id == Task.id)
            .filter(Task.project_id == project_id)
            .scalar()
            or 0.0
        )
        tools_used = [
            r[0]
            for r in base_q.with_entities(Result.tool_name).distinct().all()
            if r[0]
        ]
        return {
            "total_scans": total,
            "successful": successful,
            "failed": total - successful,
            "avg_risk_score": round(float(avg_risk), 2),
            "tools_used": tools_used,
        }


crud_exec_result = CRUDExecResult()
