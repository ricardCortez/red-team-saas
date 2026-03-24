"""Main Celery task: execute a red team tool"""
import json
import logging

from celery import shared_task

from app.tasks.base_task import BaseRedTeamTask
from app.core.tool_engine.tool_registry import ToolRegistry
from app.core.tool_engine.executor import SubprocessExecutor
from app.database import SessionLocal
from app.models.task import Task as TaskModel, TaskStatusEnum
from app.models.result import Result
from app.core.security import EncryptionHandler
from app.core.audit import create_audit_log

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    base=BaseRedTeamTask,
    name="app.tasks.tool_executor.execute_tool",
    max_retries=2,
    default_retry_delay=60,
    autoretry_for=(ConnectionError,),
    retry_backoff=True,
)
def execute_tool(
    self,
    task_id: int,
    tool_name: str,
    target: str,
    options: dict,
    user_id: int,
):
    db = SessionLocal()
    task_obj = None
    output_lines = []

    try:
        task_obj = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        if not task_obj:
            raise ValueError(f"Task {task_id} not found")

        task_obj.status = TaskStatusEnum.running
        task_obj.celery_task_id = self.request.id
        db.commit()

        def on_output(line: str):
            output_lines.append(line)
            try:
                from app.core.redis_client import redis_client
                redis_client.publish(
                    f"task:{task_id}:output",
                    json.dumps({"line": line, "task_id": task_id}),
                )
            except Exception:
                pass  # Redis unavailable — continue without streaming

        tool_class = ToolRegistry.get(tool_name)
        tool_instance = tool_class()
        executor = SubprocessExecutor(output_callback=on_output)
        result = executor.execute(tool_instance, target, options)

        result_obj = Result(
            task_id=task_id,
            tool_name=tool_name,
            tool=tool_name,
            target=target,
            raw_output=EncryptionHandler.encrypt(result.raw_output) if result.raw_output else None,
            parsed_output=result.parsed_output,
            findings=result.findings,
            risk_score=result.risk_score,
            exit_code=result.exit_code,
            duration_seconds=result.duration_seconds,
            success=result.success,
            error_message=result.error,
        )
        db.add(result_obj)

        task_obj.status = (
            TaskStatusEnum.completed if result.success else TaskStatusEnum.failed
        )
        task_obj.error_message = result.error
        db.commit()

        create_audit_log(
            db=db,
            user_id=user_id,
            action="tool_execution_completed",
            resource="task",
            resource_id=task_id,
            details={
                "tool": tool_name,
                "target": target,
                "success": result.success,
                "risk_score": result.risk_score,
            },
        )

        return {
            "task_id": task_id,
            "success": result.success,
            "risk_score": result.risk_score,
            "findings_count": len(result.findings),
            "duration": result.duration_seconds,
        }

    except Exception as exc:
        logger.error(f"Task {task_id} failed: {exc}")
        try:
            if task_obj is None:
                task_obj = db.query(TaskModel).filter(TaskModel.id == task_id).first()
            if task_obj:
                task_obj.status = TaskStatusEnum.failed
                task_obj.error_message = str(exc)
                db.commit()
        except Exception:
            pass
        raise self.retry(exc=exc)
    finally:
        db.close()
