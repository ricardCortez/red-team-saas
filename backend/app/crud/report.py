"""CRUD for Report"""
from typing import Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.crud.base import CRUDBase
from app.models.report import Report, ReportStatus
from app.schemas.report import ReportCreate, ReportUpdate


class CRUDReport(CRUDBase[Report, ReportCreate, ReportUpdate]):

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 20,
        filters: Dict = None,
    ) -> Dict:
        query = db.query(Report)

        if filters:
            if filters.get("author_id") is not None:
                query = query.filter(Report.author_id == filters["author_id"])
            if filters.get("workspace_id") is not None:
                query = query.filter(Report.workspace_id == filters["workspace_id"])
            if filters.get("status"):
                query = query.filter(Report.status == filters["status"])

        total = query.with_entities(func.count()).scalar()
        items = query.order_by(Report.created_at.desc()).offset(skip).limit(limit).all()
        return {"items": items, "total": total, "skip": skip, "limit": limit}

    def finalize(self, db: Session, *, db_obj: Report) -> Report:
        """Compute and store digital signature, set status to final"""
        from datetime import datetime, timezone
        db_obj.signature_hash = db_obj.compute_signature()
        db_obj.signed_at = datetime.now(timezone.utc)
        db_obj.status = ReportStatus.final
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


crud_report = CRUDReport(Report)
