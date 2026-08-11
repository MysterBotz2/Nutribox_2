from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.food import Food
from app.models.food_alias import FoodAlias


class FoodAliasRepository:
    """Database operations for exact alternate food names."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_food_by_normalized_alias(self, normalized_alias: str) -> Food | None:
        statement = (
            select(Food)
            .join(FoodAlias, FoodAlias.food_id == Food.id)
            .where(FoodAlias.normalized_alias == normalized_alias)
        )
        return self._session.scalar(statement)
