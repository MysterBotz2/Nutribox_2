"""create scheduled meals

Revision ID: b6e1f4a9d2c8
Revises: 7e3f1a2b4c5d
Create Date: 2026-08-22 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b6e1f4a9d2c8"
down_revision: Union[str, Sequence[str], None] = "7e3f1a2b4c5d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scheduled_meals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("notes", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("char_length(btrim(title)) > 0", name="ck_scheduled_meals_title_nonblank"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_scheduled_meals_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_scheduled_meals_user_id_scheduled_for",
        "scheduled_meals",
        ["user_id", "scheduled_for"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_scheduled_meals_user_id_scheduled_for", table_name="scheduled_meals")
    op.drop_table("scheduled_meals")
