"""add composite meal item provenance

Revision ID: b8e4c1d5a9f2
Revises: f7a2c8e4d9b1
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "b8e4c1d5a9f2"
down_revision = "f7a2c8e4d9b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_meal_items_nutrition_source_type", "meal_items", type_="check")
    op.create_check_constraint(
        "ck_meal_items_nutrition_source_type",
        "meal_items",
        "nutrition_source_type IS NULL OR nutrition_source_type IN "
        "('canteen_recipe', 'local_database', 'USDA', 'AI_estimate', 'ai_recipe_estimate')",
    )
    op.alter_column("meal_items", "food_id", existing_type=sa.Integer(), nullable=True)
    op.add_column(
        "meal_items",
        sa.Column("composite_provenance_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("meal_items", "composite_provenance_snapshot")
    op.alter_column("meal_items", "food_id", existing_type=sa.Integer(), nullable=False)
    op.drop_constraint("ck_meal_items_nutrition_source_type", "meal_items", type_="check")
    op.create_check_constraint(
        "ck_meal_items_nutrition_source_type",
        "meal_items",
        "nutrition_source_type IS NULL OR nutrition_source_type IN "
        "('canteen_recipe', 'local_database', 'USDA', 'AI_estimate')",
    )
