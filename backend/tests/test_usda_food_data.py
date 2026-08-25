import json
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


def test_usda_search_requests_a_bounded_larger_set_and_preserves_source_order() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/foods/search")
        assert json.loads(request.content)["pageSize"] == 25
        return httpx.Response(200, json={"foods": [
            {"fdcId": 2, "description": "Second result", "dataType": "Survey (FNDDS)"},
            {"fdcId": 1, "description": "First result", "dataType": "Foundation"},
        ]})

    client = _client(handler)
    results = client.search_food("test")

    assert [result.fdc_id for result in results] == [2, 1]


def test_usda_search_only_exposes_nonempty_eligible_descriptions_to_the_resolver() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"foods": [
            {"fdcId": 1, "description": "  Chicken wing, fried  ", "dataType": "Survey (FNDDS)"},
            {"fdcId": 2, "description": "   ", "dataType": "Foundation"},
            {"fdcId": 3, "description": "Chicken wing, fried", "dataType": "Branded"},
        ]})

    results = _client(handler).search_food("fried chicken")

    assert [result.description for result in results] == ["Chicken wing, fried"]


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
    assert resolution.candidate_names == ("Rice",)


def _ranked_names(query: str, *descriptions: str) -> list[str]:
    candidates = [UsdaSearchFood(index + 1, description, "Survey (FNDDS)") for index, description in enumerate(descriptions)]
    return [candidate.description for candidate in UsdaFoodReferenceService._rank_relevant_candidates(query, candidates)]


_LIVE_LIKE_FRIED_CHICKEN_CANDIDATES = (
    "Chicken fillet sandwich, fried, on wheat bun",
    "Chicken fillet sandwich, fried, on white bun",
    "Chicken wing, fried, coated, from raw",
    "Chicken wing, fried, coated, from restaurant",
    "Chicken, broilers or fryers, giblets, cooked, fried",
)


def test_usda_relevance_ranks_direct_fried_chicken_above_composites_and_offal() -> None:
    ranked = _ranked_names(
        "fried chicken",
        "Chicken fillet sandwich, fried, on wheat bun",
        "Chicken, broilers or fryers, giblets, cooked, fried",
        "Chicken wing, fried, coated, from restaurant",
        "Chicken breast, fried, breaded",
    )

    assert ranked[:2] == [
        "Chicken wing, fried, coated, from restaurant",
        "Chicken breast, fried, breaded",
    ]
    assert "Chicken fillet sandwich, fried, on wheat bun" not in ranked
    assert "Chicken, broilers or fryers, giblets, cooked, fried" not in ranked


def test_live_like_fried_chicken_candidates_return_only_direct_wing_choices(
    database_session: Session,
) -> None:
    class LiveLikeClient:
        def search_food(self, _: str):
            return [
                UsdaSearchFood(index + 1, description, "Survey (FNDDS)")
                for index, description in enumerate(_LIVE_LIKE_FRIED_CHICKEN_CANDIDATES)
            ]

    resolution = UsdaFoodReferenceService(
        FoodRepository(database_session), LiveLikeClient()  # type: ignore[arg-type]
    ).resolve("fried chicken")

    assert resolution.food is None
    assert resolution.candidate_names == (
        "Chicken wing, fried, coated, from raw",
        "Chicken wing, fried, coated, from restaurant",
    )


def test_semantic_fallback_returns_safe_candidates_when_strict_threshold_has_none(
    database_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FallbackClient:
        def search_food(self, _: str):
            return [
                UsdaSearchFood(1, "Chicken wing, fried, coated, from raw", "Survey (FNDDS)"),
                UsdaSearchFood(2, "Chicken fillet sandwich, fried, on wheat bun", "Survey (FNDDS)"),
                UsdaSearchFood(3, "Chicken, broilers or fryers, giblets, cooked, fried", "Survey (FNDDS)"),
            ]

        def get_food(self, fdc_id: int):
            return _FakeClient().get_food(fdc_id)

    monkeypatch.setattr(UsdaFoodReferenceService, "_MINIMUM_RELEVANCE_SCORE", 100)
    resolution = UsdaFoodReferenceService(
        FoodRepository(database_session), FallbackClient()  # type: ignore[arg-type]
    ).resolve("fried chicken")

    assert resolution.food is not None
    assert resolution.food.source_reference == "fdcId:1"


def test_semantic_fallback_returns_not_found_when_no_safe_candidate_survives(
    database_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    class UnsafeFallbackClient:
        def search_food(self, _: str):
            return [
                UsdaSearchFood(1, "Chicken fillet sandwich, fried, on wheat bun", "Survey (FNDDS)"),
                UsdaSearchFood(2, "Chicken, broilers or fryers, giblets, cooked, fried", "Survey (FNDDS)"),
            ]

    monkeypatch.setattr(UsdaFoodReferenceService, "_MINIMUM_RELEVANCE_SCORE", 100)
    resolution = UsdaFoodReferenceService(
        FoodRepository(database_session), UnsafeFallbackClient()  # type: ignore[arg-type]
    ).resolve("fried chicken")

    assert resolution.food is None
    assert resolution.candidate_names == ()


def test_beef_stew_requires_the_dish_identity_and_excludes_noisy_beef_results(
    database_session: Session,
) -> None:
    class BeefStewClient:
        def search_food(self, _: str):
            return [
                UsdaSearchFood(1, "Beef stew, home prepared", "Survey (FNDDS)"),
                UsdaSearchFood(2, "Stew, beef, home prepared", "SR Legacy"),
                UsdaSearchFood(3, "Beef, cooked in gravy, stew-style", "Foundation"),
                UsdaSearchFood(4, "Beef burger sandwich", "Survey (FNDDS)"),
                UsdaSearchFood(5, "Beef steak, grilled", "Foundation"),
            ]

    resolution = UsdaFoodReferenceService(
        FoodRepository(database_session), BeefStewClient()  # type: ignore[arg-type]
    ).resolve("beef stew")

    assert resolution.food is None
    assert resolution.candidate_names == (
        "Beef stew, home prepared",
        "Stew, beef, home prepared",
        "Beef, cooked in gravy, stew-style",
    )


def test_usda_relevance_respects_explicit_composites_and_specific_cuts() -> None:
    sandwich_ranked = _ranked_names(
        "fried chicken sandwich",
        "Chicken fillet sandwich, fried, on wheat bun",
        "Chicken wing, fried, coated",
    )
    cut_ranked = _ranked_names(
        "fried chicken wing",
        "Chicken breast, fried, breaded",
        "Chicken wing, fried, coated",
        "Chicken thigh, fried",
    )

    assert sandwich_ranked[0] == "Chicken fillet sandwich, fried, on wheat bun"
    assert cut_ranked[0] == "Chicken wing, fried, coated"


def test_usda_relevance_rejects_conflicting_preparation_and_irrelevant_results() -> None:
    ranked = _ranked_names(
        "grilled chicken",
        "Chicken, grilled",
        "Chicken, fried",
        "Apple pie",
    )

    assert ranked == ["Chicken, grilled"]


def test_prepared_dish_identity_rejects_generic_pork_rows_for_composite_fallback(database_session: Session) -> None:
    class PorkRows:
        def search_food(self, _: str):
            return [
                UsdaSearchFood(1, "Pork, pickled pork hocks", "Survey (FNDDS)"),
                UsdaSearchFood(2, "Pork, cured, salt pork, raw", "Survey (FNDDS)"),
                UsdaSearchFood(3, "Pork, cracklings", "Survey (FNDDS)"),
                UsdaSearchFood(4, "Pork, belly", "Survey (FNDDS)"),
                UsdaSearchFood(5, "Pork, bones", "Survey (FNDDS)"),
            ]

    resolution = UsdaFoodReferenceService(FoodRepository(database_session), PorkRows()).resolve("pork sinigang")  # type: ignore[arg-type]
    assert resolution.food is None
    assert resolution.candidates == ()
    assert resolution.candidate_names == ()


def test_one_strict_steamed_rice_candidate_auto_resolves_by_fdc_id(database_session: Session) -> None:
    class RiceRows:
        def __init__(self) -> None:
            self.loaded: list[int] = []

        def search_food(self, _: str):
            return [UsdaSearchFood(25, "Rice, white, steamed, Chinese restaurant", "Survey (FNDDS)")]

        def get_food(self, fdc_id: int):
            self.loaded.append(fdc_id)
            return _FakeClient().get_food(fdc_id)

    client = RiceRows()
    resolution = UsdaFoodReferenceService(FoodRepository(database_session), client).resolve("steamed rice")  # type: ignore[arg-type]
    assert resolution.food is not None
    assert resolution.food.source_reference == "fdcId:25"
    assert client.loaded == [25]


def test_chili_sauce_suitability_rejects_cheese_dip_but_preserves_real_sauce_ambiguity(database_session: Session) -> None:
    class ChiliRows:
        def search_food(self, _: str):
            return [
                UsdaSearchFood(1, "Tomato chili sauce", "Survey (FNDDS)"),
                UsdaSearchFood(2, "Sauce, tomato chili sauce, bottled, with salt", "Survey (FNDDS)"),
                UsdaSearchFood(3, "Sauce, peppers, hot, chili, mature red, canned", "Survey (FNDDS)"),
                UsdaSearchFood(4, "Cheese dip with chili pepper", "Survey (FNDDS)"),
            ]

    resolution = UsdaFoodReferenceService(FoodRepository(database_session), ChiliRows()).resolve("chili dipping sauce")  # type: ignore[arg-type]
    assert resolution.food is None
    assert resolution.candidate_names == (
        "Tomato chili sauce", "Sauce, tomato chili sauce, bottled, with salt", "Sauce, peppers, hot, chili, mature red, canned",
    )


def test_usda_relevance_returns_ranked_ambiguity_without_changing_selection_behavior(
    database_session: Session,
) -> None:
    class AmbiguousChickenClient:
        def search_food(self, _: str):
            return [
                UsdaSearchFood(1, "Chicken fillet sandwich, fried, on wheat bun", "Survey (FNDDS)"),
                UsdaSearchFood(2, "Chicken wing, fried, coated, from restaurant", "Survey (FNDDS)"),
                UsdaSearchFood(3, "Chicken thigh, fried", "Survey (FNDDS)"),
            ]

    resolution = UsdaFoodReferenceService(
        FoodRepository(database_session), AmbiguousChickenClient()  # type: ignore[arg-type]
    ).resolve("fried chicken")

    assert resolution.food is None
    assert resolution.candidate_names == (
        "Chicken wing, fried, coated, from restaurant",
        "Chicken thigh, fried",
    )


def test_usda_relevance_returns_no_candidates_when_none_are_relevant(database_session: Session) -> None:
    class IrrelevantClient:
        def search_food(self, _: str):
            return [UsdaSearchFood(1, "Apple pie", "Survey (FNDDS)")]

    resolution = UsdaFoodReferenceService(
        FoodRepository(database_session), IrrelevantClient()  # type: ignore[arg-type]
    ).resolve("fried chicken")

    assert resolution.food is None
    assert resolution.candidate_names == ()
