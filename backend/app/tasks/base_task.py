"""Base Celery task with DB lifecycle hooks"""
import logging
from celery import Task
from app.database import SessionLocal
from app.models.task import Task as TaskModel, TaskStatusEnum

logger = logging.getLogger(__name__)


class BaseRedTeamTask(Task):
    abstract = True
    _db = None

    @property
    def db(self):
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def on_success(self, retval, task_id, args, kwargs):
        self._update_task_status(task_id, TaskStatusEnum.completed)
        self._close_db()

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        self._update_task_status(task_id, TaskStatusEnum.failed, error=str(exc))
        self._close_db()

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        self._update_task_status(task_id, TaskStatusEnum.retrying)

    def _update_task_status(
        self, celery_task_id: str, status: TaskStatusEnum, error: str = None
    ) -> None:
        try:
            db = SessionLocal()
            task = (
                db.query(TaskModel)
                .filter(TaskModel.celery_task_id == celery_task_id)
                .first()
            )
            if task:
                task.status = status
                if error:
                    task.error_message = error
                db.commit()
        except Exception as exc:
            logger.error(f"Failed to update task status: {exc}")
        finally:
            db.close()

    def _close_db(self) -> None:
        if self._db:
            self._db.close()
            self._db = None
