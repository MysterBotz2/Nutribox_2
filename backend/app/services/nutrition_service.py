from app.models.food import Food, normalize_food_name
from app.repositories.food_repository import FoodRepository


class NutritionService:
    """Application-level lookup behavior for food nutrition reference data."""

    def __init__(self, food_repository: FoodRepository) -> None:
        self._food_repository = food_repository

    def get_food(self, food_id: int) -> Food | None:
        return self._food_repository.get_by_id(food_id)

    def search_foods(self, query: str) -> list[Food]:
        if not query.strip():
            return []
        return self._food_repository.search(normalize_food_name(query))
