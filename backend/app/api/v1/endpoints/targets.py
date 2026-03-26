"""Targets endpoints – scoped targets per project (Phase 9)"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import get_db, get_current_user
from app.crud.target import crud_target
from app.models.user import User
from app.models.target import Target, TargetStatus
from app.models.project_member import ProjectRole
from app.schemas.target import TargetCreate, TargetUpdate, TargetResponse, TargetBulkCreate
from app.core.scope_validator import ScopeValidator

router = APIRouter()


def _get_target_or_404(target_id: int, project_id: int, db: Session) -> Target:
    target = (
        db.query(Target)
        .filter(Target.id == target_id, Target.project_id == project_id)
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    return target


@router.get("/projects/{project_id}/targets")
def list_targets(
    project_id: int,
    status: Optional[TargetStatus] = Query(None),
    skip:  int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = crud_target.get_by_project(
        db, project_id, status=status, skip=skip, limit=limit
    )
    return {"total": total, "items": [TargetResponse.model_validate(t) for t in items]}


@router.post("/projects/{project_id}/targets", response_model=TargetResponse, status_code=201)
def add_target(
    project_id: int,
    payload: TargetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target = crud_target.create(db, project_id, current_user.id, payload)
    return target


@router.post("/projects/{project_id}/targets/bulk", status_code=201)
def bulk_add_targets(
    project_id: int,
    payload: TargetBulkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Import multiple targets at once."""
    created = crud_target.bulk_create(db, project_id, current_user.id, payload.targets)
    return [TargetResponse.model_validate(t) for t in created]


@router.patch(
    "/projects/{project_id}/targets/{target_id}",
    response_model=TargetResponse,
)
def update_target(
    project_id: int,
    target_id: int,
    payload: TargetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target = _get_target_or_404(target_id, project_id, db)
    return crud_target.update(db, target, payload)


@router.delete("/projects/{project_id}/targets/{target_id}", status_code=204)
def delete_target(
    project_id: int,
    target_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target = _get_target_or_404(target_id, project_id, db)
    crud_target.delete(db, target)


@router.post("/projects/{project_id}/targets/validate")
def validate_scope(
    project_id: int,
    target: str = Query(..., description="Target value to validate (IP, hostname, URL)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check whether a target string is within the project's authorised scope."""
    validator = ScopeValidator(db, project_id)
    allowed = validator.is_allowed(target)
    return {"target": target, "in_scope": allowed, "project_id": project_id}
