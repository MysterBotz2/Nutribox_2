"""add canonical sensitive profile fields

Revision ID: a7c3e9f4b2d1
Revises: f6b2d8e3a7c5
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "a7c3e9f4b2d1"
down_revision = "f6b2d8e3a7c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sensitive_profile_contexts",
        sa.Column("smoking_methods", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "sensitive_profile_contexts",
        sa.Column("average_alcohol_intake", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "sensitive_profile_contexts",
        sa.Column("alcohol_types", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "sensitive_profile_contexts", sa.Column("weight_status", sa.String(length=16), nullable=True)
    )
    op.create_check_constraint(
        "ck_sensitive_context_smoking_methods_array",
        "sensitive_profile_contexts",
        "jsonb_typeof(smoking_methods) = 'array'",
    )
    op.create_check_constraint(
        "ck_sensitive_context_alcohol_types_array",
        "sensitive_profile_contexts",
        "jsonb_typeof(alcohol_types) = 'array'",
    )
    op.create_check_constraint(
        "ck_sensitive_context_average_alcohol_intake",
        "sensitive_profile_contexts",
        "average_alcohol_intake IS NULL OR average_alcohol_intake IN ('one_to_two', 'three_to_four', 'five_or_more')",
    )
    op.create_check_constraint(
        "ck_sensitive_context_weight_status",
        "sensitive_profile_contexts",
        "weight_status IS NULL OR weight_status IN ('underweight', 'normal_weight', 'overweight', 'obesity')",
    )

    # Preserve existing voluntarily supplied values in their canonical plural
    # counterparts. No default health declaration is introduced for nulls.
    op.execute(
        """
        UPDATE sensitive_profile_contexts
        SET smoking_methods = CASE
            WHEN smoking_method IS NULL THEN NULL
            ELSE jsonb_build_array(smoking_method)
        END,
        average_alcohol_intake = drinking_average_intake,
        alcohol_types = CASE
            WHEN drinking_status = 'never' THEN '[]'::jsonb
            WHEN alcohol_type IS NULL THEN NULL
            ELSE jsonb_build_array(alcohol_type)
        END
        """
    )


def downgrade() -> None:
    op.drop_constraint("ck_sensitive_context_weight_status", "sensitive_profile_contexts", type_="check")
    op.drop_constraint(
        "ck_sensitive_context_average_alcohol_intake", "sensitive_profile_contexts", type_="check"
    )
    op.drop_constraint("ck_sensitive_context_alcohol_types_array", "sensitive_profile_contexts", type_="check")
    op.drop_constraint("ck_sensitive_context_smoking_methods_array", "sensitive_profile_contexts", type_="check")
    op.drop_column("sensitive_profile_contexts", "weight_status")
    op.drop_column("sensitive_profile_contexts", "alcohol_types")
    op.drop_column("sensitive_profile_contexts", "average_alcohol_intake")
    op.drop_column("sensitive_profile_contexts", "smoking_methods")
