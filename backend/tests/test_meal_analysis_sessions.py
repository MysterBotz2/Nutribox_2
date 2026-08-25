from datetime import timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.database.base import Base
from app.models.meal_analysis_session import MealAnalysisSession
from app.models.user import User
from app.repositories.meal_analysis_session_repository import MealAnalysisSessionRepository
from app.repositories.meal_repository import MealRepository
from app.schemas.meal_analysis_session import (
    CompositeIngredientSnapshot,
    CompositeProvenanceSnapshot,
    ComponentResolutionStatus,
    MealAnalysisSessionComponent,
    MealAnalysisSessionState,
)
from app.services.meal_analysis_session_service import (
    MealAnalysisSessionConsumedError,
    MealAnalysisSessionExpiredError,
    MealAnalysisSessionNotFoundError,
    MealAnalysisSessionService,
)
from app.services.meal_service import MealService
from app.services.nutrition_service import NutritionService
from app.repositories.food_repository import FoodRepository


def _state(weight: str = "150.000") -> MealAnalysisSessionState:
    return MealAnalysisSessionState(
        measured_weight_grams=Decimal(weight),
        components=[
            MealAnalysisSessionComponent(
                recognized_name="Rice",
                raw_estimated_proportion=Decimal("1"),
                normalized_proportion=Decimal("1"),
                estimated_weight_grams=Decimal(weight),
                resolution_status=ComponentResolutionStatus.RESOLVED,
                nutrition={"fiber_g": None, "calories": "150.000"},
            )
        ],
    )


def _user(session: Session, email: str) -> User:
    user = User(email=email, password_hash="not-used", first_name="Test", last_name="User")
    session.add(user)
    session.flush()
    return user


def _service(session: Session) -> MealAnalysisSessionService:
    return MealAnalysisSessionService(MealAnalysisSessionRepository(session))


def test_session_model_is_registered_and_matches_expected_columns() -> None:
    assert "meal_analysis_sessions" in Base.metadata.tables
    columns = inspect(MealAnalysisSession).columns
    assert columns["state"].type.__class__.__name__ == "JSONB"
    assert columns["expires_at"].type.timezone is True
    assert columns["consumed_at"].nullable is True


def test_session_create_owner_ttl_and_timezone_aware_timestamps(database_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "meal_analysis_session_ttl_minutes", 30)
    user = _user(database_session, "analysis-owner@example.com")
    item = _service(database_session).create_session(user.id, _state(), "requires_food_selection")
    database_session.refresh(item)

    assert item.user_id == user.id
    assert item.state["version"] == 1
    assert item.state["measured_weight_grams"] == "150.000"
    assert timedelta(minutes=29, seconds=59) <= item.expires_at - item.created_at <= timedelta(minutes=30, seconds=1)
    assert item.created_at.tzinfo is not None
    assert item.updated_at.tzinfo is not None
    assert item.expires_at.tzinfo is not None
    assert item.consumed_at is None
    assert item.created_at.astimezone(timezone.utc).utcoffset() == timedelta(0)


def test_session_owner_lookup_locking_and_domain_errors(database_session: Session) -> None:
    owner = _user(database_session, "analysis-owner-lookup@example.com")
    other = _user(database_session, "analysis-other-lookup@example.com")
    service = _service(database_session)
    item = service.create_session(owner.id, _state(), "pending")

    assert service.get_session_for_user(item.id, owner.id, lock=True).id == item.id
    with pytest.raises(MealAnalysisSessionNotFoundError):
        service.get_session_for_user(item.id, other.id)
    with pytest.raises(MealAnalysisSessionNotFoundError):
        service.get_session_for_user(999999, owner.id)


def test_session_expiry_consumption_and_update_guards(database_session: Session) -> None:
    owner = _user(database_session, "analysis-lifecycle@example.com")
    other = _user(database_session, "analysis-lifecycle-other@example.com")
    service = _service(database_session)
    item = service.create_session(owner.id, _state(), "pending")

    updated = service.update_session_state(item.id, owner.id, _state("151.000"), "updated")
    assert updated.status == "updated"
    assert updated.state["measured_weight_grams"] == "151.000"
    with pytest.raises(MealAnalysisSessionNotFoundError):
        service.update_session_state(item.id, other.id, _state(), "bad")

    consumed = service.consume_session(item.id, owner.id)
    assert consumed.consumed_at is not None and consumed.consumed_at.tzinfo is not None
    with pytest.raises(MealAnalysisSessionConsumedError):
        service.consume_session(item.id, owner.id)
    with pytest.raises(MealAnalysisSessionConsumedError):
        service.update_session_state(item.id, owner.id, _state(), "bad")


def test_session_expiration_is_inclusive_and_blocks_mutation(database_session: Session) -> None:
    owner = _user(database_session, "analysis-expired@example.com")
    service = _service(database_session)
    item = service.create_session(owner.id, _state(), "pending")
    item.expires_at = item.created_at
    database_session.flush()

    with pytest.raises(MealAnalysisSessionExpiredError):
        service.get_session_for_user(item.id, owner.id)
    with pytest.raises(MealAnalysisSessionExpiredError):
        service.update_session_state(item.id, owner.id, _state(), "bad")
    with pytest.raises(MealAnalysisSessionExpiredError):
        service.consume_session(item.id, owner.id)


@pytest.mark.parametrize("value", [0, -1, 1441, "invalid"])
def test_session_ttl_bounds_reject_invalid_values(value: object) -> None:
    with pytest.raises(ValueError):
        Settings(_env_file=None, meal_analysis_session_ttl_minutes=value)


def test_session_ttl_bounds_accept_minimum_default_and_maximum() -> None:
    assert Settings(_env_file=None).meal_analysis_session_ttl_minutes == 30
    assert Settings(_env_file=None, meal_analysis_session_ttl_minutes=1).meal_analysis_session_ttl_minutes == 1
    assert Settings(_env_file=None, meal_analysis_session_ttl_minutes=1440).meal_analysis_session_ttl_minutes == 1440


def _composite_state() -> MealAnalysisSessionState:
    ingredient_nutrition = {
        "calories": "100.000", "protein_g": "10.000", "carbohydrates_g": "5.000",
        "fat_g": "3.000", "fiber_g": "1.000",
    }
    composite = CompositeProvenanceSnapshot(
        dish_name="Pork sinigang",
        dish_weight_grams=Decimal("275.000"),
        ingredients=[
            CompositeIngredientSnapshot(
                ingredient_name="Cooked pork", raw_estimated_proportion=Decimal("0.5"),
                normalized_proportion=Decimal("0.5"), estimated_weight_grams=Decimal("137.500"),
                nutrition_source="USDA", source_reference_id="fdcId:111", reference_name="Pork, cooked",
                nutrition=ingredient_nutrition,
            ),
            CompositeIngredientSnapshot(
                ingredient_name="Sinigang vegetables", raw_estimated_proportion=Decimal("0.5"),
                normalized_proportion=Decimal("0.5"), estimated_weight_grams=Decimal("137.500"),
                nutrition_source="local_database", source_reference_id="food:12", reference_name="Mixed vegetables",
                nutrition=ingredient_nutrition,
            ),
        ],
    )
    return MealAnalysisSessionState(
        measured_weight_grams=Decimal("275.000"),
        components=[
            MealAnalysisSessionComponent(
                recognized_name="Pork sinigang", raw_estimated_proportion=Decimal("1"),
                normalized_proportion=Decimal("1"), estimated_weight_grams=Decimal("275.000"),
                resolution_status=ComponentResolutionStatus.RESOLVED,
                nutrition_source="ai_recipe_estimate",
                nutrition={
                    "calories": "275.000", "protein_g": "27.500", "carbohydrates_g": "13.750",
                    "fat_g": "8.250", "fiber_g": "2.750",
                },
                composite_provenance_snapshot=composite,
            )
        ],
    )


def test_composite_snapshot_preserves_decimal_weights_and_requires_exact_reconciliation() -> None:
    state = _composite_state()
    snapshot = state.components[0].composite_provenance_snapshot
    assert snapshot is not None
    assert sum((item.estimated_weight_grams for item in snapshot.ingredients), Decimal("0")) == Decimal("275.000")
    assert state.model_dump(mode="json")["components"][0]["composite_provenance_snapshot"]["dish_weight_grams"] == "275.000"

    with pytest.raises(ValueError, match="must equal the dish weight"):
        CompositeProvenanceSnapshot(
            dish_name="Invalid", dish_weight_grams=Decimal("10.000"),
            ingredients=[
                CompositeIngredientSnapshot(
                    ingredient_name="Only ingredient", raw_estimated_proportion=Decimal("1"),
                    normalized_proportion=Decimal("1"), estimated_weight_grams=Decimal("9.999"),
                    nutrition_source="USDA", source_reference_id="fdcId:1", reference_name="Reference",
                    nutrition={"calories": "1.000", "protein_g": "1.000", "carbohydrates_g": "1.000", "fat_g": "1.000", "fiber_g": "1.000"},
                )
            ],
        )


def test_session_backed_composite_meal_persists_one_foodless_snapshot(database_session: Session) -> None:
    user = _user(database_session, "composite-persistence@example.com")
    session_service = _service(database_session)
    analysis = session_service.create_session(user.id, _composite_state(), "calculated")
    meal = MealService(
        NutritionService(FoodRepository(database_session)), MealRepository(database_session)
    ).create_meal_from_analysis_session(analysis.id, user.id)
    database_session.refresh(meal)

    assert meal.measured_weight_grams == Decimal("275.000")
    assert len(meal.items) == 1
    item = meal.items[0]
    assert item.food_id is None
    assert item.food_name_snapshot == "Pork sinigang"
    assert item.weight_grams == Decimal("275.000")
    assert item.nutrition_source_type == "ai_recipe_estimate"
    assert item.nutrition_is_estimated is True
    assert item.calculated_calories == Decimal("275.000")
    assert item.composite_provenance_snapshot is not None
    assert item.composite_provenance_snapshot["ingredients"][0]["source_reference_id"] == "fdcId:111"
    assert sum((Decimal(entry["estimated_weight_grams"]) for entry in item.composite_provenance_snapshot["ingredients"]), Decimal("0")) == item.weight_grams
    assert analysis.consumed_at is not None

    analysis.state = _composite_state().model_dump(mode="json")
    analysis.state["components"][0]["composite_provenance_snapshot"]["ingredients"][0]["reference_name"] = "Changed upstream reference"
    database_session.flush()
    database_session.refresh(item)
    assert item.composite_provenance_snapshot["ingredients"][0]["reference_name"] == "Pork, cooked"


def test_session_backed_post_persists_one_composite_meal_item(
    database_session: Session, client: TestClient, auth_headers: dict[str, str]
) -> None:
    user = database_session.scalar(select(User).where(User.email == "user@example.com"))
    assert user is not None
    analysis = _service(database_session).create_session(user.id, _composite_state(), "calculated")

    response = client.post(
        "/api/meals", json={"analysis_session_id": analysis.id}, headers=auth_headers
    )

    assert response.status_code == 201
    payload = response.json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["food"] == {"id": None, "name": "Pork sinigang"}
    assert payload["items"][0]["nutrition_source"]["category"] == "ai_recipe_estimate"
    assert payload["items"][0]["composite_estimation"] is True
    database_session.refresh(analysis)
    assert analysis.consumed_at is not None
