from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy import event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

NUTRITION_SOURCE_TYPES = (
    "canteen_recipe",
    "local_database",
    "USDA",
    "AI_estimate",
)


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
        CheckConstraint(
            "saturated_fat_g_per_100g IS NULL OR saturated_fat_g_per_100g >= 0",
            name="ck_foods_saturated_fat_g_nonnegative",
        ),
        CheckConstraint(
            "sugars_g_per_100g IS NULL OR sugars_g_per_100g >= 0",
            name="ck_foods_sugars_g_nonnegative",
        ),
        CheckConstraint(
            "sodium_mg_per_100g IS NULL OR sodium_mg_per_100g >= 0",
            name="ck_foods_sodium_mg_nonnegative",
        ),
        CheckConstraint(
            "cholesterol_mg_per_100g IS NULL OR cholesterol_mg_per_100g >= 0",
            name="ck_foods_cholesterol_mg_nonnegative",
        ),
        CheckConstraint(
            "omega_3_g_per_100g IS NULL OR omega_3_g_per_100g >= 0",
            name="ck_foods_omega_3_g_nonnegative",
        ),
        CheckConstraint(
            "omega_6_g_per_100g IS NULL OR omega_6_g_per_100g >= 0",
            name="ck_foods_omega_6_g_nonnegative",
        ),
        CheckConstraint("calcium_mg_per_100g IS NULL OR calcium_mg_per_100g >= 0", name="ck_foods_calcium_mg_nonnegative"),
        CheckConstraint("potassium_mg_per_100g IS NULL OR potassium_mg_per_100g >= 0", name="ck_foods_potassium_mg_nonnegative"),
        CheckConstraint("zinc_mg_per_100g IS NULL OR zinc_mg_per_100g >= 0", name="ck_foods_zinc_mg_nonnegative"),
        CheckConstraint("iron_mg_per_100g IS NULL OR iron_mg_per_100g >= 0", name="ck_foods_iron_mg_nonnegative"),
        CheckConstraint("magnesium_mg_per_100g IS NULL OR magnesium_mg_per_100g >= 0", name="ck_foods_magnesium_mg_nonnegative"),
        CheckConstraint("phosphorus_mg_per_100g IS NULL OR phosphorus_mg_per_100g >= 0", name="ck_foods_phosphorus_mg_nonnegative"),
        CheckConstraint("vitamin_b6_mg_per_100g IS NULL OR vitamin_b6_mg_per_100g >= 0", name="ck_foods_vitamin_b6_mg_nonnegative"),
        CheckConstraint("niacin_mg_per_100g IS NULL OR niacin_mg_per_100g >= 0", name="ck_foods_niacin_mg_nonnegative"),
        CheckConstraint("vitamin_a_mcg_rae_per_100g IS NULL OR vitamin_a_mcg_rae_per_100g >= 0", name="ck_foods_vitamin_a_mcg_rae_nonnegative"),
        CheckConstraint("vitamin_b12_mcg_per_100g IS NULL OR vitamin_b12_mcg_per_100g >= 0", name="ck_foods_vitamin_b12_mcg_nonnegative"),
        CheckConstraint("vitamin_c_mg_per_100g IS NULL OR vitamin_c_mg_per_100g >= 0", name="ck_foods_vitamin_c_mg_nonnegative"),
        CheckConstraint("vitamin_d_mcg_per_100g IS NULL OR vitamin_d_mcg_per_100g >= 0", name="ck_foods_vitamin_d_mcg_nonnegative"),
        CheckConstraint("folate_mcg_dfe_per_100g IS NULL OR folate_mcg_dfe_per_100g >= 0", name="ck_foods_folate_mcg_dfe_nonnegative"),
        CheckConstraint(
            "source_type IS NULL OR source_type IN "
            "('canteen_recipe', 'local_database', 'USDA', 'AI_estimate')",
            name="ck_foods_source_type",
        ),
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
    saturated_fat_g_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(8, 3), nullable=True)
    sugars_g_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(8, 3), nullable=True)
    sodium_mg_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    cholesterol_mg_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    omega_3_g_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(8, 3), nullable=True)
    omega_6_g_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(8, 3), nullable=True)
    calcium_mg_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    potassium_mg_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    zinc_mg_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    iron_mg_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    magnesium_mg_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    phosphorus_mg_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    vitamin_b6_mg_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    niacin_mg_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    vitamin_a_mcg_rae_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    vitamin_b12_mcg_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    vitamin_c_mg_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    vitamin_d_mcg_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    folate_mcg_dfe_per_100g: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)

    source_name: Mapped[str] = mapped_column(String(160), nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    aliases: Mapped[list["FoodAlias"]] = relationship(
        back_populates="food", cascade="all, delete-orphan", passive_deletes=True
    )


@event.listens_for(Food, "before_insert")
@event.listens_for(Food, "before_update")
def set_normalized_food_name(_, __, food: Food) -> None:
    """Keep the unique lookup key aligned with the canonical display name."""
    food.name = clean_food_name(food.name)
    food.normalized_name = normalize_food_name(food.name)
