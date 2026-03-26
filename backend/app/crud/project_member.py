"""CRUD for ProjectMember"""
from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.project_member import ProjectMember, ProjectRole


class CRUDProjectMember:

    def add(
        self,
        db: Session,
        project_id: int,
        user_id: int,
        role: ProjectRole,
        added_by: int,
    ) -> ProjectMember:
        """Add or update a member's role in a project."""
        existing = (
            db.query(ProjectMember)
            .filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
            .first()
        )
        if existing:
            existing.role = role
            db.commit()
            db.refresh(existing)
            return existing

        member = ProjectMember(
            project_id=project_id,
            user_id=user_id,
            role=role,
            added_by=added_by,
        )
        db.add(member)
        db.commit()
        db.refresh(member)
        return member

    def remove(self, db: Session, project_id: int, user_id: int) -> bool:
        member = (
            db.query(ProjectMember)
            .filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
            .first()
        )
        if not member:
            return False
        db.delete(member)
        db.commit()
        return True

    def list_members(self, db: Session, project_id: int) -> List[ProjectMember]:
        return (
            db.query(ProjectMember)
            .filter(ProjectMember.project_id == project_id)
            .all()
        )

    def get_role(
        self, db: Session, project_id: int, user_id: int
    ) -> Optional[ProjectRole]:
        member = (
            db.query(ProjectMember)
            .filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
            .first()
        )
        return member.role if member else None


crud_project_member = CRUDProjectMember()
