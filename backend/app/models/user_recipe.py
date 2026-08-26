from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, event, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.food import clean_food_name, normalize_food_name


class UserRecipe(Base):
    """A user-confirmed, reusable recipe composition with no meal side effects."""

    __tablename__ = "user_recipes"
    __table_args__ = (
        CheckConstraint("source_type = 'user_confirmed'", name="ck_user_recipes_source_type"),
        Index("ix_user_recipes_user_id_normalized_name", "user_id", "normalized_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(160), nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="user_confirmed"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="recipes")
    ingredients: Mapped[list["UserRecipeIngredient"]] = relationship(
        back_populates="recipe", cascade="all, delete-orphan", passive_deletes=True
    )


class UserRecipeIngredient(Base):
    """An immutable-in-recipe reference snapshot for one recipe component."""

    __tablename__ = "user_recipe_ingredients"
    __table_args__ = (
        CheckConstraint("position > 0", name="ck_user_recipe_ingredients_position_positive"),
        CheckConstraint(
            "normalized_proportion > 0 AND normalized_proportion <= 1",
            name="ck_user_recipe_ingredients_proportion_range",
        ),
        CheckConstraint(
            "nutrition_source_type IN ('canteen_recipe', 'local_database', 'USDA', 'AI_estimate', 'ai_recipe_estimate')",
            name="ck_user_recipe_ingredients_nutrition_source_type",
        ),
        CheckConstraint(
            "ingredient_source IN ('ai_estimate', 'user_confirmed')",
            name="ck_user_recipe_ingredients_ingredient_source",
        ),
        CheckConstraint(
            "weight_source IN ('ai_estimate', 'user_confirmed')",
            name="ck_user_recipe_ingredients_weight_source",
        ),
        UniqueConstraint("recipe_id", "position", name="uq_user_recipe_ingredients_recipe_position"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipe_id: Mapped[int] = mapped_column(
        ForeignKey("user_recipes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(160), nullable=False)
    normalized_proportion: Mapped[Decimal] = mapped_column(Numeric(12, 9), nullable=False)
    nutrition_source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    resolved_reference: Mapped[str] = mapped_column(Text, nullable=False)
    ingredient_source: Mapped[str] = mapped_column(String(32), nullable=False)
    weight_source: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    recipe: Mapped[UserRecipe] = relationship(back_populates="ingredients")


@event.listens_for(UserRecipe, "before_insert")
@event.listens_for(UserRecipe, "before_update")
def set_normalized_recipe_name(_, __, recipe: UserRecipe) -> None:
    recipe.name = clean_food_name(recipe.name)
    recipe.normalized_name = normalize_food_name(recipe.name)


@event.listens_for(UserRecipeIngredient, "before_insert")
@event.listens_for(UserRecipeIngredient, "before_update")
def set_normalized_ingredient_name(_, __, ingredient: UserRecipeIngredient) -> None:
    ingredient.name_snapshot = clean_food_name(ingredient.name_snapshot)
    ingredient.normalized_name = normalize_food_name(ingredient.name_snapshot)
