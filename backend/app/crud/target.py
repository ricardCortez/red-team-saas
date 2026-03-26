"""CRUD for Target"""
from sqlalchemy.orm import Session
from typing import List, Tuple, Optional

from app.models.target import Target, TargetStatus
from app.schemas.target import TargetCreate, TargetUpdate


class CRUDTarget:

    def create(
        self,
        db: Session,
        project_id: int,
        user_id: int,
        payload: TargetCreate,
    ) -> Target:
        target = Target(
            project_id=project_id,
            added_by=user_id,
            value=payload.value,
            target_type=payload.target_type,
            status=payload.status or TargetStatus.in_scope,
            description=payload.description,
            tags=payload.tags,
        )
        db.add(target)
        db.commit()
        db.refresh(target)
        return target

    def get_by_project(
        self,
        db: Session,
        project_id: int,
        status: Optional[TargetStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Target], int]:
        q = db.query(Target).filter(Target.project_id == project_id)
        if status:
            q = q.filter(Target.status == status)
        total = q.count()
        items = q.offset(skip).limit(limit).all()
        return items, total

    def get(self, db: Session, target_id: int) -> Optional[Target]:
        return db.query(Target).filter(Target.id == target_id).first()

    def update(self, db: Session, target: Target, payload: TargetUpdate) -> Target:
        for field, value in payload.model_dump(exclude_none=True).items():
            setattr(target, field, value)
        db.commit()
        db.refresh(target)
        return target

    def bulk_create(
        self,
        db: Session,
        project_id: int,
        user_id: int,
        targets: List[TargetCreate],
    ) -> List[Target]:
        objs = [
            Target(
                project_id=project_id,
                added_by=user_id,
                value=t.value,
                target_type=t.target_type,
                status=t.status or TargetStatus.in_scope,
                description=t.description,
                tags=t.tags,
            )
            for t in targets
        ]
        db.add_all(objs)
        db.commit()
        for obj in objs:
            db.refresh(obj)
        return objs

    def delete(self, db: Session, target: Target) -> None:
        db.delete(target)
        db.commit()


crud_target = CRUDTarget()
