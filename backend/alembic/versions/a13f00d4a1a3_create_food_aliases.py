"""create food aliases

Revision ID: a13f00d4a1a3
Revises: 6b4e2f24290a
Create Date: 2026-08-11
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a13f00d4a1a3"
down_revision: Union[str, Sequence[str], None] = "6b4e2f24290a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "food_aliases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("food_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(length=160), nullable=False),
        sa.Column("normalized_alias", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["food_id"], ["foods.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_alias"),
    )
    op.create_index(op.f("ix_food_aliases_food_id"), "food_aliases", ["food_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_food_aliases_food_id"), table_name="food_aliases")
    op.drop_table("food_aliases")
