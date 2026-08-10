from collections.abc import Generator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.base import Base
from app.database.database import get_db
from app.main import app
from app.models.food import Food


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
        session = Session(bind=connection, expire_on_commit=False)
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
    assert response.json() == {
        "id": food.id,
        "name": "Test White Rice",
        "normalized_name": "test white rice",
        "category": "test",
        "nutrition_per_100g": {
            "calories": "100.00",
            "protein_g": "10.000",
            "carbohydrates_g": "20.000",
            "fat_g": "3.000",
            "fiber_g": "2.000",
        },
        "source": {
            "name": "Synthetic test source",
            "reference": "test-only",
            "verified": False,
        },
    }


def test_unknown_food_id_returns_404(client: TestClient) -> None:
    response = client.get("/api/nutrition/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Food record was not found."}
