"""CRUD for Report - Phase 6"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.report import Report, ReportStatus


class CRUDReport:

    def get(self, db: Session, report_id: int) -> Optional[Report]:
        return db.query(Report).filter(Report.id == report_id).first()

    def get_multi(
        self,
        db: Session,
        *,
        user_id: int,
        is_superuser: bool = False,
        project_id: Optional[int] = None,
        status: Optional[ReportStatus] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> dict:
        q = db.query(Report)
        if not is_superuser:
            q = q.filter(Report.created_by == user_id)
        if project_id is not None:
            q = q.filter(Report.project_id == project_id)
        if status is not None:
            q = q.filter(Report.status == status)
        total = q.with_entities(func.count()).scalar()
        items = q.order_by(Report.created_at.desc()).offset(skip).limit(limit).all()
        return {"total": total, "items": items, "skip": skip, "limit": limit}

    def delete(self, db: Session, *, report: Report) -> None:
        db.delete(report)
        db.commit()


crud_report = CRUDReport()
