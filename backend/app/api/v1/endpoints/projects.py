"""Project CRUD endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import get_db, get_current_user, require_role
from app.crud.project import crud_project
from app.schemas.project import (
    ProjectCreate, ProjectUpdate,
    ProjectResponse, ProjectListResponse,
)
from app.models.user import User
from app.core.audit import log_action

router = APIRouter()


@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    scope: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = {"status": status, "scope": scope}
    if not current_user.is_superuser:
        filters["owner_id"] = current_user.id
    return crud_project.get_multi(db, skip=skip, limit=limit, filters=filters, search=search)


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester"])),
):
    project = crud_project.create(db, obj_in=project_in, owner_id=current_user.id)
    await log_action(db, user_id=current_user.id, action="project.create", resource_id=project.id)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = crud_project.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not current_user.is_superuser and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_in: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester"])),
):
    project = crud_project.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not current_user.is_superuser and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    project = crud_project.update(db, db_obj=project, obj_in=project_in)
    await log_action(db, user_id=current_user.id, action="project.update", resource_id=project.id)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
):
    project = crud_project.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    crud_project.soft_delete(db, id=project_id)
    await log_action(db, user_id=current_user.id, action="project.delete", resource_id=project_id)


@router.get("/{project_id}/stats")
async def get_project_stats(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = crud_project.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not current_user.is_superuser and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return crud_project.get_stats(db, project_id=project_id)
