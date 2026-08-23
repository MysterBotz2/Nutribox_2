from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.food import Food
from app.repositories.food_repository import FoodRepository
from app.routers.meals import get_meal_analysis_service
from app.services.food_recognition_provider import FoodRecognitionProvider, FoodRecognitionResult
from app.services.meal_analysis_service import MealAnalysisService
from app.services.nutrition_service import NutritionService
from conftest import register_and_login


def _food() -> Food:
    return Food(name="Leftover test food", category="test", calories_per_100g=Decimal("100"), protein_g_per_100g=Decimal("10"), carbohydrates_g_per_100g=Decimal("20"), fat_g_per_100g=Decimal("3"), fiber_g_per_100g=Decimal("2"), source_name="test", source_reference="test", is_verified=False)


def _meal(client: TestClient, headers: dict[str, str], food: Food) -> dict:
    response = client.post("/api/meals", json={"items": [{"food_id": food.id, "weight_grams": "100"}]}, headers=headers)
    assert response.status_code == 201
    return response.json()


def test_leftover_requires_auth_and_owner_access(client: TestClient, database_session: Session, jwt_configuration: None) -> None:
    food = _food(); database_session.add(food); database_session.flush()
    _, owner = register_and_login(client, "owner-leftover@example.com")
    _, other = register_and_login(client, "other-leftover@example.com")
    meal = _meal(client, owner, food)
    assert client.post(f"/api/meals/{meal['id']}/leftover-analysis", data={"leftover_weight_grams": "0"}).status_code == 401
    assert client.post(f"/api/meals/{meal['id']}/leftover-analysis", data={"leftover_weight_grams": "0"}, headers=other).status_code == 404
    created = client.post(f"/api/meals/{meal['id']}/leftover-analysis", data={"leftover_weight_grams": "0"}, headers=owner)
    assert created.status_code == 201
    body = created.json()
    expected_totals = {key: meal["totals"][key] for key in body["initial_nutrition"]}
    assert body["initial_nutrition"] == expected_totals
    assert body["leftover_nutrition"] == {"calories": "0", "protein_g": "0", "carbohydrates_g": "0", "fat_g": "0", "fiber_g": "0"}
    assert body["consumed_nutrition"] == expected_totals
    assert client.get(f"/api/meals/{meal['id']}/leftover-analysis", headers=owner).status_code == 200
    assert client.get(f"/api/meals/{meal['id']}/leftover-analysis", headers=other).status_code == 404
    assert client.post(f"/api/meals/{meal['id']}/leftover-analysis", data={"leftover_weight_grams": "0"}, headers=owner).status_code == 409
    unchanged = client.get(f"/api/meals/{meal['id']}", headers=owner).json()
    assert unchanged["id"] == meal["id"]
    assert unchanged["totals"] == meal["totals"]
    assert unchanged["items"][0]["id"] == meal["items"][0]["id"]
    assert Decimal(unchanged["items"][0]["weight_grams"]) == Decimal(meal["items"][0]["weight_grams"])


def test_nonzero_leftover_requires_image(client: TestClient, database_session: Session, auth_headers: dict[str, str]) -> None:
    food = _food(); database_session.add(food); database_session.flush()
    meal = _meal(client, auth_headers, food)
    response = client.post(f"/api/meals/{meal['id']}/leftover-analysis", data={"leftover_weight_grams": "10"}, headers=auth_headers)
    assert response.status_code == 422


class _NoRecognitionProvider(FoodRecognitionProvider):
    def recognize_food(self, *, image_bytes: bytes, content_type: str) -> FoodRecognitionResult:
        raise AssertionError("Zero-leftover analysis must not call recognition.")


def test_zero_leftover_bypasses_recognition(client: TestClient, database_session: Session, auth_headers: dict[str, str]) -> None:
    food = _food(); database_session.add(food); database_session.flush()
    meal = _meal(client, auth_headers, food)
    app_service = MealAnalysisService(_NoRecognitionProvider(), NutritionService(FoodRepository(database_session)))
    client.app.dependency_overrides[get_meal_analysis_service] = lambda: app_service
    response = client.post(f"/api/meals/{meal['id']}/leftover-analysis", data={"leftover_weight_grams": "0"}, headers=auth_headers)
    assert response.status_code == 201
