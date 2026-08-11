from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.food import clean_food_name, normalize_food_name


class FoodAlias(Base):
    """An exact alternate name that resolves to one canonical Food record."""

    __tablename__ = "food_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    food_id: Mapped[int] = mapped_column(
        ForeignKey("foods.id", ondelete="CASCADE"), nullable=False, index=True
    )
    alias: Mapped[str] = mapped_column(String(160), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    food: Mapped["Food"] = relationship(back_populates="aliases")


def set_normalized_food_alias(_, __, food_alias: FoodAlias) -> None:
    """Keep an alias lookup key aligned with its display form."""
    food_alias.alias = clean_food_name(food_alias.alias)
    food_alias.normalized_alias = normalize_food_name(food_alias.alias)


from sqlalchemy import event  # noqa: E402  (keeps model declarations together)


event.listen(FoodAlias, "before_insert", set_normalized_food_alias)
event.listen(FoodAlias, "before_update", set_normalized_food_alias)
