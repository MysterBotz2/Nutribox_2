from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.meal import Meal
from app.routers.ai import get_nutrition_coach_service
from app.services.nutrition_coach_provider import (
    NutritionCoachContext,
    NutritionCoachInvalidResponse,
    NutritionCoachProvider,
    NutritionCoachResult,
    NutritionCoachUnavailable,
)
from app.services.nutrition_coach_selector import get_nutrition_coach_provider
from app.services.nutrient_calculator import NutrientCalculator
from conftest import register_and_login


class CapturingCoachProvider(NutritionCoachProvider):
    def __init__(self) -> None:
        self.contexts: list[NutritionCoachContext] = []

    async def generate_guidance(self, context: NutritionCoachContext) -> NutritionCoachResult:
        self.contexts.append(context)
        return NutritionCoachResult(
            message="Captured simulated response.", highlights=("Captured context.",), provider="capture"
        )


def add_stored_meal(session: Session, user_id: int, calories: str = "100.000") -> None:
    session.add(
        Meal(
            user_id=user_id,
            recorded_at=datetime(2026, 8, 10, 12, tzinfo=timezone.utc),
            total_calories=Decimal(calories),
            total_protein_g=Decimal("20.000"),
            total_carbohydrates_g=Decimal("30.000"),
            total_fat_g=Decimal("4.000"),
            total_fiber_g=Decimal("5.000"),
        )
    )
    session.flush()


def target_payload() -> dict[str, object]:
    return {"calories": "200.000", "source_type": "manual"}


def test_coach_requires_authentication(client: TestClient) -> None:
    assert client.post("/api/ai/coach", json={}).status_code == 401


def test_mock_coach_is_deterministic_and_handles_missing_data(
    client: TestClient, jwt_configuration: None, monkeypatch
) -> None:
    import app.services.progress_service as progress_service

    monkeypatch.setattr(
        progress_service,
        "current_utc_datetime",
        lambda: datetime(2026, 8, 10, 12, tzinfo=timezone.utc),
    )
    _, headers = register_and_login(client)
    first = client.post("/api/ai/coach", json={}, headers=headers)
    second = client.post("/api/ai/coach", json={}, headers=headers)

    assert first.status_code == second.status_code == 200
    assert first.json()["provider"] == "mock"
    assert first.json()["message"] == second.json()["message"]
    assert first.json()["highlights"] == second.json()["highlights"]
    assert "no recorded meal data" in first.json()["highlights"][0]
    assert "No configured nutrition targets" in first.json()["highlights"][1]


def test_coach_assembles_only_current_users_trusted_context(
    database_session: Session, client: TestClient, jwt_configuration: None, monkeypatch
) -> None:
    import app.services.progress_service as progress_service

    monkeypatch.setattr(
        progress_service,
        "current_utc_datetime",
        lambda: datetime(2026, 8, 10, 12, tzinfo=timezone.utc),
    )
    first, first_headers = register_and_login(client, "first@example.com")
    second, second_headers = register_and_login(client, "second@example.com")
    assert client.put(
        "/api/users/me/profile",
        json={"age": 30, "height_cm": "170.00", "weight_kg": "70.000", "activity_level": "lightly_active", "dietary_restrictions": ["vegetarian"], "allergies": ["peanut"]},
        headers=first_headers,
    ).status_code == 200
    assert client.put(
        "/api/users/me/profile",
        json={"activity_level": "very_active", "allergies": ["shellfish"]},
        headers=second_headers,
    ).status_code == 200
    assert client.put("/api/users/me/targets", json=target_payload(), headers=first_headers).status_code == 200
    assert client.put(
        "/api/users/me/targets",
        json={"calories": "999.000", "source_type": "manual"},
        headers=second_headers,
    ).status_code == 200
    add_stored_meal(database_session, first["id"], "150.000")
    add_stored_meal(database_session, second["id"], "999.000")
    provider = CapturingCoachProvider()
    app.dependency_overrides[get_nutrition_coach_provider] = lambda: provider
    try:
        response = client.post(
            "/api/ai/coach?timezone=UTC", json={"question": "How am I doing today?"}, headers=first_headers
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["provider"] == "capture"
    context = provider.contexts[0]
    assert context.profile is not None
    assert context.profile.activity_level == "lightly_active"
    assert context.profile.dietary_restrictions == ("vegetarian",)
    assert context.profile.allergies == ("peanut",)
    assert context.target is not None and context.target.values.calories == Decimal("200.000")
    assert context.today.meal_count == 1
    assert context.today.totals.calories == Decimal("150.000")
    assert context.target_comparison.remaining is not None
    assert context.target_comparison.remaining.calories == Decimal("50.000")
    assert context.weekly.meal_count == 1
    assert context.question == "How am I doing today?"
    assert not any(hasattr(context, field) for field in ("user_id", "email", "password", "token", "session"))
    assert not any(hasattr(context.profile, field) for field in ("age", "height_cm", "weight_kg"))


def test_coach_context_never_uses_calculator_or_receives_a_database_session(
    database_session: Session, client: TestClient, jwt_configuration: None, monkeypatch
) -> None:
    import app.services.progress_service as progress_service

    monkeypatch.setattr(
        progress_service,
        "current_utc_datetime",
        lambda: datetime(2026, 8, 10, 12, tzinfo=timezone.utc),
    )
    user, headers = register_and_login(client)
    add_stored_meal(database_session, user["id"])
    monkeypatch.setattr(
        NutrientCalculator,
        "calculate",
        lambda *_: (_ for _ in ()).throw(AssertionError("Coach must not calculate nutrients.")),
    )
    provider = CapturingCoachProvider()
    app.dependency_overrides[get_nutrition_coach_provider] = lambda: provider
    try:
        response = client.post("/api/ai/coach", json={}, headers=headers)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert not hasattr(provider.contexts[0], "database_session")


def test_coach_validates_timezone_question_and_authoritative_client_fields(
    client: TestClient, jwt_configuration: None
) -> None:
    _, headers = register_and_login(client)
    assert client.post(
        "/api/ai/coach?timezone=Not/AZone", json={}, headers=headers
    ).status_code == 422
    assert client.post(
        "/api/ai/coach", json={"question": "x" * 501}, headers=headers
    ).status_code == 422
    assert client.post(
        "/api/ai/coach", json={"consumed_calories": "999"}, headers=headers
    ).status_code == 422


def test_mock_coach_safely_redirects_medical_questions(
    client: TestClient, jwt_configuration: None
) -> None:
    _, headers = register_and_login(client)
    response = client.post(
        "/api/ai/coach", json={"question": "Can you diagnose diabetes?"}, headers=headers
    )

    assert response.status_code == 200
    assert "cannot diagnose" in response.json()["message"]
    assert "qualified healthcare professional" in response.json()["message"]


def test_unknown_coach_provider_fails_safely(client: TestClient, jwt_configuration: None, monkeypatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "nutrition_coach_provider", "unsupported")
    _, headers = register_and_login(client)
    response = client.post("/api/ai/coach", json={}, headers=headers)

    assert response.status_code == 503
    assert response.json() == {"detail": "Nutrition coach provider is not configured."}


def test_coach_normalizes_provider_unavailable_and_invalid_response(
    client: TestClient, jwt_configuration: None
) -> None:
    _, headers = register_and_login(client)

    class UnavailableProvider(CapturingCoachProvider):
        async def generate_guidance(self, context):
            raise NutritionCoachUnavailable("Nutrition coach provider is unavailable.")

    app.dependency_overrides[get_nutrition_coach_provider] = lambda: UnavailableProvider()
    try:
        unavailable = client.post("/api/ai/coach", json={}, headers=headers)
    finally:
        app.dependency_overrides.clear()
    assert unavailable.status_code == 503

    class InvalidProvider(CapturingCoachProvider):
        async def generate_guidance(self, context):
            raise NutritionCoachInvalidResponse("Nutrition coach provider returned an invalid response.")

    _, headers = register_and_login(client, f"invalid-provider-{uuid4().hex}@example.com")
    app.dependency_overrides[get_nutrition_coach_provider] = lambda: InvalidProvider()
    try:
        invalid = client.post("/api/ai/coach", json={}, headers=headers)
    finally:
        app.dependency_overrides.clear()
    assert invalid.status_code == 502
