"""create weight entries"""
from alembic import op
import sqlalchemy as sa
revision="c9d2e6f1a4b7"
down_revision="b6e1f4a9d2c8"
branch_labels=None
depends_on=None
def upgrade():
 op.create_table("weight_entries",sa.Column("id",sa.Integer,primary_key=True),sa.Column("user_id",sa.Integer,sa.ForeignKey("users.id",ondelete="CASCADE"),nullable=False),sa.Column("weight_kg",sa.Numeric(6,3),nullable=False),sa.Column("measured_at",sa.DateTime(timezone=True),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.text("now()"),nullable=False),sa.CheckConstraint("weight_kg > 0 AND weight_kg <= 500",name="ck_weight_entries_weight_range"))
 op.create_index("ix_weight_entries_user_id_measured_at","weight_entries",["user_id","measured_at"])
def downgrade():
 op.drop_index("ix_weight_entries_user_id_measured_at",table_name="weight_entries");op.drop_table("weight_entries")
