from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy import event
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


def normalize_food_name(value: str) -> str:
    """Create a stable canonical lookup key without doing semantic matching."""
    normalized_value = " ".join(value.split()).casefold()
    if not normalized_value:
        raise ValueError("Food name must not be blank.")
    return normalized_value


def clean_food_name(value: str) -> str:
    """Trim and collapse whitespace while preserving display capitalization."""
    cleaned_value = " ".join(value.split())
    if not cleaned_value:
        raise ValueError("Food name must not be blank.")
    return cleaned_value


class Food(Base):
    """Canonical nutrition reference data stored on a per-100-gram basis."""

    __tablename__ = "foods"
    __table_args__ = (
        CheckConstraint("calories_per_100g >= 0", name="ck_foods_calories_nonnegative"),
        CheckConstraint("protein_g_per_100g >= 0", name="ck_foods_protein_nonnegative"),
        CheckConstraint(
            "carbohydrates_g_per_100g >= 0", name="ck_foods_carbohydrates_nonnegative"
        ),
        CheckConstraint("fat_g_per_100g >= 0", name="ck_foods_fat_nonnegative"),
        CheckConstraint("fiber_g_per_100g >= 0", name="ck_foods_fiber_nonnegative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    normalized_name: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)

    calories_per_100g: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    protein_g_per_100g: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    carbohydrates_g_per_100g: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    fat_g_per_100g: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    fiber_g_per_100g: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)

    source_name: Mapped[str] = mapped_column(String(160), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


@event.listens_for(Food, "before_insert")
@event.listens_for(Food, "before_update")
def set_normalized_food_name(_, __, food: Food) -> None:
    """Keep the unique lookup key aligned with the canonical display name."""
    food.name = clean_food_name(food.name)
    food.normalized_name = normalize_food_name(food.name)
