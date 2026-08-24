"""Small, backend-only adapter for USDA FoodData Central reference data."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import logging
from typing import Any

import httpx


logger = logging.getLogger(__name__)


class UsdaFoodDataError(RuntimeError):
    """A normalized, non-transport USDA failure safe for domain callers."""


@dataclass(frozen=True)
class UsdaSearchFood:
    fdc_id: int
    description: str
    data_type: str


@dataclass(frozen=True)
class UsdaFoodReference:
    fdc_id: int
    description: str
    nutrients: dict[str, Decimal | None]


class UsdaFoodDataClient:
    """Fetch USDA data without exposing HTTP exceptions or API-key details."""

    _DATA_TYPES = ("Foundation", "Survey (FNDDS)", "SR Legacy")
    _SEARCH_PAGE_SIZE = 25
    _NUTRIENTS = {
        1008: ("calories", "kcal"), 1003: ("protein_g", "g"),
        1005: ("carbohydrates_g", "g"), 1004: ("fat_g", "g"),
        1258: ("saturated_fat_g", "g"), 1079: ("fiber_g", "g"),
        2000: ("sugars_g", "g"), 1093: ("sodium_mg", "mg"),
        1253: ("cholesterol_mg", "mg"), 1087: ("calcium_mg", "mg"),
        1092: ("potassium_mg", "mg"), 1095: ("zinc_mg", "mg"),
        1089: ("iron_mg", "mg"), 1090: ("magnesium_mg", "mg"),
        1162: ("vitamin_c_mg", "mg"), 1114: ("vitamin_d_mcg", "µg"),
        1178: ("vitamin_b12_mcg", "µg"), 1177: ("folate_mcg_dfe", "µg"),
    }

    def __init__(self, *, api_key: str, base_url: str, timeout_seconds: int, client: httpx.Client | None = None) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=timeout_seconds)

    def search_food(self, query: str) -> list[UsdaSearchFood]:
        payload = self._request("POST", "/foods/search", json={"query": query, "dataType": list(self._DATA_TYPES), "pageSize": self._SEARCH_PAGE_SIZE})
        foods = payload.get("foods") if isinstance(payload, dict) else None
        if not isinstance(foods, list):
            raise UsdaFoodDataError("USDA returned an invalid search response.")
        result: list[UsdaSearchFood] = []
        for food in foods:
            if not isinstance(food, dict):
                continue
            fdc_id, description, data_type = food.get("fdcId"), food.get("description"), food.get("dataType")
            if (
                isinstance(fdc_id, int)
                and isinstance(description, str)
                and description.strip()
                and isinstance(data_type, str)
                and data_type in self._DATA_TYPES
            ):
                result.append(UsdaSearchFood(fdc_id, description.strip(), data_type))
        # Preserve USDA result order as a deterministic tie-breaker for the
        # resolver's relevance scoring. It does not choose nutrition values.
        logger.info(
            "USDA search query=%r raw_candidates=%d eligible_candidates=%d",
            query,
            len(foods),
            len(result),
        )
        logger.debug(
            "USDA search eligible_descriptions=%s",
            [food.description for food in result],
        )
        return result

    def get_food(self, fdc_id: int) -> UsdaFoodReference:
        payload = self._request("GET", f"/food/{fdc_id}")
        if not isinstance(payload, dict) or not isinstance(payload.get("description"), str):
            raise UsdaFoodDataError("USDA returned an invalid food response.")
        nutrients = {name: None for name, _ in self._NUTRIENTS.values()}
        food_nutrients = payload.get("foodNutrients")
        if not isinstance(food_nutrients, list):
            raise UsdaFoodDataError("USDA returned an invalid nutrient response.")
        for row in food_nutrients:
            if not isinstance(row, dict):
                continue
            nutrient = row.get("nutrient") if isinstance(row.get("nutrient"), dict) else row
            nutrient_id = nutrient.get("id") or row.get("nutrientId")
            amount = row.get("amount") if "amount" in row else row.get("value")
            if nutrient_id not in self._NUTRIENTS or amount is None:
                continue
            name, expected_unit = self._NUTRIENTS[nutrient_id]
            unit = nutrient.get("unitName") or row.get("unitName")
            if unit is not None and not self._same_unit(str(unit), expected_unit):
                continue
            try:
                nutrients[name] = Decimal(str(amount))
            except (InvalidOperation, ValueError):
                raise UsdaFoodDataError("USDA returned an invalid nutrient value.") from None
        return UsdaFoodReference(fdc_id=fdc_id, description=payload["description"], nutrients=nutrients)

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = self._client.request(method, f"{self._base_url}{path}", params={"api_key": self._api_key}, **kwargs)
        except httpx.TimeoutException:
            raise UsdaFoodDataError("USDA reference lookup timed out.") from None
        except httpx.RequestError:
            raise UsdaFoodDataError("USDA reference lookup is unavailable.") from None
        if response.status_code == 429:
            raise UsdaFoodDataError("USDA reference lookup is rate limited.")
        if response.status_code >= 500:
            raise UsdaFoodDataError("USDA reference lookup is unavailable.")
        if response.is_error:
            raise UsdaFoodDataError("USDA reference lookup failed.")
        try:
            payload = response.json()
        except ValueError:
            raise UsdaFoodDataError("USDA returned an invalid response.") from None
        if not isinstance(payload, dict):
            raise UsdaFoodDataError("USDA returned an invalid response.")
        return payload

    @staticmethod
    def _same_unit(actual: str, expected: str) -> bool:
        normalized = actual.casefold().replace("micro", "µ").replace("ug", "µg")
        return normalized == expected.casefold()
