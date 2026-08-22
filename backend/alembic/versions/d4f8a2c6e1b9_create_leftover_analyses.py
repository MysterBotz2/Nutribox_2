"""create leftover analyses"""
from alembic import op
import sqlalchemy as sa
revision='d4f8a2c6e1b9';down_revision='c9d2e6f1a4b7';branch_labels=None;depends_on=None
def upgrade():
 op.create_table('leftover_analyses',sa.Column('id',sa.Integer,primary_key=True),sa.Column('meal_id',sa.Integer,sa.ForeignKey('meals.id',ondelete='CASCADE'),nullable=False),sa.Column('leftover_weight_grams',sa.Numeric(8,3),nullable=False),*[sa.Column(n,sa.Numeric(12,3),nullable=False) for n in ('leftover_calories','leftover_protein_g','leftover_carbohydrates_g','leftover_fat_g','leftover_fiber_g','consumed_calories','consumed_protein_g','consumed_carbohydrates_g','consumed_fat_g','consumed_fiber_g')],sa.Column('source',sa.String(32),nullable=False),sa.Column('recognized_food_name',sa.String(160)),sa.Column('source_reference',sa.String(255)),sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.text('now()'),nullable=False),sa.UniqueConstraint('meal_id',name='uq_leftover_analyses_meal_id'))
def downgrade(): op.drop_table('leftover_analyses')
