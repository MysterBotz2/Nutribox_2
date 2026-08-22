from logging.config import fileConfig
from pathlib import Path
import sys

from alembic import context
from sqlalchemy import engine_from_config, pool

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIRECTORY))

from app.core.config import settings  # noqa: E402
from app.database.base import Base  # noqa: E402
from app.models.food import Food  # noqa: F401, E402
from app.models.food_alias import FoodAlias  # noqa: F401, E402
from app.models.meal import Meal, MealItem  # noqa: F401, E402
from app.models.leftover_analysis import LeftoverAnalysis  # noqa: F401, E402
from app.models.nutrition_profile import NutritionProfile  # noqa: F401, E402
from app.models.nutrition_target import NutritionTarget  # noqa: F401, E402
from app.models.profile_consent import ProfileConsent  # noqa: F401, E402
from app.models.scheduled_meal import ScheduledMeal  # noqa: F401, E402
from app.models.sensitive_profile_context import SensitiveProfileContext  # noqa: F401, E402
from app.models.user import User  # noqa: F401, E402
from app.models.weight_entry import WeightEntry  # noqa: F401, E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

if not settings.database_url:
    raise RuntimeError("DATABASE_URL must be configured before running Alembic.")

config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without creating a database engine."""
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with a database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
