"""Phase 4: add execution engine fields to tasks and results

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Add 'retrying' to the taskstatusenum PostgreSQL enum (if using native enum)
    # Using try/except so this is safe whether the column is VARCHAR or native ENUM
    try:
        op.execute("ALTER TYPE taskstatusenum ADD VALUE IF NOT EXISTS 'retrying'")
    except Exception:
        pass  # SQLite (tests) or enum not yet created

    # ── tasks: new Phase 4 columns ────────────────────────────────────────────
    op.add_column("tasks", sa.Column("name", sa.String(500), nullable=True))
    op.add_column("tasks", sa.Column("target", sa.String(1024), nullable=True))
    op.add_column("tasks", sa.Column("options", sa.JSON(), nullable=True))
    op.add_column("tasks", sa.Column("celery_task_id", sa.String(255), nullable=True))
    op.add_column("tasks", sa.Column("error_message", sa.Text(), nullable=True))
    op.add_column(
        "tasks",
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id"),
            nullable=True,
        ),
    )

    try:
        op.create_index("ix_tasks_celery_task_id", "tasks", ["celery_task_id"])
        op.create_index("ix_tasks_project_id", "tasks", ["project_id"])
    except Exception:
        pass

    # ── results: new Phase 4 columns ──────────────────────────────────────────
    op.add_column("results", sa.Column("tool_name", sa.String(255), nullable=True))
    op.add_column("results", sa.Column("target", sa.String(1024), nullable=True))
    op.add_column("results", sa.Column("raw_output", sa.Text(), nullable=True))
    op.add_column("results", sa.Column("parsed_output", sa.JSON(), nullable=True))
    op.add_column("results", sa.Column("findings", sa.JSON(), nullable=True))
    op.add_column("results", sa.Column("risk_score", sa.Float(), nullable=True, server_default="0.0"))
    op.add_column("results", sa.Column("exit_code", sa.Integer(), nullable=True, server_default="0"))
    op.add_column("results", sa.Column("duration_seconds", sa.Float(), nullable=True, server_default="0.0"))
    op.add_column("results", sa.Column("success", sa.Boolean(), nullable=True, server_default="false"))
    op.add_column("results", sa.Column("error_message", sa.Text(), nullable=True))

    # Make existing 'tool' column nullable (some results may be created without it)
    op.alter_column("results", "tool", nullable=True)


def downgrade() -> None:
    # results
    op.alter_column("results", "tool", nullable=False)
    for col in [
        "error_message", "success", "duration_seconds", "exit_code",
        "risk_score", "findings", "parsed_output", "raw_output", "target", "tool_name",
    ]:
        op.drop_column("results", col)

    # tasks
    try:
        op.drop_index("ix_tasks_project_id", "tasks")
        op.drop_index("ix_tasks_celery_task_id", "tasks")
    except Exception:
        pass
    for col in ["project_id", "error_message", "celery_task_id", "options", "target", "name"]:
        op.drop_column("tasks", col)
