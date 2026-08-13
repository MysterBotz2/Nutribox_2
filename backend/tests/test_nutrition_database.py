from collections.abc import Generator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.base import Base
from app.database.database import get_db
from app.main import app
from app.models.food import Food
from app.models.meal import Meal


def create_test_food(name: str = "Test White Rice") -> Food:
    return Food(
        name=name,
        category="test",
        calories_per_100g=Decimal("100.00"),
        protein_g_per_100g=Decimal("10.000"),
        carbohydrates_g_per_100g=Decimal("20.000"),
        fat_g_per_100g=Decimal("3.000"),
        fiber_g_per_100g=Decimal("2.000"),
        source_name="Synthetic test source",
        source_reference="test-only",
        is_verified=False,
    )


@pytest.fixture
def database_session() -> Generator[Session, None, None]:
    test_database_url = settings.test_database_url
    if not test_database_url:
        pytest.skip("Set TEST_DATABASE_URL to run PostgreSQL nutrition integration tests.")
    if test_database_url == settings.database_url:
        pytest.skip("TEST_DATABASE_URL must be different from DATABASE_URL.")

    test_engine = create_engine(test_database_url)
    with test_engine.connect() as connection:
        transaction = connection.begin()
        Base.metadata.create_all(connection)
        session = Session(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()
    test_engine.dispose()


@pytest.fixture
def client(database_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield database_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_food_model_can_be_persisted_and_normalized(database_session: Session) -> None:
    food = create_test_food("  Test   White Rice ")
    database_session.add(food)
    database_session.flush()

    assert food.id is not None
    assert food.name == "Test White Rice"
    assert food.normalized_name == "test white rice"


def test_duplicate_normalized_food_name_is_rejected(database_session: Session) -> None:
    database_session.add(create_test_food("Test White Rice"))
    database_session.flush()

    with database_session.begin_nested():
        database_session.add(create_test_food("  test   white RICE  "))
        with pytest.raises(IntegrityError):
            database_session.flush()


def test_search_finds_food_case_insensitively(
    database_session: Session, client: TestClient
) -> None:
    database_session.add(create_test_food("Test White Rice"))
    database_session.flush()

    response = client.get("/api/nutrition/search", params={"q": "RICE"})

    assert response.status_code == 200
    assert response.json()["foods"][0]["normalized_name"] == "test white rice"


def test_search_with_no_matches_returns_empty_collection(client: TestClient) -> None:
    response = client.get("/api/nutrition/search", params={"q": "missing"})

    assert response.status_code == 200
    assert response.json() == {"foods": []}


def test_get_food_returns_structured_per_100g_response(
    database_session: Session, client: TestClient
) -> None:
    food = create_test_food()
    database_session.add(food)
    database_session.flush()

    response = client.get(f"/api/nutrition/{food.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == food.id
    assert payload["name"] == "Test White Rice"
    assert {key: payload["nutrition_per_100g"][key] for key in ("calories", "protein_g", "carbohydrates_g", "fat_g", "fiber_g")} == {
        "calories": "100.00", "protein_g": "10.000", "carbohydrates_g": "20.000", "fat_g": "3.000", "fiber_g": "2.000",
    }
    assert payload["source"] == {"name": "Synthetic test source", "reference": "test-only", "verified": False, "category": None}


def test_unknown_food_id_returns_404(client: TestClient) -> None:
    response = client.get("/api/nutrition/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Food record was not found."}


def test_calculate_food_returns_portion_nutrition(
    database_session: Session, client: TestClient
) -> None:
    food = create_test_food("Test Food")
    database_session.add(food)
    database_session.flush()

    response = client.post(
        "/api/nutrition/calculate",
        json={"food_id": food.id, "weight_grams": "180"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["food"] == {"id": food.id, "name": "Test Food"}
    assert payload["weight_grams"] == "180"
    assert {key: payload["nutrition"][key] for key in ("calories", "protein_g", "carbohydrates_g", "fat_g", "fiber_g")} == {
        "calories": "180.000", "protein_g": "18.000", "carbohydrates_g": "36.000", "fat_g": "5.400", "fiber_g": "3.600",
    }


def test_calculate_unknown_food_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/nutrition/calculate",
        json={"food_id": 999999, "weight_grams": "180"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Food record was not found."}


def test_create_one_item_meal_and_return_snapshots(database_session: Session, client: TestClient, auth_headers: dict[str, str]) -> None:
    food = create_test_food("Test Food")
    database_session.add(food)
    database_session.flush()

    response = client.post("/api/meals", json={"items": [{"food_id": food.id, "weight_grams": "180"}]}, headers=auth_headers)

    assert response.status_code == 201
    assert response.json()["items"][0]["food"]["name"] == "Test Food"
    assert response.json()["items"][0]["nutrition"]["calories"] == "180.000"
    assert response.json()["totals"]["calories"] == "180.000"


def test_create_multi_item_meal_allows_duplicate_food_ids(database_session: Session, client: TestClient, auth_headers: dict[str, str]) -> None:
    food = create_test_food("Test Food")
    database_session.add(food)
    database_session.flush()

    response = client.post("/api/meals", json={"items": [{"food_id": food.id, "weight_grams": "100"}, {"food_id": food.id, "weight_grams": "50"}]}, headers=auth_headers)

    assert response.status_code == 201
    assert len(response.json()["items"]) == 2
    assert response.json()["totals"]["calories"] == "150.000"


def test_unknown_food_rolls_back_entire_meal(database_session: Session, client: TestClient, auth_headers: dict[str, str]) -> None:
    food = create_test_food("Test Food")
    database_session.add(food)
    database_session.flush()

    response = client.post("/api/meals", json={"items": [{"food_id": food.id, "weight_grams": "100"}, {"food_id": 999999, "weight_grams": "100"}]}, headers=auth_headers)

    assert response.status_code == 404
    assert database_session.scalar(select(func.count()).select_from(Meal)) == 0


@pytest.mark.parametrize("items", [[], [{"food_id": 1, "weight_grams": "0"}], [{"food_id": 1, "weight_grams": "-1"}], [{"food_id": 1, "weight_grams": "5000.1"}]])
def test_meal_creation_rejects_invalid_items(client: TestClient, auth_headers: dict[str, str], items: list[dict[str, object]]) -> None:
    response = client.post("/api/meals", json={"items": items}, headers=auth_headers)

    assert response.status_code == 422


def test_get_and_list_meals_newest_first_with_pagination(database_session: Session, client: TestClient, auth_headers: dict[str, str]) -> None:
    food = create_test_food("Test Food")
    database_session.add(food)
    database_session.flush()
    first = client.post("/api/meals", json={"items": [{"food_id": food.id, "weight_grams": "100"}]}, headers=auth_headers).json()
    second = client.post("/api/meals", json={"items": [{"food_id": food.id, "weight_grams": "200"}]}, headers=auth_headers).json()

    detail = client.get(f"/api/meals/{first['id']}", headers=auth_headers)
    listed = client.get("/api/meals", params={"limit": 1, "offset": 0}, headers=auth_headers)

    assert detail.status_code == 200
    assert detail.json()["items"][0]["nutrition"]["calories"] == "100.000"
    assert listed.status_code == 200
    assert listed.json()["meals"][0]["id"] == second["id"]
    assert client.get("/api/meals/999999", headers=auth_headers).status_code == 404


def test_meal_detail_uses_stored_snapshot_after_food_reference_changes(database_session: Session, client: TestClient, auth_headers: dict[str, str]) -> None:
    food = create_test_food("Test Food")
    database_session.add(food)
    database_session.flush()
    created = client.post("/api/meals", json={"items": [{"food_id": food.id, "weight_grams": "100"}]}, headers=auth_headers).json()

    food.name = "Changed Test Food"
    food.calories_per_100g = Decimal("999.00")
    database_session.flush()
    response = client.get(f"/api/meals/{created['id']}", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["items"][0]["food"]["name"] == "Test Food"
    assert response.json()["items"][0]["nutrition"]["calories"] == "100.000"
