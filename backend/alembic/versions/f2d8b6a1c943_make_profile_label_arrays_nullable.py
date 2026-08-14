"""make profile label arrays nullable

Revision ID: f2d8b6a1c943
Revises: c4b6e4d10f92
Create Date: 2026-08-14 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f2d8b6a1c943"
down_revision: Union[str, Sequence[str], None] = "c4b6e4d10f92"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Allow unknown dietary/allergy declarations without fabricating empty arrays."""
    op.alter_column(
        "nutrition_profiles",
        "dietary_restrictions",
        existing_type=postgresql.JSONB(),
        nullable=True,
        server_default=None,
    )
    op.alter_column(
        "nutrition_profiles",
        "allergies",
        existing_type=postgresql.JSONB(),
        nullable=True,
        server_default=None,
    )


def downgrade() -> None:
    """Restore the former non-null array contract; null unknown values become empty arrays."""
    op.execute(
        "UPDATE nutrition_profiles SET dietary_restrictions = '[]'::jsonb "
        "WHERE dietary_restrictions IS NULL"
    )
    op.execute("UPDATE nutrition_profiles SET allergies = '[]'::jsonb WHERE allergies IS NULL")
    op.alter_column(
        "nutrition_profiles",
        "dietary_restrictions",
        existing_type=postgresql.JSONB(),
        nullable=False,
        server_default=sa.text("'[]'::jsonb"),
    )
    op.alter_column(
        "nutrition_profiles",
        "allergies",
        existing_type=postgresql.JSONB(),
        nullable=False,
        server_default=sa.text("'[]'::jsonb"),
    )
