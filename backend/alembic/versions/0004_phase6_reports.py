"""Phase 6: Rebuild reports table for reporting engine

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Enum type names (PostgreSQL)
REPORT_TYPE_ENUM = "reporttype"
REPORT_FORMAT_ENUM = "reportformat"
REPORT_STATUS_ENUM = "reportstatus"
REPORT_CLASSIFICATION_ENUM = "reportclassification"


def upgrade() -> None:
    # Drop legacy reports table (Phase 3 schema)
    op.drop_table("reports")

    # Create new PostgreSQL enum types
    sa.Enum("executive", "technical", "compliance", name=REPORT_TYPE_ENUM).create(
        op.get_bind(), checkfirst=True
    )
    sa.Enum("pdf", "html", name=REPORT_FORMAT_ENUM).create(
        op.get_bind(), checkfirst=True
    )
    sa.Enum("pending", "generating", "ready", "failed", name=REPORT_STATUS_ENUM).create(
        op.get_bind(), checkfirst=True
    )
    sa.Enum(
        "public", "internal", "confidential", "restricted",
        name=REPORT_CLASSIFICATION_ENUM,
    ).create(op.get_bind(), checkfirst=True)

    # Create Phase 6 reports table
    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column(
            "report_type",
            sa.Enum("executive", "technical", "compliance", name=REPORT_TYPE_ENUM),
            nullable=False,
        ),
        sa.Column(
            "report_format",
            sa.Enum("pdf", "html", name=REPORT_FORMAT_ENUM),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "generating", "ready", "failed", name=REPORT_STATUS_ENUM),
            nullable=True,
        ),
        sa.Column(
            "classification",
            sa.Enum("public", "internal", "confidential", "restricted", name=REPORT_CLASSIFICATION_ENUM),
            nullable=True,
        ),
        sa.Column("scope_description", sa.Text(), nullable=True),
        sa.Column("executive_summary", sa.Text(), nullable=True),
        sa.Column("recommendations", sa.Text(), nullable=True),
        sa.Column("file_path", sa.String(length=1024), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("total_findings", sa.Integer(), nullable=True),
        sa.Column("critical_count", sa.Integer(), nullable=True),
        sa.Column("high_count", sa.Integer(), nullable=True),
        sa.Column("medium_count", sa.Integer(), nullable=True),
        sa.Column("low_count", sa.Integer(), nullable=True),
        sa.Column("overall_risk", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reports_id", "reports", ["id"])
    op.create_index("ix_reports_project_id", "reports", ["project_id"])
    op.create_index("ix_reports_created_by", "reports", ["created_by"])
    op.create_index("ix_reports_status", "reports", ["status"])


def downgrade() -> None:
    op.drop_index("ix_reports_status", table_name="reports")
    op.drop_index("ix_reports_created_by", table_name="reports")
    op.drop_index("ix_reports_project_id", table_name="reports")
    op.drop_index("ix_reports_id", table_name="reports")
    op.drop_table("reports")

    sa.Enum(name=REPORT_CLASSIFICATION_ENUM).drop(op.get_bind(), checkfirst=True)
    sa.Enum(name=REPORT_STATUS_ENUM).drop(op.get_bind(), checkfirst=True)
    sa.Enum(name=REPORT_FORMAT_ENUM).drop(op.get_bind(), checkfirst=True)
    sa.Enum(name=REPORT_TYPE_ENUM).drop(op.get_bind(), checkfirst=True)

    # Recreate legacy Phase 3 reports table
    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("workspace_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=True),
        sa.Column("findings", sa.Text(), nullable=True),
        sa.Column("recommendations", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("signature_hash", sa.String(length=64), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
