from datetime import timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.database.base import Base
from app.models.meal_analysis_session import MealAnalysisSession
from app.models.user import User
from app.repositories.meal_analysis_session_repository import MealAnalysisSessionRepository
from app.schemas.meal_analysis_session import (
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
