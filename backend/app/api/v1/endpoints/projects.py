"""Project endpoints – Phase 3 (original) + Phase 9 (members, archive, activity)"""
from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.orm import Session
from typing import Optional, List

from app.api.deps import get_db, get_current_user, require_role
from app.crud.project import crud_project
from app.crud.project_member import crud_project_member
from app.schemas.project import (
    ProjectCreate, ProjectUpdate,
    ProjectResponse, ProjectListResponse,
)
from app.schemas.project_member import MemberAdd, MemberResponse
from app.models.user import User
from app.models.project import Project, ProjectStatus
from app.models.project_member import ProjectRole
from app.core.audit import log_action, create_audit_log

router = APIRouter()


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_project_or_404(project_id: int, db: Session) -> Project:
    project = crud_project.get(db, id=project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _require_project_access(
    project_id: int,
    user_id: int,
    db: Session,
    min_role: ProjectRole = ProjectRole.viewer,
) -> None:
    """Raise 403 unless user is superuser or has at least *min_role* in project."""
    from app.models.user import User as UserModel
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if user and user.is_superuser:
        return

    role = crud_project.get_user_role(db, project_id, user_id)
    if role is None:
        raise HTTPException(status_code=403, detail="Not a member of this project")

    order = [ProjectRole.viewer, ProjectRole.operator, ProjectRole.lead]
    if order.index(role) < order.index(min_role):
        raise HTTPException(
            status_code=403, detail=f"Requires at least '{min_role.value}' role"
        )


def _enrich(project: Project) -> dict:
    """Add member_count / target_count to a ProjectResponse dict."""
    data = ProjectResponse.model_validate(project).model_dump()
    data["member_count"] = len(project.members) if project.members is not None else 0
    data["target_count"] = len(project.targets) if project.targets is not None else 0
    return data


# ── LEGACY Phase-3 routes (kept for backward compat) ──────────────────────────

@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    skip:   int = Query(0, ge=0),
    limit:  int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    scope:  Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = {"status": status, "scope": scope}
    if not current_user.is_superuser:
        filters["owner_id"] = current_user.id
    return crud_project.get_multi(db, skip=skip, limit=limit, filters=filters, search=search)


@router.post("/", response_model=ProjectResponse, status_code=http_status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester"])),
):
    project = crud_project.create_with_owner_member(db, obj_in=project_in, owner_id=current_user.id)
    await log_action(db, user_id=current_user.id, action="project.create", resource_id=project.id)
    return _enrich(project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_or_404(project_id, db)
    if not current_user.is_superuser and project.owner_id != current_user.id:
        # also allow project members
        role = crud_project.get_user_role(db, project_id, current_user.id)
        if role is None:
            raise HTTPException(status_code=403, detail="Not enough permissions")
    return _enrich(project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project_put(
    project_id: int,
    project_in: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester"])),
):
    project = _get_project_or_404(project_id, db)
    if not current_user.is_superuser and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    project = crud_project.update(db, db_obj=project, obj_in=project_in)
    await log_action(db, user_id=current_user.id, action="project.update", resource_id=project.id)
    return _enrich(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project_patch(
    project_id: int,
    project_in: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_project_access(project_id, current_user.id, db, min_role=ProjectRole.lead)
    project = _get_project_or_404(project_id, db)
    project = crud_project.update(db, db_obj=project, obj_in=project_in)
    create_audit_log(
        db=db, user_id=current_user.id,
        action="project_updated", resource="project", resource_id=project_id,
    )
    return _enrich(project)


@router.delete("/{project_id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
):
    project = _get_project_or_404(project_id, db)
    crud_project.soft_delete(db, id=project_id)
    await log_action(db, user_id=current_user.id, action="project.delete", resource_id=project_id)


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/{project_id}/stats")
async def get_project_stats(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project_or_404(project_id, db)
    if not current_user.is_superuser and project.owner_id != current_user.id:
        role = crud_project.get_user_role(db, project_id, current_user.id)
        if role is None:
            raise HTTPException(status_code=403, detail="Not enough permissions")

    try:
        from app.core.analytics.metrics import MetricsEngine
        from app.core.analytics.trends import TrendsEngine
        return {
            "summary": MetricsEngine.project_summary(db, project_id),
            "recent_trend": TrendsEngine.findings_over_time(
                db, current_user.id, days=14, project_id=project_id
            ),
        }
    except Exception:
        # Fall back to legacy stats if analytics not available
        return crud_project.get_stats(db, project_id=project_id)


# ── Archive ───────────────────────────────────────────────────────────────────

@router.post("/{project_id}/archive", response_model=ProjectResponse)
def archive_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not crud_project.can_manage(db, project_id, current_user.id):
        raise HTTPException(
            status_code=403,
            detail="Only project owner, LEAD member, or admin can archive",
        )
    project = _get_project_or_404(project_id, db)
    if project.status == ProjectStatus.archived:
        raise HTTPException(status_code=400, detail="Project already archived")
    project = crud_project.archive(db, project)
    create_audit_log(
        db=db, user_id=current_user.id,
        action="project_archived", resource="project", resource_id=project_id,
    )
    return _enrich(project)


# ── Members ───────────────────────────────────────────────────────────────────

@router.get("/{project_id}/members", response_model=List[MemberResponse])
def list_members(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_project_access(project_id, current_user.id, db)
    return crud_project_member.list_members(db, project_id)


@router.post(
    "/{project_id}/members",
    response_model=MemberResponse,
    status_code=http_status.HTTP_201_CREATED,
)
def add_member(
    project_id: int,
    payload: MemberAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_project_access(project_id, current_user.id, db, min_role=ProjectRole.lead)
    member = crud_project_member.add(
        db, project_id, payload.user_id, payload.role, current_user.id
    )
    create_audit_log(
        db=db, user_id=current_user.id,
        action="member_added", resource="project", resource_id=project_id,
        details={"added_user": payload.user_id, "role": payload.role.value},
    )
    return member


@router.delete("/{project_id}/members/{user_id}", status_code=http_status.HTTP_204_NO_CONTENT)
def remove_member(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_project_access(project_id, current_user.id, db, min_role=ProjectRole.lead)
    project = _get_project_or_404(project_id, db)
    if project.owner_id == user_id:
        raise HTTPException(status_code=400, detail="Cannot remove project owner")
    removed = crud_project_member.remove(db, project_id, user_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Member not found")


# ── Activity log ──────────────────────────────────────────────────────────────

@router.get("/{project_id}/activity")
def project_activity(
    project_id: int,
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_project_access(project_id, current_user.id, db)
    from app.models.audit_log import AuditLog
    rows = (
        db.query(AuditLog)
        .filter(AuditLog.resource == str(project_id))
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return rows
