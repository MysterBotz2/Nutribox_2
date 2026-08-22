from datetime import datetime
from decimal import Decimal
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

class LeftoverAnalysis(Base):
    __tablename__="leftover_analyses"
    __table_args__=(UniqueConstraint("meal_id",name="uq_leftover_analyses_meal_id"),)
    id:Mapped[int]=mapped_column(Integer,primary_key=True)
    meal_id:Mapped[int]=mapped_column(ForeignKey("meals.id",ondelete="CASCADE"),nullable=False)
    leftover_weight_grams:Mapped[Decimal]=mapped_column(Numeric(8,3),nullable=False)
    leftover_calories:Mapped[Decimal]=mapped_column(Numeric(12,3),nullable=False)
    leftover_protein_g:Mapped[Decimal]=mapped_column(Numeric(12,3),nullable=False)
    leftover_carbohydrates_g:Mapped[Decimal]=mapped_column(Numeric(12,3),nullable=False)
    leftover_fat_g:Mapped[Decimal]=mapped_column(Numeric(12,3),nullable=False)
    leftover_fiber_g:Mapped[Decimal]=mapped_column(Numeric(12,3),nullable=False)
    consumed_calories:Mapped[Decimal]=mapped_column(Numeric(12,3),nullable=False)
    consumed_protein_g:Mapped[Decimal]=mapped_column(Numeric(12,3),nullable=False)
    consumed_carbohydrates_g:Mapped[Decimal]=mapped_column(Numeric(12,3),nullable=False)
    consumed_fat_g:Mapped[Decimal]=mapped_column(Numeric(12,3),nullable=False)
    consumed_fiber_g:Mapped[Decimal]=mapped_column(Numeric(12,3),nullable=False)
    source:Mapped[str]=mapped_column(String(32),nullable=False)
    recognized_food_name: Mapped[str|None]=mapped_column(String(160),nullable=True)
    source_reference: Mapped[str|None]=mapped_column(String(255),nullable=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now(),nullable=False)
    meal: Mapped["Meal"] = relationship(back_populates="leftover_analysis")
