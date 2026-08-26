from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SaveUserRecipeRequest(BaseModel):
    """Optional safe display-name override for trusted session-derived recipes."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=160)


class UserRecipeIngredientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    normalized_proportion: Decimal
    nutrition_source: str
    resolved_reference: str
    ingredient_source: str
    weight_source: str


class UserRecipeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    source_type: str
    created_at: datetime
    updated_at: datetime
    ingredients: list[UserRecipeIngredientResponse]


class UserRecipeListResponse(BaseModel):
    recipes: list[UserRecipeResponse]


def user_recipe_response_from_model(recipe) -> UserRecipeResponse:
    """Serialize a recipe without exposing persistence-only fields."""
    return UserRecipeResponse(
        id=recipe.id,
        name=recipe.name,
        source_type=recipe.source_type,
        created_at=recipe.created_at,
        updated_at=recipe.updated_at,
        ingredients=[
            {
                "name": ingredient.name_snapshot,
                "normalized_proportion": ingredient.normalized_proportion,
                "nutrition_source": ingredient.nutrition_source_type,
                "resolved_reference": ingredient.resolved_reference,
                "ingredient_source": ingredient.ingredient_source,
                "weight_source": ingredient.weight_source,
            }
            for ingredient in recipe.ingredients
        ],
    )
