"""Add user_ai_configs table

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

AI_PROVIDER_ENUM = "aiproviderenum"


def upgrade() -> None:
    sa.Enum(
        "ollama", "lmstudio", "openai_compatible", "openai",
        "anthropic", "gemini", "groq", "mistral", "custom",
        name=AI_PROVIDER_ENUM,
    ).create(op.get_bind(), checkfirst=True)

    op.create_table(
        "user_ai_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.Enum(
            "ollama", "lmstudio", "openai_compatible", "openai",
            "anthropic", "gemini", "groq", "mistral", "custom",
            name=AI_PROVIDER_ENUM, create_type=False,
        ), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("base_url", sa.String(512), nullable=True),
        sa.Column("model", sa.String(255), nullable=False, server_default=""),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("user_id", "provider", name="uq_user_ai_provider"),
    )
    op.create_index("ix_user_ai_configs_user_id", "user_ai_configs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_ai_configs_user_id", "user_ai_configs")
    op.drop_table("user_ai_configs")
    sa.Enum(name=AI_PROVIDER_ENUM).drop(op.get_bind(), checkfirst=True)
