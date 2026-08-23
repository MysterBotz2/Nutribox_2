"""create device pairing

Revision ID: f6b2d8e3a7c5
Revises: e5a1c7b2d6f4
"""
from alembic import op
import sqlalchemy as sa

revision = "f6b2d8e3a7c5"
down_revision = "e5a1c7b2d6f4"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("paired_devices", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(160), nullable=False), sa.Column("device_type", sa.String(32), nullable=False, server_default="nutribox_pi"), sa.Column("token_hash", sa.String(64), nullable=False, unique=True), sa.Column("paired_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.Column("last_seen_at", sa.DateTime(timezone=True)), sa.Column("revoked_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.CheckConstraint("device_type = 'nutribox_pi'", name="ck_paired_devices_type"))
    op.create_index("ix_paired_devices_user_id", "paired_devices", ["user_id"])
    op.create_table("device_pairing_sessions", sa.Column("id", sa.String(64), primary_key=True), sa.Column("pairing_code_digest", sa.String(64), nullable=False, unique=True), sa.Column("device_token_hash", sa.String(64), nullable=False, unique=True), sa.Column("device_name", sa.String(160), nullable=False), sa.Column("device_type", sa.String(32), nullable=False, server_default="nutribox_pi"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("paired_at", sa.DateTime(timezone=True)), sa.Column("paired_device_id", sa.Integer(), sa.ForeignKey("paired_devices.id", ondelete="SET NULL"), unique=True), sa.CheckConstraint("device_type = 'nutribox_pi'", name="ck_pairing_sessions_type"))

def downgrade() -> None:
    op.drop_table("device_pairing_sessions")
    op.drop_index("ix_paired_devices_user_id", table_name="paired_devices")
    op.drop_table("paired_devices")
