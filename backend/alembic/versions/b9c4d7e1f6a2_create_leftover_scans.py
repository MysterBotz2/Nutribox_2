"""create paired-device leftover scans

Revision ID: b9c4d7e1f6a2
Revises: f7a2c8e4d9b1, e8f1c3a7b5d2
Create Date: 2026-09-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "b9c4d7e1f6a2"
down_revision = ("f7a2c8e4d9b1", "e8f1c3a7b5d2")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "leftover_scans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("meal_id", sa.Integer(), nullable=False),
        sa.Column("analysis_session_id", sa.Integer(), nullable=False),
        sa.Column("original_weight_grams", sa.Numeric(precision=8, scale=3), nullable=False),
        sa.Column("remaining_weight_grams", sa.Numeric(precision=8, scale=3), nullable=False),
        sa.Column("consumed_weight_grams", sa.Numeric(precision=8, scale=3), nullable=False),
        sa.Column("consumed_portion_percentage", sa.Numeric(precision=7, scale=3), nullable=False),
        sa.Column("remaining_nutrition_snapshot", postgresql.JSONB(none_as_null=True), nullable=False),
        sa.Column("consumed_nutrition_snapshot", postgresql.JSONB(none_as_null=True), nullable=False),
        sa.Column("comparison_warnings", postgresql.JSONB(none_as_null=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_session_id"], ["meal_analysis_sessions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["meal_id"], ["meals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("analysis_session_id", name="uq_leftover_scans_analysis_session_id"),
    )
    op.create_index(op.f("ix_leftover_scans_meal_id"), "leftover_scans", ["meal_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_leftover_scans_meal_id"), table_name="leftover_scans")
    op.drop_table("leftover_scans")
