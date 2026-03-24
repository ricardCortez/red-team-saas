"""Tool configuration CRUD endpoints (Phase 3)

Complements the existing /tools/available and /tools/info endpoints
with CRUD management for tool configs stored in GenericToolConfig.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import get_db, get_current_user, require_role
from app.models.user import User
from app.models.generic_tool import GenericToolConfig

router = APIRouter()


@router.get("/configs")
async def list_tool_configs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    is_enabled: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List tool configurations"""
    query = db.query(GenericToolConfig)
    if is_enabled is not None:
        if hasattr(GenericToolConfig, "is_enabled"):
            query = query.filter(GenericToolConfig.is_enabled == is_enabled)
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/configs/{tool_id}")
async def get_tool_config(
    tool_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tool = db.get(GenericToolConfig, tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool config not found")
    return tool
