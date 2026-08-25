from app.services.composite_dish_estimator import (
    CompositeDishEstimate,
    CompositeDishEstimator,
    CompositeDishEstimatorError,
)


class MockCompositeDishEstimator(CompositeDishEstimator):
    """Deterministic test/development estimator; no implicit recipe guesses."""

    def __init__(self, estimates: dict[str, CompositeDishEstimate] | None = None) -> None:
        self._estimates = {name.casefold(): estimate for name, estimate in (estimates or {}).items()}

    def estimate_composition(self, *, dish_name: str, dish_weight_grams) -> CompositeDishEstimate:
        estimate = self._estimates.get(dish_name.casefold())
        if estimate is None:
            raise CompositeDishEstimatorError("Composite dish estimation provider is unavailable.", 503)
        return estimate
