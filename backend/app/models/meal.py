from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
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
    leftover_analysis: Mapped["LeftoverAnalysis | None"] = relationship(back_populates="meal", uselist=False, cascade="all, delete-orphan", passive_deletes=True)


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
        CheckConstraint("calculated_saturated_fat_g IS NULL OR calculated_saturated_fat_g >= 0", name="ck_meal_items_saturated_fat_g_nonnegative"),
        CheckConstraint("calculated_sugars_g IS NULL OR calculated_sugars_g >= 0", name="ck_meal_items_sugars_g_nonnegative"),
        CheckConstraint("calculated_sodium_mg IS NULL OR calculated_sodium_mg >= 0", name="ck_meal_items_sodium_mg_nonnegative"),
        CheckConstraint("calculated_cholesterol_mg IS NULL OR calculated_cholesterol_mg >= 0", name="ck_meal_items_cholesterol_mg_nonnegative"),
        CheckConstraint("calculated_omega_3_g IS NULL OR calculated_omega_3_g >= 0", name="ck_meal_items_omega_3_g_nonnegative"),
        CheckConstraint("calculated_omega_6_g IS NULL OR calculated_omega_6_g >= 0", name="ck_meal_items_omega_6_g_nonnegative"),
        CheckConstraint("calculated_calcium_mg IS NULL OR calculated_calcium_mg >= 0", name="ck_meal_items_calcium_mg_nonnegative"),
        CheckConstraint("calculated_potassium_mg IS NULL OR calculated_potassium_mg >= 0", name="ck_meal_items_potassium_mg_nonnegative"),
        CheckConstraint("calculated_zinc_mg IS NULL OR calculated_zinc_mg >= 0", name="ck_meal_items_zinc_mg_nonnegative"),
        CheckConstraint("calculated_iron_mg IS NULL OR calculated_iron_mg >= 0", name="ck_meal_items_iron_mg_nonnegative"),
        CheckConstraint("calculated_magnesium_mg IS NULL OR calculated_magnesium_mg >= 0", name="ck_meal_items_magnesium_mg_nonnegative"),
        CheckConstraint("calculated_vitamin_a_mcg_rae IS NULL OR calculated_vitamin_a_mcg_rae >= 0", name="ck_meal_items_vitamin_a_mcg_rae_nonnegative"),
        CheckConstraint("calculated_vitamin_b12_mcg IS NULL OR calculated_vitamin_b12_mcg >= 0", name="ck_meal_items_vitamin_b12_mcg_nonnegative"),
        CheckConstraint("calculated_vitamin_c_mg IS NULL OR calculated_vitamin_c_mg >= 0", name="ck_meal_items_vitamin_c_mg_nonnegative"),
        CheckConstraint("calculated_vitamin_d_mcg IS NULL OR calculated_vitamin_d_mcg >= 0", name="ck_meal_items_vitamin_d_mcg_nonnegative"),
        CheckConstraint("calculated_folate_mcg_dfe IS NULL OR calculated_folate_mcg_dfe >= 0", name="ck_meal_items_folate_mcg_dfe_nonnegative"),
        CheckConstraint("nutrition_source_type IS NULL OR nutrition_source_type IN ('canteen_recipe', 'local_database', 'USDA', 'AI_estimate')", name="ck_meal_items_nutrition_source_type"),
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
    calculated_saturated_fat_g: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    calculated_sugars_g: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    calculated_sodium_mg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    calculated_cholesterol_mg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    calculated_omega_3_g: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    calculated_omega_6_g: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    calculated_calcium_mg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    calculated_potassium_mg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    calculated_zinc_mg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    calculated_iron_mg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    calculated_magnesium_mg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    calculated_vitamin_a_mcg_rae: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    calculated_vitamin_b12_mcg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    calculated_vitamin_c_mg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    calculated_vitamin_d_mcg: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    calculated_folate_mcg_dfe: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    food_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    food_normalized_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    nutrition_source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    nutrition_source_name_snapshot: Mapped[str | None] = mapped_column(String(160), nullable=True)
    nutrition_source_reference_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    nutrition_is_estimated: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    meal: Mapped[Meal] = relationship(back_populates="items")
