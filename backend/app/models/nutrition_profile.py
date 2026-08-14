from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class NutritionProfile(Base):
    """Optional, conservative nutrition-preference data owned by one user."""

    __tablename__ = "nutrition_profiles"
    __table_args__ = (
        CheckConstraint("age IS NULL OR age BETWEEN 0 AND 130", name="ck_profiles_age_range"),
        CheckConstraint(
            "height_cm IS NULL OR height_cm > 0 AND height_cm <= 300",
            name="ck_profiles_height_range",
        ),
        CheckConstraint(
            "weight_kg IS NULL OR weight_kg > 0 AND weight_kg <= 500",
            name="ck_profiles_weight_range",
        ),
        CheckConstraint(
            "activity_level IS NULL OR activity_level IN "
            "('sedentary', 'lightly_active', 'moderately_active', 'very_active')",
            name="ck_profiles_activity_level",
        ),
        CheckConstraint(
            "nutrition_goal IS NULL OR nutrition_goal IN "
            "('maintain_weight', 'lose_weight', 'gain_weight', 'general_health')",
            name="ck_profiles_nutrition_goal",
        ),
        CheckConstraint(
            "jsonb_typeof(dietary_restrictions) = 'array'",
            name="ck_profiles_dietary_restrictions_array",
        ),
        CheckConstraint("jsonb_typeof(allergies) = 'array'", name="ck_profiles_allergies_array"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 3), nullable=True)
    activity_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    nutrition_goal: Mapped[str | None] = mapped_column(String(32), nullable=True)
    dietary_restrictions: Mapped[list[str] | None] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )
    allergies: Mapped[list[str] | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="nutrition_profile")
