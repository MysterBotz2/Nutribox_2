from datetime import datetime, timezone

from sqlalchemy import func, select

from app.cli.seed_demo_user import DEMO_EMAIL, seed_demo_user
from app.models.meal import Meal
from app.models.user import User
from app.repositories.meal_repository import MealRepository
from app.repositories.nutrition_target_repository import NutritionTargetRepository
from app.repositories.scheduled_meal_repository import ScheduledMealRepository
from app.repositories.weight_entry_repository import WeightEntryRepository
from app.services.weekly_diagnostics_service import WeeklyDiagnosticsService
from tests.conftest import register_and_login


def test_demo_seed_is_idempotent_reset_is_scoped_and_diagnostics_can_read_it(database_session, client):
    _, _ = register_and_login(client, "real-user@example.com")
    fixed_now = datetime(2026, 8, 20, 12, tzinfo=timezone.utc)
    demo = seed_demo_user(database_session, "test-only-password", now=fixed_now)
    database_session.flush()
    first_meal_count = database_session.scalar(select(func.count(Meal.id)).where(Meal.user_id == demo.id))
    assert demo.email == DEMO_EMAIL
    assert first_meal_count >= 16
    assert database_session.scalar(select(User).where(User.email == "real-user@example.com")) is not None

    same_demo = seed_demo_user(database_session, "test-only-password", now=fixed_now)
    assert same_demo.id == demo.id
    assert database_session.scalar(select(func.count(Meal.id)).where(Meal.user_id == demo.id)) == first_meal_count

    reset_demo = seed_demo_user(database_session, "test-only-password", reset=True, now=fixed_now)
    assert reset_demo.email == DEMO_EMAIL
    assert database_session.scalar(select(User).where(User.email == "real-user@example.com")) is not None
    diagnostics = WeeklyDiagnosticsService(MealRepository(database_session), ScheduledMealRepository(database_session), WeightEntryRepository(database_session), NutritionTargetRepository(database_session)).weekly(reset_demo.id, fixed_now.date().replace(day=17))
    assert diagnostics.meals_logged > 0
    assert diagnostics.weight.latest_weight_kg is not None
