"""Scan CRUD endpoints"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import get_db, get_current_user, require_role
from app.crud.scan import crud_scan
from app.schemas.scan import (
    ScanCreate, ScanUpdate,
    ScanResponse, ScanListResponse,
)
from app.models.user import User
from app.core.audit import log_action

router = APIRouter()


@router.get("/", response_model=ScanListResponse)
async def list_scans(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    project_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    scan_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = {"project_id": project_id, "status": status, "scan_type": scan_type}
    return crud_scan.get_multi(db, skip=skip, limit=limit, filters=filters)


@router.post("/", response_model=ScanResponse, status_code=status.HTTP_201_CREATED)
async def create_scan(
    scan_in: ScanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester"])),
):
    scan = crud_scan.create(db, obj_in=scan_in, created_by=current_user.id)
    await log_action(db, user_id=current_user.id, action="scan.create", resource_id=scan.id)
    # Queue Celery task in a thread to avoid blocking the async event loop
    import asyncio
    def _queue_task():
        try:
            from app.tasks.scan_tasks import execute_scan
            return execute_scan.delay(scan.id)
        except Exception:
            return None
    try:
        loop = asyncio.get_event_loop()
        task = await asyncio.wait_for(
            loop.run_in_executor(None, _queue_task),
            timeout=3.0,
        )
        if task:
            crud_scan.update(db, db_obj=scan, obj_in={"celery_task_id": task.id, "status": "pending"})
    except Exception:
        pass  # Celery unavailable; scan stays pending
    return scan


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(
    scan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scan = crud_scan.get(db, id=scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@router.put("/{scan_id}", response_model=ScanResponse)
async def update_scan(
    scan_id: int,
    scan_in: ScanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester"])),
):
    scan = crud_scan.get(db, id=scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return crud_scan.update(db, db_obj=scan, obj_in=scan_in)


@router.post("/{scan_id}/cancel", response_model=ScanResponse)
async def cancel_scan(
    scan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester"])),
):
    scan = crud_scan.get(db, id=scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    scan_status = scan.status.value if hasattr(scan.status, "value") else scan.status
    if scan_status not in ("pending", "running"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel scan in status: {scan_status}",
        )
    if scan.celery_task_id:
        try:
            from app.workers.celery_app import celery_app
            celery_app.control.revoke(scan.celery_task_id, terminate=True)
        except Exception:
            pass
    updated = crud_scan.update(db, db_obj=scan, obj_in={"status": "cancelled"})
    await log_action(db, user_id=current_user.id, action="scan.cancel", resource_id=scan_id)
    return updated


@router.delete("/{scan_id}", status_code=204)
async def delete_scan(
    scan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester"])),
):
    scan = crud_scan.get(db, id=scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    db.delete(scan)
    db.commit()
    await log_action(db, user_id=current_user.id, action="scan.delete", resource_id=scan_id)


@router.post("/{scan_id}/run", response_model=ScanResponse)
async def run_scan(
    scan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "manager", "pentester"])),
):
    """Manually trigger/re-trigger a pending scan."""
    scan = crud_scan.get(db, id=scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    scan_status = scan.status.value if hasattr(scan.status, "value") else scan.status
    if scan_status not in ("pending", "failed"):
        raise HTTPException(status_code=400, detail=f"Cannot run scan in status: {scan_status}")
    import asyncio
    def _queue_run():
        try:
            from app.tasks.scan_tasks import execute_scan
            return execute_scan.delay(scan.id)
        except Exception:
            return None
    try:
        loop = asyncio.get_event_loop()
        task = await asyncio.wait_for(loop.run_in_executor(None, _queue_run), timeout=3.0)
        if task:
            updated = crud_scan.update(db, db_obj=scan, obj_in={"celery_task_id": task.id, "status": "pending"})
        else:
            updated = crud_scan.update(db, db_obj=scan, obj_in={"status": "pending"})
    except Exception:
        updated = crud_scan.update(db, db_obj=scan, obj_in={"status": "pending"})
    await log_action(db, user_id=current_user.id, action="scan.run", resource_id=scan_id)
    return updated


@router.get("/{scan_id}/progress")
async def get_scan_progress(
    scan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scan = crud_scan.get(db, id=scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    progress = scan.progress
    try:
        from app.core.redis import redis_client
        redis_val = await redis_client.get(f"scan:{scan_id}:progress")
        if redis_val is not None:
            progress = int(redis_val)
    except Exception:
        pass
    scan_status = scan.status.value if hasattr(scan.status, "value") else scan.status
    return {
        "scan_id": scan_id,
        "status": scan_status,
        "progress": progress,
        "celery_task_id": scan.celery_task_id,
    }
