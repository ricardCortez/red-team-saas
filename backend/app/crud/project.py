"""CRUD for Project"""
import json
from typing import Dict, Optional, Union, Any
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.crud.base import CRUDBase
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate

_JSON_LIST_FIELDS = ("tags", "compliance")


class CRUDProject(CRUDBase[Project, ProjectCreate, ProjectUpdate]):

    @staticmethod
    def _to_json(data: dict) -> dict:
        for field in _JSON_LIST_FIELDS:
            if field in data and not isinstance(data[field], str):
                data[field] = json.dumps(data[field]) if data[field] is not None else None
        return data

    def create(self, db: Session, *, obj_in: ProjectCreate, **kwargs) -> Project:
        data = self._to_json(jsonable_encoder(obj_in))
        data.update(kwargs)
        db_obj = Project(**data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: Project, obj_in: Union[ProjectUpdate, Dict[str, Any]]) -> Project:
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
        search: Optional[str] = None,
    ) -> Dict:
        query = db.query(Project).filter(Project.is_active == True)

        if filters:
            if filters.get("owner_id"):
                query = query.filter(Project.owner_id == filters["owner_id"])
            if filters.get("status"):
                query = query.filter(Project.status == filters["status"])
            if filters.get("scope"):
                query = query.filter(Project.scope == filters["scope"])

        if search:
            query = query.filter(
                or_(
                    Project.name.ilike(f"%{search}%"),
                    Project.target.ilike(f"%{search}%"),
                    Project.client_name.ilike(f"%{search}%"),
                )
            )

        total = query.with_entities(func.count()).scalar()
        items = query.order_by(Project.created_at.desc()).offset(skip).limit(limit).all()
        return {"items": items, "total": total, "skip": skip, "limit": limit}

    def get_stats(self, db: Session, project_id: int) -> Dict:
        from app.models.scan import Scan
        from app.models.finding import Finding, Severity

        scan_count = (
            db.query(func.count(Scan.id))
            .filter(Scan.project_id == project_id)
            .scalar()
        )
        results_by_severity = (
            db.query(Finding.severity, func.count(Finding.id))
            .join(Scan)
            .filter(Scan.project_id == project_id)
            .group_by(Finding.severity)
            .all()
        )
        return {
            "scan_count": scan_count,
            "findings": {sev: count for sev, count in results_by_severity},
        }


crud_project = CRUDProject(Project)
