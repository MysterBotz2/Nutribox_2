"""add transient meal analysis sessions

Revision ID: f7a2c8e4d9b1
Revises: a7c3e9f4b2d1
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "f7a2c8e4d9b1"
down_revision = "a7c3e9f4b2d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("meals", sa.Column("measured_weight_grams", sa.Numeric(8, 3), nullable=True))
    op.add_column("meal_items", sa.Column("weight_source", sa.String(32), nullable=True))
    op.create_table(
        "meal_analysis_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("state", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_meal_analysis_sessions_user_id", "meal_analysis_sessions", ["user_id"])
    op.create_index("ix_meal_analysis_sessions_status", "meal_analysis_sessions", ["status"])
    op.create_index("ix_meal_analysis_sessions_user_expires", "meal_analysis_sessions", ["user_id", "expires_at"])
    op.create_index("ix_meal_analysis_sessions_status_expires", "meal_analysis_sessions", ["status", "expires_at"])


def downgrade() -> None:
    op.drop_index("ix_meal_analysis_sessions_status_expires", table_name="meal_analysis_sessions")
    op.drop_index("ix_meal_analysis_sessions_user_expires", table_name="meal_analysis_sessions")
    op.drop_index("ix_meal_analysis_sessions_status", table_name="meal_analysis_sessions")
    op.drop_index("ix_meal_analysis_sessions_user_id", table_name="meal_analysis_sessions")
    op.drop_table("meal_analysis_sessions")
    op.drop_column("meal_items", "weight_source")
    op.drop_column("meals", "measured_weight_grams")
