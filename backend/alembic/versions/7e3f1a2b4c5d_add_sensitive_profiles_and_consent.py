"""add sensitive profiles and consent

Revision ID: 7e3f1a2b4c5d
Revises: f2d8b6a1c943
Create Date: 2026-08-22 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "7e3f1a2b4c5d"
down_revision: Union[str, Sequence[str], None] = "f2d8b6a1c943"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_profiles_activity_level", "nutrition_profiles", type_="check")
    op.create_check_constraint(
        "ck_profiles_activity_level",
        "nutrition_profiles",
        "activity_level IS NULL OR activity_level IN "
        "('sedentary', 'lightly_active', 'moderately_active', 'very_active', 'highly_active')",
    )
    op.add_column("nutrition_profiles", sa.Column("budget_allotment", sa.String(length=32), nullable=True))
    op.create_check_constraint(
        "ck_profiles_budget_allotment",
        "nutrition_profiles",
        "budget_allotment IS NULL OR budget_allotment IN "
        "('under_php_100', 'php_100_to_500', 'php_500_to_1000', "
        "'php_1000_to_1500', 'more_than_php_1500')",
    )
    op.create_table(
        "profile_consents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("sensitive_storage", sa.String(length=16), server_default="not_asked", nullable=False),
        sa.Column("personalization", sa.String(length=16), server_default="not_asked", nullable=False),
        sa.Column("ai_context", sa.String(length=16), server_default="not_asked", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("sensitive_storage IN ('not_asked', 'granted', 'declined', 'withdrawn')", name="ck_profile_consents_sensitive_storage"),
        sa.CheckConstraint("personalization IN ('not_asked', 'granted', 'declined', 'withdrawn')", name="ck_profile_consents_personalization"),
        sa.CheckConstraint("ai_context IN ('not_asked', 'granted', 'declined', 'withdrawn')", name="ck_profile_consents_ai_context"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_profile_consents_user_id"), "profile_consents", ["user_id"], unique=True)
    op.create_table(
        "sensitive_profile_contexts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("medical_conditions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("medical_conditions_other", sa.String(length=250), nullable=True),
        sa.Column("pregnancy_status", sa.String(length=16), nullable=True),
        sa.Column("pregnancy_duration_value", sa.Integer(), nullable=True),
        sa.Column("pregnancy_duration_unit", sa.String(length=8), nullable=True),
        sa.Column("pregnancy_due_date", sa.Date(), nullable=True),
        sa.Column("smoking_status", sa.String(length=32), nullable=True),
        sa.Column("smoking_method", sa.String(length=32), nullable=True),
        sa.Column("drinking_status", sa.String(length=16), nullable=True),
        sa.Column("drinking_frequency", sa.String(length=16), nullable=True),
        sa.Column("drinking_average_intake", sa.String(length=16), nullable=True),
        sa.Column("last_alcohol_consumption", sa.String(length=32), nullable=True),
        sa.Column("alcohol_type", sa.String(length=16), nullable=True),
        sa.Column("body_build", sa.String(length=16), nullable=True),
        sa.Column("ethnicity", sa.String(length=16), nullable=True),
        sa.Column("medical_needs", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("jsonb_typeof(medical_conditions) = 'array'", name="ck_sensitive_context_medical_conditions_array"),
        sa.CheckConstraint("jsonb_typeof(medical_needs) = 'array'", name="ck_sensitive_context_medical_needs_array"),
        sa.CheckConstraint("pregnancy_status IS NULL OR pregnancy_status IN ('pregnant', 'postpartum', 'none', 'declined')", name="ck_sensitive_context_pregnancy_status"),
        sa.CheckConstraint("pregnancy_duration_unit IS NULL OR pregnancy_duration_unit IN ('weeks', 'months')", name="ck_sensitive_context_pregnancy_duration_unit"),
        sa.CheckConstraint("pregnancy_duration_value IS NULL OR pregnancy_duration_value BETWEEN 0 AND 1000", name="ck_sensitive_context_pregnancy_duration_value"),
        sa.CheckConstraint("smoking_status IS NULL OR smoking_status IN ('never', 'last_6_months', 'last_12_months', 'more_than_12_months_ago')", name="ck_sensitive_context_smoking_status"),
        sa.CheckConstraint("smoking_method IS NULL OR smoking_method IN ('cigarettes', 'alternative_tobacco', 'vaping', 'e_cigarettes', 'cannabis', 'none')", name="ck_sensitive_context_smoking_method"),
        sa.CheckConstraint("drinking_status IS NULL OR drinking_status IN ('never', 'former', 'current')", name="ck_sensitive_context_drinking_status"),
        sa.CheckConstraint("drinking_frequency IS NULL OR drinking_frequency IN ('daily', 'weekly', 'monthly', 'occasionally', 'rarely')", name="ck_sensitive_context_drinking_frequency"),
        sa.CheckConstraint("drinking_average_intake IS NULL OR drinking_average_intake IN ('one_to_two', 'three_to_four', 'five_or_more')", name="ck_sensitive_context_drinking_average_intake"),
        sa.CheckConstraint("last_alcohol_consumption IS NULL OR last_alcohol_consumption IN ('last_24_hours', 'last_7_days', 'last_30_days', 'more_than_30_days_ago', 'never')", name="ck_sensitive_context_last_alcohol_consumption"),
        sa.CheckConstraint("alcohol_type IS NULL OR alcohol_type IN ('beer', 'wine', 'spirits', 'mixed_drinks')", name="ck_sensitive_context_alcohol_type"),
        sa.CheckConstraint("body_build IS NULL OR body_build IN ('lean', 'average', 'muscular', 'stocky')", name="ck_sensitive_context_body_build"),
        sa.CheckConstraint("ethnicity IS NULL OR ethnicity IN ('filipino', 'other', 'declined')", name="ck_sensitive_context_ethnicity"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sensitive_profile_contexts_user_id"), "sensitive_profile_contexts", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_sensitive_profile_contexts_user_id"), table_name="sensitive_profile_contexts")
    op.drop_table("sensitive_profile_contexts")
    op.drop_index(op.f("ix_profile_consents_user_id"), table_name="profile_consents")
    op.drop_table("profile_consents")
    op.drop_constraint("ck_profiles_budget_allotment", "nutrition_profiles", type_="check")
    op.drop_column("nutrition_profiles", "budget_allotment")
    op.drop_constraint("ck_profiles_activity_level", "nutrition_profiles", type_="check")
    op.create_check_constraint(
        "ck_profiles_activity_level",
        "nutrition_profiles",
        "activity_level IS NULL OR activity_level IN "
        "('sedentary', 'lightly_active', 'moderately_active', 'very_active')",
    )
