from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import MAXIMUM_TARGET_CALORIES, MAXIMUM_TARGET_NUTRIENT_GRAMS
from app.database.base import Base


class NutritionTarget(Base):
    """Explicit, provenance-aware nutrition targets configured for one user."""

    __tablename__ = "nutrition_targets"
    __table_args__ = (
        CheckConstraint(
            f"calories IS NULL OR calories > 0 AND calories <= {MAXIMUM_TARGET_CALORIES}",
            name="ck_targets_calories_range",
        ),
        CheckConstraint(
            "protein_g IS NULL OR protein_g > 0 AND "
            f"protein_g <= {MAXIMUM_TARGET_NUTRIENT_GRAMS}",
            name="ck_targets_protein_range",
        ),
        CheckConstraint(
            "carbohydrates_g IS NULL OR carbohydrates_g > 0 AND "
            f"carbohydrates_g <= {MAXIMUM_TARGET_NUTRIENT_GRAMS}",
            name="ck_targets_carbohydrates_range",
        ),
        CheckConstraint(
            "fat_g IS NULL OR fat_g > 0 AND "
            f"fat_g <= {MAXIMUM_TARGET_NUTRIENT_GRAMS}",
            name="ck_targets_fat_range",
        ),
        CheckConstraint(
            "fiber_g IS NULL OR fiber_g > 0 AND "
            f"fiber_g <= {MAXIMUM_TARGET_NUTRIENT_GRAMS}",
            name="ck_targets_fiber_range",
        ),
        CheckConstraint(
            "source_type IN ('manual', 'researcher_assigned', 'professional_assigned')",
            name="ck_targets_source_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    calories: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    protein_g: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    carbohydrates_g: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    fat_g: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    fiber_g: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="nutrition_target")
