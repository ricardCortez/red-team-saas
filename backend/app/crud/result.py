"""CRUD for Finding (scan results)"""
import json
from typing import Dict, Optional, Union, Any
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.crud.base import CRUDBase
from app.models.finding import Finding, Severity
from app.schemas.result import ResultCreate, ResultUpdate

_JSON_FIELDS = ("cve_ids", "mitre_ids")  # Text columns holding JSON arrays


class CRUDResult(CRUDBase[Finding, ResultCreate, ResultUpdate]):

    @staticmethod
    def _to_json(data: dict) -> dict:
        for field in _JSON_FIELDS:
            if field in data and not isinstance(data[field], str):
                data[field] = json.dumps(data[field]) if data[field] is not None else None
        return data

    def create(self, db: Session, *, obj_in: ResultCreate, **kwargs) -> Finding:
        data = self._to_json(jsonable_encoder(obj_in))
        data.update(kwargs)
        db_obj = Finding(**data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: Finding, obj_in: Union[ResultUpdate, Dict[str, Any]]) -> Finding:
        update_data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump(exclude_unset=True)
        update_data = self._to_json(update_data)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 50,
        filters: Dict = None,
    ) -> Dict:
        query = db.query(Finding)

        if filters:
            if filters.get("scan_id") is not None:
                query = query.filter(Finding.scan_id == filters["scan_id"])
            if filters.get("severity"):
                query = query.filter(Finding.severity == filters["severity"])
            if filters.get("tool"):
                query = query.filter(Finding.tool == filters["tool"])
            if filters.get("verified") is not None:
                query = query.filter(Finding.verified == filters["verified"])
            if filters.get("false_positive") is not None:
                query = query.filter(Finding.false_positive == filters["false_positive"])

        total = query.count()
        items = query.order_by(Finding.created_at.desc()).offset(skip).limit(limit).all()
        return {"items": items, "total": total, "skip": skip, "limit": limit}

    def get_summary(
        self,
        db: Session,
        scan_id: Optional[int] = None,
        project_id: Optional[int] = None,
    ) -> Dict:
        from app.models.scan import Scan

        query = db.query(Finding)
        if scan_id is not None:
            query = query.filter(Finding.scan_id == scan_id)
        elif project_id is not None:
            query = query.join(Scan).filter(Scan.project_id == project_id)

        by_severity = (
            query.with_entities(Finding.severity, func.count(Finding.id))
            .group_by(Finding.severity)
            .all()
        )
        total = query.count()
        verified = query.filter(Finding.verified == True).count()
        false_positives = query.filter(Finding.false_positive == True).count()

        summary = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for sev, count in by_severity:
            summary[sev.value if hasattr(sev, "value") else sev] = count

        return {
            **summary,
            "total": total,
            "verified": verified,
            "false_positives": false_positives,
        }


crud_result = CRUDResult(Finding)
