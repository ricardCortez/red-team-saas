"""Initial schema: all tables (Phase 1 + Phase 2)

Revision ID: 0001
Revises:
Create Date: 2026-03-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("username", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("role", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_is_active", "users", ["is_active"])

    # ── workspaces ───────────────────────────────────────────────────────────
    op.create_table(
        "workspaces",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("client_name", sa.String(255), nullable=True),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workspaces_id", "workspaces", ["id"])
    op.create_index("ix_workspaces_owner_id", "workspaces", ["owner_id"])
    op.create_index("ix_workspaces_name", "workspaces", ["name"])
    op.create_index("ix_workspaces_client_name", "workspaces", ["client_name"])
    op.create_index("ix_workspaces_is_active", "workspaces", ["is_active"])

    # ── tasks ────────────────────────────────────────────────────────────────
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id"), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("tool_name", sa.String(255), nullable=True),
        sa.Column("parameters", sa.String(2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tasks_id", "tasks", ["id"])
    op.create_index("ix_tasks_user_id", "tasks", ["user_id"])
    op.create_index("ix_tasks_workspace_id", "tasks", ["workspace_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])

    # ── results ──────────────────────────────────────────────────────────────
    op.create_table(
        "results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("tool", sa.String(255), nullable=False),
        sa.Column("output", sa.Text(), nullable=True),
        sa.Column("parsed_data", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_results_id", "results", ["id"])
    op.create_index("ix_results_task_id", "results", ["task_id"])

    # ── audit_logs ───────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(255), nullable=False),
        sa.Column("resource", sa.String(255), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_id", "audit_logs", ["id"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])

    # ── generic_tool_configs ─────────────────────────────────────────────────
    op.create_table(
        "generic_tool_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tool_name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("execution_mode", sa.String(30), nullable=True),
        sa.Column("command_template", sa.String(1000), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("docker_image", sa.String(255), nullable=True),
        sa.Column("requires_auth", sa.String(50), nullable=True),
        sa.Column("output_format", sa.String(50), nullable=True),
        sa.Column("parser_function", sa.String(255), nullable=True),
        sa.Column("is_enabled", sa.String(1), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tool_name"),
    )
    op.create_index("ix_generic_tool_configs_id", "generic_tool_configs", ["id"])
    op.create_index("ix_generic_tool_configs_tool_name", "generic_tool_configs", ["tool_name"])
    op.create_index("ix_generic_tool_configs_category", "generic_tool_configs", ["category"])

    # ── tool_executions ──────────────────────────────────────────────────────
    op.create_table(
        "tool_executions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tool_config_id", sa.Integer(), sa.ForeignKey("generic_tool_configs.id"), nullable=False),
        sa.Column("command_executed", sa.String(2000), nullable=False),
        sa.Column("target", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("output", sa.Text(), nullable=True),
        sa.Column("parsed_output", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tool_executions_id", "tool_executions", ["id"])
    op.create_index("ix_tool_executions_tool_config_id", "tool_executions", ["tool_config_id"])

    # ── brute_force_configs ──────────────────────────────────────────────────
    op.create_table(
        "brute_force_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tool_name", sa.String(50), nullable=False),
        sa.Column("target", sa.String(255), nullable=False),
        sa.Column("username_list", sa.Text(), nullable=True),
        sa.Column("wordlist_path", sa.String(500), nullable=True),
        sa.Column("wordlist_size", sa.Integer(), nullable=True),
        sa.Column("attack_type", sa.String(50), nullable=True),
        sa.Column("timeout_seconds", sa.Integer(), nullable=True),
        sa.Column("max_attempts", sa.Integer(), nullable=True),
        sa.Column("rate_limit", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_brute_force_configs_id", "brute_force_configs", ["id"])
    op.create_index("ix_brute_force_configs_tool_name", "brute_force_configs", ["tool_name"])
    op.create_index("ix_brute_force_configs_target", "brute_force_configs", ["target"])

    # ── brute_force_results ──────────────────────────────────────────────────
    op.create_table(
        "brute_force_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("config_id", sa.Integer(), sa.ForeignKey("brute_force_configs.id"), nullable=False),
        sa.Column("credential", sa.String(500), nullable=True),
        sa.Column("is_valid", sa.Boolean(), nullable=True),
        sa.Column("attempts_count", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_brute_force_results_id", "brute_force_results", ["id"])
    op.create_index("ix_brute_force_results_config_id", "brute_force_results", ["config_id"])

    # ── plugins ──────────────────────────────────────────────────────────────
    op.create_table(
        "plugins",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(20), nullable=True),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("documentation", sa.Text(), nullable=True),
        sa.Column("requirements", sa.Text(), nullable=True),
        sa.Column("download_count", sa.Integer(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("is_public", sa.String(1), nullable=True),
        sa.Column("is_paid", sa.String(1), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("revenue_share", sa.Float(), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_plugins_id", "plugins", ["id"])
    op.create_index("ix_plugins_name", "plugins", ["name"])
    op.create_index("ix_plugins_category", "plugins", ["category"])

    # ── plugin_executions ────────────────────────────────────────────────────
    op.create_table(
        "plugin_executions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plugin_id", sa.Integer(), sa.ForeignKey("plugins.id"), nullable=False),
        sa.Column("target", sa.String(255), nullable=True),
        sa.Column("parameters", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("output", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plugin_executions_id", "plugin_executions", ["id"])
    op.create_index("ix_plugin_executions_plugin_id", "plugin_executions", ["plugin_id"])

    # ── templates (Phase 2) ──────────────────────────────────────────────────
    op.create_table(
        "templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("tool_configs", sa.Text(), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_templates_id", "templates", ["id"])
    op.create_index("ix_templates_user_id", "templates", ["user_id"])
    op.create_index("ix_templates_name", "templates", ["name"])
    op.create_index("ix_templates_category", "templates", ["category"])
    op.create_index("ix_templates_is_public", "templates", ["is_public"])

    # ── threat_intel (Phase 2) ───────────────────────────────────────────────
    op.create_table(
        "threat_intel",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cve_id", sa.String(20), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("cvss_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("affected_products", sa.Text(), nullable=True),
        sa.Column("exploit_available", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("patch_available", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("references", sa.Text(), nullable=True),
        sa.Column("published_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_modified", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tags", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cve_id"),
    )
    op.create_index("ix_threat_intel_id", "threat_intel", ["id"])
    op.create_index("ix_threat_intel_cve_id", "threat_intel", ["cve_id"])
    op.create_index("ix_threat_intel_severity", "threat_intel", ["severity"])
    op.create_index("ix_threat_intel_exploit_available", "threat_intel", ["exploit_available"])

    # ── risk_scores (Phase 2) ────────────────────────────────────────────────
    op.create_table(
        "risk_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("score", sa.Numeric(4, 2), nullable=False),
        sa.Column("components", sa.Text(), nullable=True),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_risk_scores_id", "risk_scores", ["id"])
    op.create_index("ix_risk_scores_task_id", "risk_scores", ["task_id"])

    # ── compliance_mappings (Phase 2) ────────────────────────────────────────
    op.create_table(
        "compliance_mappings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("framework", sa.String(20), nullable=False),
        sa.Column("control_id", sa.String(50), nullable=False),
        sa.Column("control_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="not_assessed"),
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id"), nullable=True),
        sa.Column("threat_intel_id", sa.Integer(), sa.ForeignKey("threat_intel.id"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_compliance_mappings_id", "compliance_mappings", ["id"])
    op.create_index("ix_compliance_mappings_framework", "compliance_mappings", ["framework"])
    op.create_index("ix_compliance_mappings_control_id", "compliance_mappings", ["control_id"])
    op.create_index("ix_compliance_mappings_status", "compliance_mappings", ["status"])
    op.create_index("ix_compliance_mappings_task_id", "compliance_mappings", ["task_id"])
    op.create_index("ix_compliance_mappings_threat_intel_id", "compliance_mappings", ["threat_intel_id"])

    # ── reports (Phase 2) ────────────────────────────────────────────────────
    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id"), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=True),
        sa.Column("findings", sa.Text(), nullable=True),
        sa.Column("recommendations", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("signature_hash", sa.String(64), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reports_id", "reports", ["id"])
    op.create_index("ix_reports_author_id", "reports", ["author_id"])
    op.create_index("ix_reports_workspace_id", "reports", ["workspace_id"])
    op.create_index("ix_reports_status", "reports", ["status"])


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("reports")
    op.drop_table("compliance_mappings")
    op.drop_table("risk_scores")
    op.drop_table("threat_intel")
    op.drop_table("templates")
    op.drop_table("plugin_executions")
    op.drop_table("plugins")
    op.drop_table("brute_force_results")
    op.drop_table("brute_force_configs")
    op.drop_table("tool_executions")
    op.drop_table("generic_tool_configs")
    op.drop_table("audit_logs")
    op.drop_table("results")
    op.drop_table("tasks")
    op.drop_table("workspaces")
    op.drop_table("users")
