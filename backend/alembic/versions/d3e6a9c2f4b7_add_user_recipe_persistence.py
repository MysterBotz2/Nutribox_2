"""add user recipe persistence

Revision ID: d3e6a9c2f4b7
Revises: b8e4c1d5a9f2
"""

from alembic import op
import sqlalchemy as sa


revision = "d3e6a9c2f4b7"
down_revision = "b8e4c1d5a9f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_recipes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("normalized_name", sa.String(length=160), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False, server_default="user_confirmed"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("source_type = 'user_confirmed'", name="ck_user_recipes_source_type"),
    )
    op.create_index("ix_user_recipes_user_id", "user_recipes", ["user_id"])
    op.create_index(
        "ix_user_recipes_user_id_normalized_name",
        "user_recipes",
        ["user_id", "normalized_name"],
    )
    op.create_table(
        "user_recipe_ingredients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recipe_id", sa.Integer(), sa.ForeignKey("user_recipes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("normalized_name", sa.String(length=160), nullable=False),
        sa.Column("normalized_proportion", sa.Numeric(12, 9), nullable=False),
        sa.Column("nutrition_source_type", sa.String(length=32), nullable=False),
        sa.Column("resolved_reference", sa.Text(), nullable=False),
        sa.Column("ingredient_source", sa.String(length=32), nullable=False),
        sa.Column("weight_source", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("position > 0", name="ck_user_recipe_ingredients_position_positive"),
        sa.CheckConstraint("normalized_proportion > 0 AND normalized_proportion <= 1", name="ck_user_recipe_ingredients_proportion_range"),
        sa.CheckConstraint("nutrition_source_type IN ('canteen_recipe', 'local_database', 'USDA', 'AI_estimate', 'ai_recipe_estimate')", name="ck_user_recipe_ingredients_nutrition_source_type"),
        sa.CheckConstraint("ingredient_source IN ('ai_estimate', 'user_confirmed')", name="ck_user_recipe_ingredients_ingredient_source"),
        sa.CheckConstraint("weight_source IN ('ai_estimate', 'user_confirmed')", name="ck_user_recipe_ingredients_weight_source"),
        sa.UniqueConstraint("recipe_id", "position", name="uq_user_recipe_ingredients_recipe_position"),
    )
    op.create_index("ix_user_recipe_ingredients_recipe_id", "user_recipe_ingredients", ["recipe_id"])


def downgrade() -> None:
    op.drop_index("ix_user_recipe_ingredients_recipe_id", table_name="user_recipe_ingredients")
    op.drop_table("user_recipe_ingredients")
    op.drop_index("ix_user_recipes_user_id_normalized_name", table_name="user_recipes")
    op.drop_index("ix_user_recipes_user_id", table_name="user_recipes")
    op.drop_table("user_recipes")
