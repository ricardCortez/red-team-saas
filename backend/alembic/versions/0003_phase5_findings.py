"""Phase 5: extend findings table and add deduplication/status fields

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# PostgreSQL enum type names
FINDING_STATUS_TYPE = "findingstatus"


def upgrade() -> None:
    # Create FindingStatus enum type (PostgreSQL)
    findingstatus_enum = sa.Enum(
        "open", "confirmed", "false_positive", "resolved", "accepted_risk",
        name=FINDING_STATUS_TYPE,
    )
    findingstatus_enum.create(op.get_bind(), checkfirst=True)

    # Make scan_id nullable (was NOT NULL in Phase 3)
    op.alter_column("findings", "scan_id", existing_type=sa.Integer(), nullable=True)

    # Phase 5 new columns on findings table
    op.add_column("findings", sa.Column("result_id", sa.Integer(), nullable=True))
    op.add_column("findings", sa.Column("task_id", sa.Integer(), nullable=True))
    op.add_column("findings", sa.Column("project_id", sa.Integer(), nullable=True))
    op.add_column("findings", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("findings", sa.Column(
        "status",
        sa.Enum("open", "confirmed", "false_positive", "resolved", "accepted_risk", name=FINDING_STATUS_TYPE),
        server_default="open",
        nullable=False,
    ))
    op.add_column("findings", sa.Column("host", sa.String(255), nullable=True))
    op.add_column("findings", sa.Column("port", sa.Integer(), nullable=True))
    op.add_column("findings", sa.Column("service", sa.String(100), nullable=True))
    op.add_column("findings", sa.Column("tool_name", sa.String(255), nullable=True))
    op.add_column("findings", sa.Column("fingerprint", sa.String(64), nullable=True))
    op.add_column("findings", sa.Column("is_duplicate", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("findings", sa.Column("duplicate_of", sa.Integer(), nullable=True))
    op.add_column("findings", sa.Column("false_positive_reason", sa.Text(), nullable=True))
    op.add_column("findings", sa.Column("assigned_to", sa.Integer(), nullable=True))

    # Indexes for new columns
    op.create_index("ix_findings_result_id", "findings", ["result_id"])
    op.create_index("ix_findings_task_id", "findings", ["task_id"])
    op.create_index("ix_findings_project_id", "findings", ["project_id"])
    op.create_index("ix_findings_fingerprint", "findings", ["fingerprint"])
    op.create_index("ix_findings_is_duplicate", "findings", ["is_duplicate"])
    op.create_index("ix_findings_status", "findings", ["status"])
    op.create_index("ix_findings_host", "findings", ["host"])
    op.create_index("ix_findings_tool_name", "findings", ["tool_name"])

    # Foreign key constraints
    op.create_foreign_key(
        "fk_findings_result_id", "findings", "results", ["result_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_findings_task_id", "findings", "tasks", ["task_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_findings_project_id", "findings", "projects", ["project_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_findings_duplicate_of", "findings", "findings", ["duplicate_of"], ["id"]
    )
    op.create_foreign_key(
        "fk_findings_assigned_to", "findings", "users", ["assigned_to"], ["id"]
    )


def downgrade() -> None:
    # Drop foreign keys
    op.drop_constraint("fk_findings_assigned_to", "findings", type_="foreignkey")
    op.drop_constraint("fk_findings_duplicate_of", "findings", type_="foreignkey")
    op.drop_constraint("fk_findings_project_id", "findings", type_="foreignkey")
    op.drop_constraint("fk_findings_task_id", "findings", type_="foreignkey")
    op.drop_constraint("fk_findings_result_id", "findings", type_="foreignkey")

    # Drop indexes
    op.drop_index("ix_findings_tool_name", "findings")
    op.drop_index("ix_findings_host", "findings")
    op.drop_index("ix_findings_status", "findings")
    op.drop_index("ix_findings_is_duplicate", "findings")
    op.drop_index("ix_findings_fingerprint", "findings")
    op.drop_index("ix_findings_project_id", "findings")
    op.drop_index("ix_findings_task_id", "findings")
    op.drop_index("ix_findings_result_id", "findings")

    # Drop columns
    for col in [
        "assigned_to", "false_positive_reason", "duplicate_of", "is_duplicate",
        "fingerprint", "tool_name", "service", "port", "host", "status",
        "description", "project_id", "task_id", "result_id",
    ]:
        op.drop_column("findings", col)

    # Restore scan_id to NOT NULL
    op.alter_column("findings", "scan_id", existing_type=sa.Integer(), nullable=False)

    # Drop enum type
    sa.Enum(name=FINDING_STATUS_TYPE).drop(op.get_bind(), checkfirst=True)
