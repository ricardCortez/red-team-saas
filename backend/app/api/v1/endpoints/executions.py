"""Execution engine endpoints (Phase 4)"""
import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.task import Task, TaskStatusEnum
from app.models.user import User
from app.schemas.execution import ExecutionCreate, ExecutionResponse, ExecutionStatus
from app.core.tool_engine.tool_registry import ToolRegistry
import app.core.tool_definitions  # noqa: F401 — triggers registration

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=ExecutionResponse, status_code=202)
def create_execution(
    payload: ExecutionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create and enqueue a tool execution."""
    if not ToolRegistry.is_available(payload.tool_name):
        # Accept unknown tools in test/dev — still create the task
        try:
            ToolRegistry.get(payload.tool_name)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Tool '{payload.tool_name}' is not registered",
            )

    task = Task(
        name=f"{payload.tool_name} -> {payload.target}",
        tool_name=payload.tool_name,
        target=payload.target,
        options=payload.options or {},
        status=TaskStatusEnum.pending,
        user_id=current_user.id,
        project_id=payload.project_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Enqueue in Celery (skip if task_always_eager is already set by tests)
    try:
        from app.tasks.tool_executor import execute_tool
        job = execute_tool.apply_async(
            args=[
                task.id,
                payload.tool_name,
                payload.target,
                payload.options or {},
                current_user.id,
            ],
            queue="tool_execution",
            priority=payload.priority or 5,
        )
        task.celery_task_id = job.id
        db.commit()
    except Exception as exc:
        logger.warning(f"Celery enqueue failed (task still created): {exc}")

    db.refresh(task)
    return task


@router.get("/{task_id}/status", response_model=ExecutionStatus)
def get_execution_status(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.user_id != current_user.id and not current_user.is_superuser:
        role_val = (
            current_user.role.value
            if hasattr(current_user.role, "value")
            else current_user.role
        )
        if role_val == "viewer":
            raise HTTPException(status_code=403, detail="Forbidden")

    celery_state = None
    if task.celery_task_id:
        try:
            from app.tasks.celery_app import celery_app
            result = celery_app.AsyncResult(task.celery_task_id)
            celery_state = result.state
        except Exception:
            pass

    return ExecutionStatus(
        task_id=task.id,
        status=task.status,
        celery_state=celery_state,
        celery_task_id=task.celery_task_id,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.delete("/{task_id}", status_code=204)
def cancel_execution(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a pending or running execution."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status not in [TaskStatusEnum.pending, TaskStatusEnum.running]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel task in status: {task.status.value}",
        )
    if task.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Forbidden")

    if task.celery_task_id:
        try:
            from app.tasks.celery_app import celery_app
            celery_app.control.revoke(task.celery_task_id, terminate=True, signal="SIGTERM")
        except Exception:
            pass

    task.status = TaskStatusEnum.cancelled
    db.commit()


@router.get("/{task_id}/stream")
async def stream_execution_output(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Server-sent events stream of real-time tool output."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        try:
            from app.core.redis_client import redis_client
            pubsub = redis_client.pubsub()
            pubsub.subscribe(f"task:{task_id}:output")
        except Exception:
            yield f"data: {json.dumps({'event': 'error', 'detail': 'Redis unavailable'})}\n\n"
            return

        try:
            while True:
                message = pubsub.get_message(timeout=1.0)
                if message and message["type"] == "message":
                    data = json.loads(message["data"])
                    yield f"data: {json.dumps(data)}\n\n"

                task_state = (
                    db.query(Task.status).filter(Task.id == task_id).scalar()
                )
                if task_state in [
                    TaskStatusEnum.completed,
                    TaskStatusEnum.failed,
                    TaskStatusEnum.cancelled,
                ]:
                    yield f"data: {json.dumps({'event': 'done', 'status': task_state.value})}\n\n"
                    break

                await asyncio.sleep(0.1)
        finally:
            try:
                pubsub.unsubscribe()
            except Exception:
                pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("", response_model=list)
def list_available_tools(
    current_user: User = Depends(get_current_user),
):
    """List registered tools and their availability."""
    import app.core.tool_definitions  # noqa: F401
    tools = ToolRegistry.list_tools()
    return [
        {**info, "available": ToolRegistry.is_available(name)}
        for name, info in tools.items()
    ]
