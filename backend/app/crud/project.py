"""CRUD for Project"""
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union, Any
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, desc
from app.crud.base import CRUDBase
from app.models.project import Project, ProjectStatus
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


    # ── Phase 9 helpers ───────────────────────────────────────────────────────

    def get_for_user(
        self,
        db: Session,
        user_id: int,
        status: Optional[ProjectStatus] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Project], int]:
        """Return projects visible to the user (admin sees all; others see membership)."""
        from app.models.user import User
        from app.models.project_member import ProjectMember

        user = db.query(User).filter(User.id == user_id).first()
        if user and user.is_superuser:
            q = db.query(Project).filter(Project.is_active == True)
        else:
            q = (
                db.query(Project)
                .join(ProjectMember, ProjectMember.project_id == Project.id)
                .filter(ProjectMember.user_id == user_id, Project.is_active == True)
            )

        if status:
            q = q.filter(Project.status == status)

        total = q.count()
        items = q.order_by(desc(Project.created_at)).offset(skip).limit(limit).all()
        return items, total

    def get_user_role(self, db: Session, project_id: int, user_id: int):
        """Return the ProjectRole of user in project, or None."""
        from app.models.project_member import ProjectMember
        member = (
            db.query(ProjectMember)
            .filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
            .first()
        )
        return member.role if member else None

    def can_manage(self, db: Session, project_id: int, user_id: int) -> bool:
        """True if user is LEAD, owner, or global superuser."""
        from app.models.user import User
        from app.models.project_member import ProjectRole

        user = db.query(User).filter(User.id == user_id).first()
        if user and user.is_superuser:
            return True

        project = db.query(Project).filter(Project.id == project_id).first()
        if project and project.owner_id == user_id:
            return True

        role = self.get_user_role(db, project_id, user_id)
        return role == ProjectRole.lead

    def archive(self, db: Session, project: Project) -> Project:
        project.status = ProjectStatus.archived
        project.archived_at = datetime.utcnow()
        db.commit()
        db.refresh(project)
        return project

    def create_with_owner_member(
        self, db: Session, *, obj_in: ProjectCreate, owner_id: int
    ) -> Project:
        """Create project AND auto-add owner as LEAD member."""
        from app.models.project_member import ProjectMember, ProjectRole

        data = self._to_json(jsonable_encoder(obj_in))
        data["owner_id"] = owner_id
        project = Project(**data)
        db.add(project)
        db.flush()

        member = ProjectMember(
            project_id=project.id,
            user_id=owner_id,
            role=ProjectRole.lead,
            added_by=owner_id,
        )
        db.add(member)
        db.commit()
        db.refresh(project)
        return project


crud_project = CRUDProject(Project)
