"""CRUD for Scan"""
import json
from typing import Dict, Union, Any
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.crud.base import CRUDBase
from app.models.scan import Scan
from app.schemas.scan import ScanCreate, ScanUpdate

_JSON_FIELDS = ("tools",)  # Text columns that hold JSON arrays


class CRUDScan(CRUDBase[Scan, ScanCreate, ScanUpdate]):

    @staticmethod
    def _to_json(data: dict) -> dict:
        for field in _JSON_FIELDS:
            if field in data and not isinstance(data[field], str):
                data[field] = json.dumps(data[field]) if data[field] is not None else None
        return data

    def create(self, db: Session, *, obj_in: ScanCreate, **kwargs) -> Scan:
        data = self._to_json(jsonable_encoder(obj_in))
        data.update(kwargs)
        db_obj = Scan(**data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: Scan, obj_in: Union[ScanUpdate, Dict[str, Any]]) -> Scan:
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
        limit: int = 20,
        filters: Dict = None,
    ) -> Dict:
        query = db.query(Scan)

        if filters:
            if filters.get("project_id") is not None:
                query = query.filter(Scan.project_id == filters["project_id"])
            if filters.get("status"):
                query = query.filter(Scan.status == filters["status"])
            if filters.get("scan_type"):
                query = query.filter(Scan.scan_type == filters["scan_type"])
            if filters.get("created_by") is not None:
                query = query.filter(Scan.created_by == filters["created_by"])

        total = query.with_entities(func.count()).scalar()
        items = query.order_by(Scan.created_at.desc()).offset(skip).limit(limit).all()
        return {"items": items, "total": total, "skip": skip, "limit": limit}


crud_scan = CRUDScan(Scan)
