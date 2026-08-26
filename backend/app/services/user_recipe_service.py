from decimal import Decimal, ROUND_HALF_UP

from pydantic import ValidationError

from app.models.food import clean_food_name, normalize_food_name
from app.models.user_recipe import UserRecipe, UserRecipeIngredient
from app.repositories.user_recipe_repository import UserRecipeRepository
from app.schemas.meal_analysis_session import ComponentResolutionStatus, MealAnalysisSessionState
from app.services.meal_analysis_session_service import MealAnalysisSessionService


class UserRecipeNotFoundError(ValueError):
    """Raised when an owner-scoped personal recipe is absent."""


class UserRecipeSaveEligibilityError(ValueError):
    """Raised when analysis-session state cannot safely become a reusable recipe."""


class UserRecipeService:
    """Owner-scoped personal recipes reconstructed from trusted session state."""

    _PROPORTION_QUANTUM = Decimal("0.000000001")

    def __init__(
        self,
        repository: UserRecipeRepository,
        analysis_session_service: MealAnalysisSessionService,
    ) -> None:
        self._repository = repository
        self._analysis_session_service = analysis_session_service

    def save_from_analysis_component(
        self,
        *,
        user_id: int,
        analysis_session_id: int,
        component_id: str,
        recipe_name_override: str | None = None,
    ) -> UserRecipe:
        """Persist a new recipe variation from one resolved confirmed composite."""
        session = self._repository.session
        transaction = session.begin_nested() if session.in_transaction() else session.begin()
        with transaction:
            persisted = self._analysis_session_service.get_session_for_user(
                analysis_session_id, user_id
            )
            if persisted.status != "calculated":
                raise UserRecipeSaveEligibilityError(
                    "Meal analysis session is not ready to save a recipe."
                )
            try:
                state = MealAnalysisSessionState.model_validate(persisted.state)
            except ValidationError as error:
                raise UserRecipeSaveEligibilityError(
                    "Meal analysis session state is invalid for recipe saving."
                ) from error

            component = next(
                (item for item in state.components if str(item.component_id) == component_id),
                None,
            )
            if component is None:
                raise UserRecipeSaveEligibilityError("Meal analysis component was not found.")
            if component.resolution_status != ComponentResolutionStatus.RESOLVED:
                raise UserRecipeSaveEligibilityError(
                    "Meal analysis component is not fully resolved."
                )
            provenance = component.composite_provenance_snapshot
            if provenance is None:
                raise UserRecipeSaveEligibilityError(
                    "Only resolved composite meal components can be saved as recipes."
                )
            if provenance.composition_source != "user_confirmed":
                raise UserRecipeSaveEligibilityError(
                    "Recipe composition must be explicitly user-confirmed."
                )
            if (
                provenance.dish_name != component.recognized_name
                or provenance.dish_weight_grams != component.estimated_weight_grams
            ):
                raise UserRecipeSaveEligibilityError(
                    "Composite recipe provenance does not match its meal component."
                )

            recipe_name = self._recipe_name(component.recognized_name, recipe_name_override)
            proportions = self._normalized_proportions(
                component.estimated_weight_grams,
                [ingredient.estimated_weight_grams for ingredient in provenance.ingredients],
            )
            ingredients: list[UserRecipeIngredient] = []
            for position, (ingredient, proportion) in enumerate(
                zip(provenance.ingredients, proportions, strict=True), start=1
            ):
                if not ingredient.source_reference_id or not ingredient.nutrition_source:
                    raise UserRecipeSaveEligibilityError(
                        "Confirmed recipe ingredients require authoritative nutrition references."
                    )
                ingredients.append(
                    UserRecipeIngredient(
                        position=position,
                        name_snapshot=ingredient.ingredient_name,
                        normalized_name=normalize_food_name(ingredient.ingredient_name),
                        normalized_proportion=proportion,
                        nutrition_source_type=ingredient.nutrition_source,
                        resolved_reference=ingredient.source_reference_id,
                        ingredient_source=ingredient.ingredient_source,
                        weight_source=ingredient.weight_source.value,
                    )
                )

            recipe = UserRecipe(
                user_id=user_id,
                name=recipe_name,
                normalized_name=normalize_food_name(recipe_name),
                source_type="user_confirmed",
                ingredients=ingredients,
            )
            return self._repository.create(recipe)

    def get_for_user(self, recipe_id: int, user_id: int) -> UserRecipe:
        recipe = self._repository.get_by_id_for_user(recipe_id, user_id)
        if recipe is None:
            raise UserRecipeNotFoundError("Personal recipe was not found.")
        return recipe

    def list_for_user(self, user_id: int) -> list[UserRecipe]:
        return self._repository.list_for_user(user_id)

    def delete_for_user(self, recipe_id: int, user_id: int) -> None:
        session = self._repository.session
        transaction = session.begin_nested() if session.in_transaction() else session.begin()
        with transaction:
            if not self._repository.delete_for_user(recipe_id, user_id):
                raise UserRecipeNotFoundError("Personal recipe was not found.")
            session.flush()

    @classmethod
    def _normalized_proportions(
        cls, component_weight: Decimal, ingredient_weights: list[Decimal]
    ) -> list[Decimal]:
        if not component_weight.is_finite() or component_weight <= 0:
            raise UserRecipeSaveEligibilityError("Composite component weight must be positive.")
        if not ingredient_weights or any(
            not weight.is_finite() or weight <= 0 for weight in ingredient_weights
        ):
            raise UserRecipeSaveEligibilityError(
                "Composite recipe ingredients must have positive finite weights."
            )
        if sum(ingredient_weights, Decimal("0")) != component_weight:
            raise UserRecipeSaveEligibilityError(
                "Composite ingredient weights must equal the component weight exactly."
            )

        rounded = [
            (weight / component_weight).quantize(cls._PROPORTION_QUANTUM, rounding=ROUND_HALF_UP)
            for weight in ingredient_weights[:-1]
        ]
        final_proportion = Decimal("1") - sum(rounded, Decimal("0"))
        if final_proportion <= 0 or final_proportion > 1:
            raise UserRecipeSaveEligibilityError("Composite recipe proportions are invalid.")
        proportions = [*rounded, final_proportion]
        if sum(proportions, Decimal("0")) != Decimal("1"):
            raise UserRecipeSaveEligibilityError("Composite recipe proportions do not reconcile.")
        return proportions

    @staticmethod
    def _recipe_name(component_name: str, override: str | None) -> str:
        try:
            name = clean_food_name(override if override is not None else component_name)
        except ValueError as error:
            raise UserRecipeSaveEligibilityError("Recipe name must not be blank.") from error
        if len(name) > 160:
            raise UserRecipeSaveEligibilityError("Recipe name is too long.")
        return name
