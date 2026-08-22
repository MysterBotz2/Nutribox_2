from decimal import Decimal

import httpx
import pytest
from sqlalchemy.orm import Session

from app.models.food import Food
from app.repositories.food_repository import FoodRepository
from app.services.usda_food_data_client import UsdaFoodDataClient, UsdaFoodDataError, UsdaFoodReference, UsdaSearchFood
from app.services.usda_food_reference_service import UsdaFoodReferenceService


def _client(handler) -> UsdaFoodDataClient:
    return UsdaFoodDataClient(api_key="test-only", base_url="https://example.test", timeout_seconds=1, client=httpx.Client(transport=httpx.MockTransport(handler)))


def _detail_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"description": "Plain rice", "foodNutrients": [
        {"nutrient": {"id": 1008, "unitName": "KCAL"}, "amount": 130},
        {"nutrient": {"id": 1003, "unitName": "g"}, "amount": 2.7},
        {"nutrient": {"id": 1005, "unitName": "g"}, "amount": 28},
        {"nutrient": {"id": 1004, "unitName": "g"}, "amount": 0.3},
        {"nutrient": {"id": 1079, "unitName": "g"}, "amount": 0},
        {"nutrient": {"id": 1093, "unitName": "mg"}, "amount": 0},
    ]})


def test_usda_mapping_preserves_missing_and_explicit_zero() -> None:
    reference = _client(_detail_response).get_food(123)
    assert reference.nutrients["fiber_g"] == Decimal("0")
    assert reference.nutrients["sodium_mg"] == Decimal("0")
    assert reference.nutrients["cholesterol_mg"] is None


@pytest.mark.parametrize("response", [httpx.Response(429), httpx.Response(503), httpx.Response(200, content=b"not-json")])
def test_usda_transport_failures_are_normalized(response: httpx.Response) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return response
    with pytest.raises(UsdaFoodDataError):
        _client(handler).search_food("rice")


class _FakeClient:
    def __init__(self) -> None:
        self.searches = 0
        self.details = 0

    def search_food(self, _: str) -> list[UsdaSearchFood]:
        self.searches += 1
        return [UsdaSearchFood(123, "Plain rice", "Foundation")]

    def get_food(self, _: int) -> UsdaFoodReference:
        self.details += 1
        return UsdaFoodReference(123, "Plain rice", {"calories": Decimal("130"), "protein_g": Decimal("2.7"), "carbohydrates_g": Decimal("28"), "fat_g": Decimal("0.3"), "fiber_g": Decimal("0"), "saturated_fat_g": None, "sugars_g": None, "sodium_mg": Decimal("0"), "cholesterol_mg": None, "calcium_mg": None, "potassium_mg": None, "zinc_mg": None, "iron_mg": None, "magnesium_mg": None, "vitamin_c_mg": None, "vitamin_d_mcg": None, "vitamin_b12_mcg": None, "folate_mcg_dfe": None})


def test_usda_reference_is_cached_and_reused(database_session: Session) -> None:
    fake = _FakeClient()
    service = UsdaFoodReferenceService(FoodRepository(database_session), fake)  # type: ignore[arg-type]
    first = service.resolve("Plain rice")
    second = service.resolve("Plain rice")
    assert first.food is not None and second.food is not None
    assert first.food.id == second.food.id
    assert first.food.source_type == "USDA"
    assert first.food.source_reference == "fdcId:123"
    assert fake.details == 1


def test_ambiguous_usda_results_are_not_selected(database_session: Session) -> None:
    class AmbiguousClient:
        def search_food(self, _: str):
            return [UsdaSearchFood(1, "Rice", "Foundation"), UsdaSearchFood(2, "Rice", "SR Legacy")]
    resolution = UsdaFoodReferenceService(FoodRepository(database_session), AmbiguousClient()).resolve("Rice")  # type: ignore[arg-type]
    assert resolution.food is None
    assert resolution.candidate_names == ("Rice", "Rice")
