from dataclasses import dataclass

from app.models.food import Food, normalize_food_name
from app.repositories.food_repository import FoodRepository
from app.services.usda_food_data_client import UsdaFoodDataClient, UsdaFoodDataError


@dataclass(frozen=True)
class UsdaResolution:
    food: Food | None = None
    candidate_names: tuple[str, ...] = ()


class UsdaFoodReferenceService:
    """Resolve a local miss through USDA and cache a selected reference locally."""

    _REQUIRED = ("calories", "protein_g", "carbohydrates_g", "fat_g", "fiber_g")

    def __init__(self, food_repository: FoodRepository, client: UsdaFoodDataClient | None) -> None:
        self._food_repository = food_repository
        self._client = client

    def resolve(self, recognized_name: str) -> UsdaResolution:
        if self._client is None:
            return UsdaResolution()
        try:
            candidates = self._client.search_food(recognized_name)
        except UsdaFoodDataError:
            return UsdaResolution()
        exact = [candidate for candidate in candidates if normalize_food_name(candidate.description) == normalize_food_name(recognized_name)]
        if len(exact) != 1:
            return UsdaResolution(candidate_names=tuple(candidate.description for candidate in candidates[:5]))
        selected = exact[0]
        reference = f"fdcId:{selected.fdc_id}"
        cached = self._food_repository.get_by_source_reference(reference)
        if cached is not None:
            return UsdaResolution(food=cached)
        try:
            detail = self._client.get_food(selected.fdc_id)
        except UsdaFoodDataError:
            return UsdaResolution()
        if any(detail.nutrients[name] is None for name in self._REQUIRED):
            return UsdaResolution()
        food = Food(
            name=detail.description,
            category=selected.data_type,
            calories_per_100g=detail.nutrients["calories"],
            protein_g_per_100g=detail.nutrients["protein_g"],
            carbohydrates_g_per_100g=detail.nutrients["carbohydrates_g"],
            fat_g_per_100g=detail.nutrients["fat_g"],
            fiber_g_per_100g=detail.nutrients["fiber_g"],
            saturated_fat_g_per_100g=detail.nutrients["saturated_fat_g"],
            sugars_g_per_100g=detail.nutrients["sugars_g"],
            sodium_mg_per_100g=detail.nutrients["sodium_mg"],
            cholesterol_mg_per_100g=detail.nutrients["cholesterol_mg"],
            calcium_mg_per_100g=detail.nutrients["calcium_mg"],
            potassium_mg_per_100g=detail.nutrients["potassium_mg"],
            zinc_mg_per_100g=detail.nutrients["zinc_mg"],
            iron_mg_per_100g=detail.nutrients["iron_mg"],
            magnesium_mg_per_100g=detail.nutrients["magnesium_mg"],
            vitamin_c_mg_per_100g=detail.nutrients["vitamin_c_mg"],
            vitamin_d_mcg_per_100g=detail.nutrients["vitamin_d_mcg"],
            vitamin_b12_mcg_per_100g=detail.nutrients["vitamin_b12_mcg"],
            folate_mcg_dfe_per_100g=detail.nutrients["folate_mcg_dfe"],
            source_name="USDA FoodData Central",
            source_type="USDA",
            source_reference=reference,
            is_verified=False,
        )
        self._food_repository.add(food)
        self._food_repository.flush()
        return UsdaResolution(food=food)
