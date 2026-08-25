from dataclasses import dataclass
import logging
import re

from app.models.food import Food, normalize_food_name
from app.repositories.food_repository import FoodRepository
from app.services.usda_food_data_client import UsdaFoodDataClient, UsdaFoodDataError, UsdaSearchFood


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UsdaResolution:
    food: Food | None = None
    candidates: tuple[UsdaSearchFood, ...] = ()
    candidate_names: tuple[str, ...] = ()


class UsdaFoodReferenceService:
    """Resolve a local miss through USDA and cache a selected reference locally."""

    _REQUIRED = ("calories", "protein_g", "carbohydrates_g", "fat_g", "fiber_g")
    _RESULT_LIMIT = 5

    # Deliberately small, explainable relevance vocabulary. These terms guide
    # candidate presentation only; they never alter USDA nutrient values.
    _COMPOSITE_TERMS = frozenset({"sandwich", "burger", "bun", "wrap", "burrito", "taco", "pizza", "salad", "soup", "casserole", "stew"})
    # These are composite dishes, but remain part of the food identity.  A
    # query for beef stew must not devolve into a query for any beef cut.
    # A direct reference for a named prepared dish must retain this identity.
    # This intentionally prevents generic meat/cut token overlap from becoming
    # a false direct-reference path.
    _DISH_IDENTITY_TERMS = frozenset({
        "stew", "soup", "curry", "sinigang", "adobo", "caldereta", "tinola",
        "pinakbet", "laing", "pancit",
    })
    _CONDIMENT_IDENTITY_TERMS = frozenset({"sauce", "dressing"})
    _PREPARATION_TERMS = frozenset({"fried", "baked", "grilled", "roasted", "boiled", "steamed", "raw", "breaded", "coated"})
    _FRIED_COMPATIBLE_TERMS = frozenset({"fried", "breaded", "coated"})
    _COMMON_CUTS = frozenset({"wing", "breast", "thigh", "leg", "drumstick"})
    _OFFAL_TERMS = frozenset({"giblets", "liver", "heart", "gizzard"})
    _NON_IDENTITY_TERMS = (
        _PREPARATION_TERMS
        | _COMPOSITE_TERMS
        | _COMMON_CUTS
        | _OFFAL_TERMS
        | frozenset({"and", "with", "from", "on", "of", "or", "the", "a"})
    ) - _DISH_IDENTITY_TERMS

    _CORE_MATCH_SCORE = 6
    _EXACT_PHRASE_SCORE = 12
    _PREPARATION_MATCH_SCORE = 4
    _CUT_MATCH_SCORE = 8
    _DIFFERENT_CUT_PENALTY = 5
    _COMPOSITE_PENALTY = 7
    _OFFAL_PENALTY = 10
    _PREPARATION_CONFLICT_PENALTY = 4
    _MINIMUM_RELEVANCE_SCORE = 2

    def __init__(self, food_repository: FoodRepository, client: UsdaFoodDataClient | None) -> None:
        self._food_repository = food_repository
        self._client = client

    def resolve(self, recognized_name: str) -> UsdaResolution:
        if self._client is None:
            return UsdaResolution()
        try:
            candidates = self._client.search_food(recognized_name)
        except UsdaFoodDataError:
            return UsdaResolution()
        raw_candidates = candidates
        raw_candidate_count = len(raw_candidates)
        strict_candidates = self._rank_relevant_candidates(recognized_name, raw_candidates)
        fallback_candidates: list[UsdaSearchFood] = []
        candidates = strict_candidates
        if not candidates:
            fallback_candidates = self._rank_semantic_fallback_candidates(
                recognized_name, candidates=raw_candidates
            )
            candidates = fallback_candidates
        logger.info(
            "USDA relevance candidates raw=%d strict=%d fallback=%d final=%d",
            raw_candidate_count,
            len(strict_candidates),
            len(fallback_candidates),
            len(candidates),
        )
        logger.debug(
            "USDA relevance query=%r strict_candidates=%s fallback_candidates=%s final_candidates=%s",
            recognized_name,
            [candidate.description for candidate in strict_candidates],
            [candidate.description for candidate in fallback_candidates],
            [candidate.description for candidate in candidates],
        )
        # A single strict candidate is safe to load by its immutable FDC ID.
        # Duplicate raw rows with the same display name still represent an
        # ambiguous reference identity and must not be guessed.
        duplicate_identity_count = 0
        if len(candidates) == 1:
            selected_name = normalize_food_name(candidates[0].description)
            duplicate_identity_count = sum(
                1 for candidate in raw_candidates
                if normalize_food_name(candidate.description) == selected_name
                and self._is_semantically_eligible(recognized_name, candidate.description)
            )
        if len(candidates) != 1 or duplicate_identity_count != 1:
            logger.info(
                "USDA relevance outcome=%s",
                "requires_food_selection" if candidates else "nutrition_reference_not_found",
            )
            visible = tuple(candidates[:self._RESULT_LIMIT])
            return UsdaResolution(candidates=visible, candidate_names=tuple(candidate.description for candidate in visible))
        selected = candidates[0]
        return UsdaResolution(food=self.load_by_fdc_id(selected.fdc_id, selected.data_type))

    def load_by_fdc_id(self, fdc_id: int, data_type: str = "USDA") -> Food | None:
        """Load and cache exactly one stored USDA reference; never search by name."""
        if self._client is None:
            return None
        reference = f"fdcId:{fdc_id}"
        cached = self._food_repository.get_by_source_reference(reference)
        if cached is not None:
            return cached
        try:
            detail = self._client.get_food(fdc_id)
        except UsdaFoodDataError:
            return None
        if any(detail.nutrients[name] is None for name in self._REQUIRED):
            return None
        food = Food(
            name=detail.description,
            category=data_type,
            calories_per_100g=detail.nutrients["calories"],
            protein_g_per_100g=detail.nutrients["protein_g"],
            carbohydrates_g_per_100g=detail.nutrients["carbohydrates_g"],
            fat_g_per_100g=detail.nutrients["fat_g"],
            fiber_g_per_100g=detail.nutrients["fiber_g"],
            saturated_fat_g_per_100g=detail.nutrients["saturated_fat_g"],
            sugars_g_per_100g=detail.nutrients["sugars_g"],
            sodium_mg_per_100g=detail.nutrients["sodium_mg"],
            cholesterol_mg_per_100g=detail.nutrients["cholesterol_mg"],
            calcium_mg_per_100g=detail.nutrients["calcium_mg"],
            potassium_mg_per_100g=detail.nutrients["potassium_mg"],
            zinc_mg_per_100g=detail.nutrients["zinc_mg"],
            iron_mg_per_100g=detail.nutrients["iron_mg"],
            magnesium_mg_per_100g=detail.nutrients["magnesium_mg"],
            vitamin_c_mg_per_100g=detail.nutrients["vitamin_c_mg"],
            vitamin_d_mcg_per_100g=detail.nutrients["vitamin_d_mcg"],
            vitamin_b12_mcg_per_100g=detail.nutrients["vitamin_b12_mcg"],
            folate_mcg_dfe_per_100g=detail.nutrients["folate_mcg_dfe"],
            source_name="USDA FoodData Central",
            source_type="USDA",
            source_reference=reference,
            is_verified=False,
        )
        self._food_repository.add(food)
        self._food_repository.flush()
        return food

    @classmethod
    def _rank_relevant_candidates(
        cls, recognized_name: str, candidates: list[UsdaSearchFood]
    ) -> list[UsdaSearchFood]:
        """Score all USDA candidates, retaining original USDA order for ties."""
        return cls._rank_candidates(recognized_name, candidates, minimum_score=cls._MINIMUM_RELEVANCE_SCORE)

    @classmethod
    def _rank_semantic_fallback_candidates(
        cls, recognized_name: str, *, candidates: list[UsdaSearchFood]
    ) -> list[UsdaSearchFood]:
        """Retain only safe direct-food candidates if strict ranking has none."""
        eligible = [
            candidate
            for candidate in candidates
            if cls._is_semantically_eligible(recognized_name, candidate.description)
        ]
        return cls._rank_candidates(recognized_name, eligible, minimum_score=None)

    @classmethod
    def _rank_candidates(
        cls,
        recognized_name: str,
        candidates: list[UsdaSearchFood],
        *,
        minimum_score: int | None,
    ) -> list[UsdaSearchFood]:
        query_tokens = cls._matching_tokens(recognized_name)
        query_token_set = set(query_tokens)
        query_text = " ".join(query_tokens)
        query_composites = query_token_set & cls._COMPOSITE_TERMS
        query_preparation = query_token_set & cls._PREPARATION_TERMS
        query_cuts = query_token_set & cls._COMMON_CUTS
        query_offal = query_token_set & cls._OFFAL_TERMS
        core_tokens = query_token_set - cls._NON_IDENTITY_TERMS

        ranked: list[tuple[int, int, UsdaSearchFood]] = []
        for original_index, candidate in enumerate(candidates):
            candidate_token_sequence = cls._matching_tokens(candidate.description)
            tokens = set(candidate_token_sequence)
            if not cls._is_query_identity_compatible(query_token_set, tokens, candidate_token_sequence):
                continue
            if not cls._is_semantically_eligible(recognized_name, candidate.description):
                continue
            score, reasons = cls._candidate_relevance(
                query_text=query_text,
                candidate_text=" ".join(candidate_token_sequence),
                query_composites=query_composites,
                query_preparation=query_preparation,
                query_cuts=query_cuts,
                query_offal=query_offal,
                core_tokens=core_tokens,
                candidate_tokens=tokens,
            )
            logger.debug(
                "USDA relevance candidate=%r tokens=%s score=%d reasons=%s",
                candidate.description,
                candidate_token_sequence,
                score,
                reasons,
            )
            if minimum_score is None or score >= minimum_score:
                ranked.append((score, original_index, candidate))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        deduplicated: list[UsdaSearchFood] = []
        seen: set[str] = set()
        for _, _, candidate in ranked:
            key = normalize_food_name(candidate.description)
            if key not in seen:
                seen.add(key)
                deduplicated.append(candidate)
        return deduplicated

    @staticmethod
    def _is_query_identity_compatible(query_tokens: set[str], candidate_tokens: set[str], candidate_sequence: tuple[str, ...]) -> bool:
        """Hard, query-aware exclusions for clearly different foods/dishes."""
        animal_terms = {"chicken", "beef", "pork", "fish"}
        if query_tokens & animal_terms and candidate_tokens & {"meatless", "vegan", "plant", "based", "imitation"}:
            return False
        if query_tokens == {"fried", "chicken"}:
            if "chicken" not in candidate_tokens or not (candidate_tokens & {"fried", "breaded", "coated"}):
                return False
            if candidate_tokens & {"rice", "sandwich", "burger", "frozen", "potatoes", "vegetable", "meal"}:
                return False
        if query_tokens == {"beef", "stew"}:
            if not {"beef", "stew"}.issubset(candidate_tokens):
                return False
            if "stew" in candidate_tokens and "meat" in candidate_tokens and "beef" in candidate_tokens and "stew meat" in " ".join(candidate_sequence):
                return False
        return True

    @classmethod
    def _is_semantically_eligible(cls, recognized_name: str, description: str) -> bool:
        """Apply hard safety guards without using a numeric score threshold."""
        query_tokens = set(cls._matching_tokens(recognized_name))
        candidate_tokens = set(cls._matching_tokens(description))
        core_tokens = query_tokens - cls._NON_IDENTITY_TERMS
        if core_tokens and not (core_tokens & candidate_tokens):
            return False
        dish_identity_tokens = core_tokens & cls._DISH_IDENTITY_TERMS
        if dish_identity_tokens and not dish_identity_tokens.issubset(candidate_tokens):
            return False
        condiment_identity_tokens = query_tokens & cls._CONDIMENT_IDENTITY_TERMS
        if condiment_identity_tokens and not condiment_identity_tokens.issubset(candidate_tokens):
            return False
        query_preparation = query_tokens & cls._PREPARATION_TERMS
        candidate_preparation = candidate_tokens & cls._PREPARATION_TERMS
        for preparation in query_preparation:
            compatible_terms = cls._FRIED_COMPATIBLE_TERMS if preparation == "fried" else {preparation}
            if not (candidate_preparation & compatible_terms):
                return False
        if not query_tokens & cls._COMPOSITE_TERMS and candidate_tokens & cls._COMPOSITE_TERMS:
            return False
        if not query_tokens & cls._OFFAL_TERMS and candidate_tokens & cls._OFFAL_TERMS:
            return False
        query_cuts = query_tokens & cls._COMMON_CUTS
        candidate_cuts = candidate_tokens & cls._COMMON_CUTS
        return not query_cuts or not candidate_cuts or bool(query_cuts & candidate_cuts)

    @classmethod
    def _candidate_score(
        cls,
        *,
        query_text: str,
        candidate_text: str,
        query_composites: set[str],
        query_preparation: set[str],
        query_cuts: set[str],
        query_offal: set[str],
        core_tokens: set[str],
        candidate_tokens: set[str],
    ) -> int:
        """Return the deterministic candidate score without diagnostics."""
        return cls._candidate_relevance(
            query_text=query_text,
            candidate_text=candidate_text,
            query_composites=query_composites,
            query_preparation=query_preparation,
            query_cuts=query_cuts,
            query_offal=query_offal,
            core_tokens=core_tokens,
            candidate_tokens=candidate_tokens,
        )[0]

    @classmethod
    def _candidate_relevance(
        cls,
        *,
        query_text: str,
        candidate_text: str,
        query_composites: set[str],
        query_preparation: set[str],
        query_cuts: set[str],
        query_offal: set[str],
        core_tokens: set[str],
        candidate_tokens: set[str],
    ) -> tuple[int, tuple[str, ...]]:
        core_overlap = core_tokens & candidate_tokens
        if core_tokens and not core_overlap:
            return 0, ("no_core_identity_overlap",)

        dish_identity_tokens = core_tokens & cls._DISH_IDENTITY_TERMS
        if dish_identity_tokens and not dish_identity_tokens.issubset(candidate_tokens):
            return 0, ("missing_dish_identity",)

        score = len(core_overlap) * cls._CORE_MATCH_SCORE
        reasons = [f"core_overlap={','.join(sorted(core_overlap))}"] if core_overlap else []
        if query_text and query_text == candidate_text:
            score += cls._EXACT_PHRASE_SCORE
            reasons.append("exact_normalized_phrase")

        candidate_preparation = candidate_tokens & cls._PREPARATION_TERMS
        for preparation in query_preparation:
            compatible_terms = cls._FRIED_COMPATIBLE_TERMS if preparation == "fried" else {preparation}
            if candidate_preparation & compatible_terms:
                score += cls._PREPARATION_MATCH_SCORE
                reasons.append(f"preparation_match={preparation}")
            elif candidate_preparation:
                score -= cls._PREPARATION_CONFLICT_PENALTY
                reasons.append(f"preparation_conflict={preparation}")

        candidate_cuts = candidate_tokens & cls._COMMON_CUTS
        if query_cuts:
            if candidate_cuts & query_cuts:
                score += cls._CUT_MATCH_SCORE
                reasons.append("cut_match")
            elif candidate_cuts:
                score -= cls._DIFFERENT_CUT_PENALTY
                reasons.append("different_cut_penalty")

        candidate_offal = candidate_tokens & cls._OFFAL_TERMS
        if not query_offal:
            offal_penalty = len(candidate_offal) * cls._OFFAL_PENALTY
            score -= offal_penalty
            if offal_penalty:
                reasons.append("offal_penalty")

        # A composite query can legitimately contain its supporting terms (for
        # example, a bun with a sandwich). A generic food query cannot.
        if not query_composites:
            composite_penalty = len((candidate_tokens & cls._COMPOSITE_TERMS) - query_composites) * cls._COMPOSITE_PENALTY
            score -= composite_penalty
            if composite_penalty:
                reasons.append("composite_penalty")
        return score, tuple(reasons)

    @staticmethod
    def _matching_tokens(value: str) -> tuple[str, ...]:
        return tuple(re.findall(r"[a-z0-9]+", value.casefold()))
