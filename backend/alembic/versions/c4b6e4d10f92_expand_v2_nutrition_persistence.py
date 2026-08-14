"""expand V2 nutrition persistence

Revision ID: c4b6e4d10f92
Revises: a13f00d4a1a3
Create Date: 2026-08-13

Existing rows retain their five known nutrient values. New V2 nutrient and
provenance fields deliberately remain nullable because their historical values
are unknown, not zero.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4b6e4d10f92"
down_revision: Union[str, Sequence[str], None] = "a13f00d4a1a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FOOD_NUTRIENT_COLUMNS = (
    ("saturated_fat_g_per_100g", sa.Numeric(8, 3)),
    ("sugars_g_per_100g", sa.Numeric(8, 3)),
    ("sodium_mg_per_100g", sa.Numeric(10, 3)),
    ("cholesterol_mg_per_100g", sa.Numeric(10, 3)),
    ("omega_3_g_per_100g", sa.Numeric(8, 3)),
    ("omega_6_g_per_100g", sa.Numeric(8, 3)),
    ("calcium_mg_per_100g", sa.Numeric(10, 3)),
    ("potassium_mg_per_100g", sa.Numeric(10, 3)),
    ("zinc_mg_per_100g", sa.Numeric(10, 3)),
    ("iron_mg_per_100g", sa.Numeric(10, 3)),
    ("magnesium_mg_per_100g", sa.Numeric(10, 3)),
    ("vitamin_a_mcg_rae_per_100g", sa.Numeric(10, 3)),
    ("vitamin_b12_mcg_per_100g", sa.Numeric(10, 3)),
    ("vitamin_c_mg_per_100g", sa.Numeric(10, 3)),
    ("vitamin_d_mcg_per_100g", sa.Numeric(10, 3)),
    ("folate_mcg_dfe_per_100g", sa.Numeric(10, 3)),
)

MEAL_ITEM_NUTRIENT_COLUMNS = (
    ("calculated_saturated_fat_g", sa.Numeric(12, 3)),
    ("calculated_sugars_g", sa.Numeric(12, 3)),
    ("calculated_sodium_mg", sa.Numeric(12, 3)),
    ("calculated_cholesterol_mg", sa.Numeric(12, 3)),
    ("calculated_omega_3_g", sa.Numeric(12, 3)),
    ("calculated_omega_6_g", sa.Numeric(12, 3)),
    ("calculated_calcium_mg", sa.Numeric(12, 3)),
    ("calculated_potassium_mg", sa.Numeric(12, 3)),
    ("calculated_zinc_mg", sa.Numeric(12, 3)),
    ("calculated_iron_mg", sa.Numeric(12, 3)),
    ("calculated_magnesium_mg", sa.Numeric(12, 3)),
    ("calculated_vitamin_a_mcg_rae", sa.Numeric(12, 3)),
    ("calculated_vitamin_b12_mcg", sa.Numeric(12, 3)),
    ("calculated_vitamin_c_mg", sa.Numeric(12, 3)),
    ("calculated_vitamin_d_mcg", sa.Numeric(12, 3)),
    ("calculated_folate_mcg_dfe", sa.Numeric(12, 3)),
)


def _nonnegative_constraint(table: str, column: str, name: str) -> None:
    op.create_check_constraint(name, table, f"{column} IS NULL OR {column} >= 0")


def upgrade() -> None:
    for name, column_type in FOOD_NUTRIENT_COLUMNS:
        op.add_column("foods", sa.Column(name, column_type, nullable=True))
        _nonnegative_constraint("foods", name, f"ck_foods_{name.removesuffix('_per_100g')}_nonnegative")
    op.add_column("foods", sa.Column("source_type", sa.String(length=32), nullable=True))
    op.create_check_constraint(
        "ck_foods_source_type",
        "foods",
        "source_type IS NULL OR source_type IN "
        "('canteen_recipe', 'local_database', 'USDA', 'AI_estimate')",
    )

    for name, column_type in MEAL_ITEM_NUTRIENT_COLUMNS:
        op.add_column("meal_items", sa.Column(name, column_type, nullable=True))
        _nonnegative_constraint("meal_items", name, f"ck_meal_items_{name.removeprefix('calculated_')}_nonnegative")
    op.add_column("meal_items", sa.Column("nutrition_source_type", sa.String(length=32), nullable=True))
    op.add_column("meal_items", sa.Column("nutrition_source_name_snapshot", sa.String(length=160), nullable=True))
    op.add_column("meal_items", sa.Column("nutrition_source_reference_snapshot", sa.Text(), nullable=True))
    op.add_column("meal_items", sa.Column("nutrition_is_estimated", sa.Boolean(), nullable=True))
    op.create_check_constraint(
        "ck_meal_items_nutrition_source_type",
        "meal_items",
        "nutrition_source_type IS NULL OR nutrition_source_type IN "
        "('canteen_recipe', 'local_database', 'USDA', 'AI_estimate')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_meal_items_nutrition_source_type", "meal_items", type_="check")
    for name in (
        "nutrition_is_estimated",
        "nutrition_source_reference_snapshot",
        "nutrition_source_name_snapshot",
        "nutrition_source_type",
    ):
        op.drop_column("meal_items", name)
    for name, _ in reversed(MEAL_ITEM_NUTRIENT_COLUMNS):
        op.drop_constraint(
            f"ck_meal_items_{name.removeprefix('calculated_')}_nonnegative",
            "meal_items",
            type_="check",
        )
        op.drop_column("meal_items", name)

    op.drop_constraint("ck_foods_source_type", "foods", type_="check")
    op.drop_column("foods", "source_type")
    for name, _ in reversed(FOOD_NUTRIENT_COLUMNS):
        op.drop_constraint(
            f"ck_foods_{name.removesuffix('_per_100g')}_nonnegative",
            "foods",
            type_="check",
        )
        op.drop_column("foods", name)
