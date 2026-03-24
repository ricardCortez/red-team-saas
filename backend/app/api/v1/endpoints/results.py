"""Result (Finding) endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import get_db, get_current_user, require_role
from app.crud.result import crud_result
from app.schemas.result import (
    ResultCreate, ResultUpdate,
    ResultResponse, ResultListResponse, ResultSummary,
)
from app.models.user import User

router = APIRouter()


@router.get("/summary", response_model=ResultSummary)
async def get_results_summary(
    scan_id: Optional[int] = Query(None),
    project_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return crud_result.get_summary(db, scan_id=scan_id, project_id=project_id)


@router.get("/", response_model=ResultListResponse)
async def list_results(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    scan_id: Optional[int] = Query(None),
    severity: Optional[str] = Query(None),
    verified: Optional[bool] = Query(None),
    false_positive: Optional[bool] = Query(None),
    tool: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = {
        "scan_id": scan_id,
        "severity": severity,
        "verified": verified,
        "false_positive": false_positive,
        "tool": tool,
    }
    return crud_result.get_multi(db, skip=skip, limit=limit, filters=filters)


@router.post("/", response_model=ResultResponse, status_code=201)
async def create_result(
    result_in: ResultCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester"])),
):
    return crud_result.create(db, obj_in=result_in)


@router.get("/{result_id}", response_model=ResultResponse)
async def get_result(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = crud_result.get(db, id=result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return result


@router.put("/{result_id}", response_model=ResultResponse)
async def update_result(
    result_id: int,
    result_in: ResultUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester"])),
):
    result = crud_result.get(db, id=result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return crud_result.update(db, db_obj=result, obj_in=result_in)


@router.post("/{result_id}/verify", response_model=ResultResponse)
async def verify_result(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester"])),
):
    result = crud_result.get(db, id=result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return crud_result.update(
        db, db_obj=result, obj_in={"verified": True, "verified_by": current_user.id}
    )


@router.post("/{result_id}/false-positive", response_model=ResultResponse)
async def mark_false_positive(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester"])),
):
    result = crud_result.get(db, id=result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return crud_result.update(db, db_obj=result, obj_in={"false_positive": True})
