from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.routers.ai import get_nutrition_coach_service
from app.services.nutrition_coach_provider import NutritionCoachProvider, NutritionCoachResult, NutritionCoachUnavailable
from app.services.nutrition_coach_service import NutritionCoachService
from conftest import register_and_login


class CaptureProvider(NutritionCoachProvider):
    def __init__(self) -> None:
        self.contexts = []

    async def generate_guidance(self, context):
        return NutritionCoachResult("coach", (), "capture")

    async def generate_chat_reply(self, context):
        self.contexts.append(context)
        return NutritionCoachResult("assistant reply", (), "capture")


def _override(client: TestClient, database_session: Session, provider: NutritionCoachProvider) -> None:
    from app.repositories.meal_repository import MealRepository
    from app.repositories.nutrition_profile_repository import NutritionProfileRepository
    from app.repositories.nutrition_target_repository import NutritionTargetRepository
    from app.services.nutrition_target_comparison_service import NutritionTargetComparisonService
    from app.services.nutrition_target_service import NutritionTargetService
    from app.services.progress_service import ProgressService
    target_repository = NutritionTargetRepository(database_session)
    progress = ProgressService(MealRepository(database_session))
    client.app.dependency_overrides[get_nutrition_coach_service] = lambda: NutritionCoachService(provider, NutritionProfileRepository(database_session), NutritionTargetService(target_repository), progress, NutritionTargetComparisonService(progress, target_repository))


def test_chat_requires_authentication(client: TestClient) -> None:
    assert client.post("/api/ai/chat", json={"message": "Hello"}).status_code == 401


def test_chat_persists_owner_history_and_bounds_context(client: TestClient, database_session: Session, jwt_configuration: None) -> None:
    provider = CaptureProvider(); _override(client, database_session, provider)
    _, first = register_and_login(client, "chat-one@example.com")
    _, second = register_and_login(client, "chat-two@example.com")
    created = client.post("/api/ai/chat", json={"message": "What did I eat today?"}, headers=first)
    assert created.status_code == 201
    conversation_id = created.json()["conversation_id"]
    follow_up = client.post("/api/ai/chat", json={"conversation_id": conversation_id, "message": "How about protein?"}, headers=first)
    assert follow_up.status_code == 201
    history = client.get(f"/api/ai/conversations/{conversation_id}", headers=first)
    assert [message["role"] for message in history.json()["messages"]] == ["user", "assistant", "user", "assistant"]
    assert client.get(f"/api/ai/conversations/{conversation_id}", headers=second).status_code == 404
    assert provider.contexts[1].conversation_history[0].content == "What did I eat today?"
    assert provider.contexts[0].today.meal_count == 0
    assert provider.contexts[0].target is None


def test_chat_validation_and_provider_failure_are_safe(client: TestClient, database_session: Session, auth_headers: dict[str, str]) -> None:
    provider = CaptureProvider(); _override(client, database_session, provider)
    assert client.post("/api/ai/chat", json={"message": " "}, headers=auth_headers).status_code == 422
    assert client.post("/api/ai/chat", json={"message": "x" * 1001}, headers=auth_headers).status_code == 422

    class DownProvider(CaptureProvider):
        async def generate_chat_reply(self, context):
            raise NutritionCoachUnavailable("Nutrition coach provider is unavailable.")
    _override(client, database_session, DownProvider())
    response = client.post("/api/ai/chat", json={"message": "Hello"}, headers=auth_headers)
    assert response.status_code == 503
    assert response.json() == {"detail": "Nutrition coach provider is unavailable."}
