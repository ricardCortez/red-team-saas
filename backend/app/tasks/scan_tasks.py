"""Celery task for real scan execution — runs each tool sequentially."""
import json
import logging
from datetime import datetime, timezone

from app.tasks.celery_app import celery_app
from app.tasks.base_task import BaseRedTeamTask

# Import tool definitions so they auto-register in ToolRegistry
import app.core.tool_definitions  # noqa: F401

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    base=BaseRedTeamTask,
    name="app.tasks.scan_tasks.execute_scan",
    max_retries=1,
    default_retry_delay=30,
)
def execute_scan(self, scan_id: int):
    """Execute all tools listed in a scan sequentially."""
    from app.database import SessionLocal
    from app.models.scan import Scan, ScanStatus
    from app.models.task import Task as TaskModel, TaskStatusEnum
    from app.models.result import Result
    from app.core.tool_engine.tool_registry import ToolRegistry
    from app.core.tool_engine.executor import SubprocessExecutor
    from app.core.findings_processor import process_result_findings

    db = SessionLocal()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            logger.warning("execute_scan: scan %s not found", scan_id)
            return {"scan_id": scan_id, "status": "not_found"}

        # Parse tools and options from JSON columns
        try:
            tools: list = json.loads(scan.tools) if scan.tools else []
        except (json.JSONDecodeError, TypeError):
            tools = []

        try:
            # EncryptedString auto-decrypts to a JSON string on read
            options: dict = json.loads(scan.options) if scan.options else {}
        except (json.JSONDecodeError, TypeError):
            options = {}

        if not tools:
            scan.status = ScanStatus.completed
            scan.progress = 100
            scan.completed_at = datetime.now(timezone.utc)
            db.commit()
            return {"scan_id": scan_id, "status": "completed", "tools": 0}

        # Mark scan as running
        scan.status = ScanStatus.running
        if not scan.started_at:
            scan.started_at = datetime.now(timezone.utc)
        scan.progress = 0
        db.commit()

        total = len(tools)
        completed = 0
        any_success = False

        for tool_name in tools:
            task_obj = None
            try:
                # Create a Task record for this tool execution
                task_obj = TaskModel(
                    name=f"{scan.name} — {tool_name}",
                    user_id=scan.created_by,
                    project_id=scan.project_id,
                    status=TaskStatusEnum.running,
                    tool_name=tool_name,
                    target=scan.target,
                    options=options,
                )
                db.add(task_obj)
                db.commit()
                db.refresh(task_obj)

                output_lines = []

                def _on_output(line: str, _task_id=task_obj.id):
                    output_lines.append(line)
                    try:
                        from app.core.redis_client import redis_client
                        redis_client.publish(
                            f"task:{_task_id}:output",
                            json.dumps({"line": line, "task_id": _task_id}),
                        )
                    except Exception:
                        pass

                tool_class = ToolRegistry.get(tool_name)
                tool_instance = tool_class()
                executor = SubprocessExecutor(output_callback=_on_output)
                result = executor.execute(tool_instance, scan.target, options)

                # Persist result
                result_obj = Result(
                    task_id=task_obj.id,
                    tool_name=tool_name,
                    tool=tool_name,
                    target=scan.target,
                    raw_output=result.raw_output,
                    parsed_output=result.parsed_output,
                    findings=result.findings,
                    risk_score=result.risk_score,
                    exit_code=result.exit_code,
                    duration_seconds=result.duration_seconds,
                    success=result.success,
                    error_message=result.error,
                )
                db.add(result_obj)
                task_obj.status = TaskStatusEnum.completed if result.success else TaskStatusEnum.failed
                task_obj.error_message = result.error
                db.commit()
                db.refresh(result_obj)

                # Extract findings → Finding rows with scan_id pre-set
                if result.findings:
                    try:
                        # process_result_findings commits internally; pass scan_id via result_obj
                        result_obj.scan_id = scan_id if hasattr(result_obj, "scan_id") else None
                        created = process_result_findings(db, result_obj)
                        # Back-fill scan_id on any findings that missed it
                        needs_commit = False
                        for f in created:
                            if not f.scan_id:
                                f.scan_id = scan_id
                                needs_commit = True
                        if needs_commit:
                            db.commit()
                    except Exception as fp_exc:
                        logger.warning("findings_processor failed (scan %s, tool %s): %s", scan_id, tool_name, fp_exc)

                if result.success:
                    any_success = True

            except ValueError as ve:
                # Tool not registered (not installed or unknown name)
                logger.warning("execute_scan: tool '%s' not in registry: %s", tool_name, ve)
                if task_obj:
                    task_obj.status = TaskStatusEnum.failed
                    task_obj.error_message = str(ve)
                    db.commit()

            except Exception as exc:
                logger.error("execute_scan: tool '%s' failed for scan %s: %s", tool_name, scan_id, exc)
                if task_obj:
                    try:
                        task_obj.status = TaskStatusEnum.failed
                        task_obj.error_message = str(exc)
                        db.commit()
                    except Exception:
                        pass

            finally:
                completed += 1
                progress = int(completed / total * 100)
                scan.progress = progress
                db.commit()
                # Publish progress to Redis for real-time polling
                try:
                    from app.core.redis_client import redis_client
                    redis_client.set(f"scan:{scan_id}:progress", str(progress), ex=3600)
                except Exception:
                    pass

        # Finalise scan
        scan.status = ScanStatus.completed if any_success else ScanStatus.failed
        scan.progress = 100
        scan.completed_at = datetime.now(timezone.utc)
        db.commit()

        logger.info("execute_scan: scan %s done — status=%s tools=%s", scan_id, scan.status, total)
        return {"scan_id": scan_id, "status": scan.status.value, "tools": total}

    except Exception as exc:
        logger.exception("execute_scan: unhandled error for scan %s: %s", scan_id, exc)
        try:
            scan = db.query(Scan).filter(Scan.id == scan_id).first()
            if scan:
                scan.status = ScanStatus.failed
                scan.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            pass
        raise self.retry(exc=exc)
    finally:
        db.close()
