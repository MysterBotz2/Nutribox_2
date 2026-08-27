"""expand PI-3A nutrition snapshots

Revision ID: e8f1c3a7b5d2
Revises: d3e6a9c2f4b7
"""

from alembic import op
import sqlalchemy as sa


revision = "e8f1c3a7b5d2"
down_revision = "d3e6a9c2f4b7"
branch_labels = None
depends_on = None


_FOOD_COLUMNS = (
    "phosphorus_mg_per_100g",
    "vitamin_b6_mg_per_100g",
    "niacin_mg_per_100g",
)
_ITEM_COLUMNS = (
    "calculated_phosphorus_mg",
    "calculated_vitamin_b6_mg",
    "calculated_niacin_mg",
)


def upgrade() -> None:
    for column in _FOOD_COLUMNS:
        op.add_column("foods", sa.Column(column, sa.Numeric(10, 3), nullable=True))
        op.create_check_constraint(
            f"ck_foods_{column.removesuffix('_per_100g')}_nonnegative",
            "foods",
            f"{column} IS NULL OR {column} >= 0",
        )
    for column in _ITEM_COLUMNS:
        op.add_column("meal_items", sa.Column(column, sa.Numeric(12, 3), nullable=True))
        op.create_check_constraint(
            f"ck_meal_items_{column.removeprefix('calculated_')}_nonnegative",
            "meal_items",
            f"{column} IS NULL OR {column} >= 0",
        )


def downgrade() -> None:
    for column in reversed(_ITEM_COLUMNS):
        op.drop_constraint(
            f"ck_meal_items_{column.removeprefix('calculated_')}_nonnegative",
            "meal_items",
            type_="check",
        )
        op.drop_column("meal_items", column)
    for column in reversed(_FOOD_COLUMNS):
        op.drop_constraint(
            f"ck_foods_{column.removesuffix('_per_100g')}_nonnegative",
            "foods",
            type_="check",
        )
        op.drop_column("foods", column)
