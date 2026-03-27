"""Celery tasks for running Alembic database migrations."""
import subprocess
import sys
from pathlib import Path

from app.tasks.celery_app import celery_app


@celery_app.task(name="migration_tasks.run_alembic_upgrade", bind=True, max_retries=3)
def run_alembic_upgrade(self):
    """Run alembic upgrade head to apply all pending migrations."""
    backend_dir = Path(__file__).resolve().parents[2]
    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=str(backend_dir),
            capture_output=True,
            text=True,
            timeout=120,
        )
        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "error": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired as exc:
        return {"status": "error", "output": "", "error": "Migration timed out after 120s", "returncode": -1}
    except Exception as exc:
        return {"status": "error", "output": "", "error": str(exc), "returncode": -1}


@celery_app.task(name="migration_tasks.run_alembic_downgrade", bind=True, max_retries=1)
def run_alembic_downgrade(self, revision: str):
    """Run alembic downgrade to a specific revision.

    Args:
        revision: Target revision identifier (e.g. '-1', 'base', or a revision hash).
    """
    backend_dir = Path(__file__).resolve().parents[2]
    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "downgrade", revision],
            cwd=str(backend_dir),
            capture_output=True,
            text=True,
            timeout=120,
        )
        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "error": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "output": "", "error": "Downgrade timed out after 120s", "returncode": -1}
    except Exception as exc:
        return {"status": "error", "output": "", "error": str(exc), "returncode": -1}
