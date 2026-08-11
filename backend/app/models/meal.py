from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import MAXIMUM_PROTOTYPE_WEIGHT_GRAMS
from app.database.base import Base


class Meal(Base):
    """One locally recorded meal with server-derived nutrient totals."""

    __tablename__ = "meals"
    __table_args__ = (Index("ix_meals_user_id_recorded_at", "user_id", "recorded_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    total_calories: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    total_protein_g: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    total_carbohydrates_g: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    total_fat_g: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    total_fiber_g: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", name="fk_meals_user_id_users", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    items: Mapped[list["MealItem"]] = relationship(
        back_populates="meal", cascade="all, delete-orphan", passive_deletes=True
    )
    user: Mapped["User | None"] = relationship(back_populates="meals")


class MealItem(Base):
    """An immutable food and calculated-nutrition snapshot owned by one meal."""

    __tablename__ = "meal_items"
    __table_args__ = (
        CheckConstraint("weight_grams > 0", name="ck_meal_items_weight_positive"),
        CheckConstraint(
            f"weight_grams <= {MAXIMUM_PROTOTYPE_WEIGHT_GRAMS}",
            name="ck_meal_items_weight_maximum",
        ),
        CheckConstraint("calculated_calories >= 0", name="ck_meal_items_calories_nonnegative"),
        CheckConstraint("calculated_protein_g >= 0", name="ck_meal_items_protein_nonnegative"),
        CheckConstraint("calculated_carbohydrates_g >= 0", name="ck_meal_items_carbohydrates_nonnegative"),
        CheckConstraint("calculated_fat_g >= 0", name="ck_meal_items_fat_nonnegative"),
        CheckConstraint("calculated_fiber_g >= 0", name="ck_meal_items_fiber_nonnegative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meal_id: Mapped[int] = mapped_column(
        ForeignKey("meals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    food_id: Mapped[int] = mapped_column(
        ForeignKey("foods.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    weight_grams: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    calculated_calories: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    calculated_protein_g: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    calculated_carbohydrates_g: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    calculated_fat_g: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    calculated_fiber_g: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    food_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    food_normalized_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    meal: Mapped[Meal] = relationship(back_populates="items")
