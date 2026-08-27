"""Validated, local CSV ingestion for canonical nutrition reference data."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.food import NUTRITION_SOURCE_TYPES, Food, clean_food_name, normalize_food_name
from app.models.food_alias import FoodAlias


REQUIRED_HEADERS = (
    "name",
    "category",
    "calories_per_100g",
    "protein_g_per_100g",
    "carbohydrates_g_per_100g",
    "fat_g_per_100g",
    "fiber_g_per_100g",
    "source_name",
    "source_type",
    "source_reference",
    "is_verified",
    "aliases",
)

_NUTRIENT_SPECS = {
    "calories_per_100g": (10, 2),
    "protein_g_per_100g": (8, 3),
    "carbohydrates_g_per_100g": (8, 3),
    "fat_g_per_100g": (8, 3),
    "fiber_g_per_100g": (8, 3),
    "saturated_fat_g_per_100g": (8, 3),
    "sugars_g_per_100g": (8, 3),
    "sodium_mg_per_100g": (10, 3),
    "cholesterol_mg_per_100g": (10, 3),
    "omega_3_g_per_100g": (8, 3),
    "omega_6_g_per_100g": (8, 3),
    "calcium_mg_per_100g": (10, 3),
    "potassium_mg_per_100g": (10, 3),
    "zinc_mg_per_100g": (10, 3),
    "iron_mg_per_100g": (10, 3),
    "magnesium_mg_per_100g": (10, 3),
    "phosphorus_mg_per_100g": (10, 3),
    "vitamin_b6_mg_per_100g": (10, 3),
    "niacin_mg_per_100g": (10, 3),
    "vitamin_a_mcg_rae_per_100g": (10, 3),
    "vitamin_b12_mcg_per_100g": (10, 3),
    "vitamin_c_mg_per_100g": (10, 3),
    "vitamin_d_mcg_per_100g": (10, 3),
    "folate_mcg_dfe_per_100g": (10, 3),
}

MANDATORY_NUTRIENT_FIELDS = (
    "calories_per_100g",
    "protein_g_per_100g",
    "carbohydrates_g_per_100g",
    "fat_g_per_100g",
    "fiber_g_per_100g",
)


@dataclass(frozen=True)
class FoodImportIssue:
    row_number: int | None
    field: str | None
    message: str


@dataclass(frozen=True)
class FoodImportReport:
    rows_processed: int
    valid: int
    invalid: int
    planned_inserts: int
    planned_aliases: int
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    aliases_inserted: int = 0
    errors: tuple[FoodImportIssue, ...] = ()
    warnings: tuple[FoodImportIssue, ...] = ()


class FoodIngestionValidationError(ValueError):
    """Raised when a complete import plan contains invalid rows or conflicts."""

    def __init__(self, report: FoodImportReport) -> None:
        super().__init__("Food import validation failed.")
        self.report = report


class FoodIngestionExecutionError(RuntimeError):
    """Raised when a validated import cannot be persisted safely."""


@dataclass(frozen=True)
class _FoodRow:
    row_number: int
    name: str
    normalized_name: str
    category: str | None
    nutrients: dict[str, Decimal | None]
    source_name: str
    source_type: str
    source_reference: str
    is_verified: bool
    aliases: tuple[tuple[str, str], ...]


class FoodIngestionService:
    """Parse, validate, plan, and atomically persist curated local CSV files."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def import_csv(self, file_path: str | Path, *, dry_run: bool = False) -> FoodImportReport:
        path = Path(file_path)
        if not path.is_file():
            report = FoodImportReport(0, 0, 0, 0, 0, errors=(
                FoodImportIssue(None, None, "CSV file was not found."),
            ))
            raise FoodIngestionValidationError(report)

        rows, errors, rows_processed = self._parse_csv(path)
        errors.extend(self._validate_conflicts(rows))
        invalid_rows = {issue.row_number for issue in errors if issue.row_number is not None}
        report = FoodImportReport(
            rows_processed=rows_processed,
            valid=len(rows) - len({row.row_number for row in rows if row.row_number in invalid_rows}),
            invalid=len(invalid_rows),
            planned_inserts=len(rows) if not errors else 0,
            planned_aliases=sum(len(row.aliases) for row in rows) if not errors else 0,
            errors=tuple(errors),
        )
        if errors:
            raise FoodIngestionValidationError(report)
        if dry_run:
            return report

        try:
            transaction = self._session.begin_nested() if self._session.in_transaction() else self._session.begin()
            with transaction:
                for row in rows:
                    food = Food(
                        name=row.name,
                        category=row.category,
                        calories_per_100g=row.nutrients["calories_per_100g"],
                        protein_g_per_100g=row.nutrients["protein_g_per_100g"],
                        carbohydrates_g_per_100g=row.nutrients["carbohydrates_g_per_100g"],
                        fat_g_per_100g=row.nutrients["fat_g_per_100g"],
                        fiber_g_per_100g=row.nutrients["fiber_g_per_100g"],
                        saturated_fat_g_per_100g=row.nutrients["saturated_fat_g_per_100g"],
                        sugars_g_per_100g=row.nutrients["sugars_g_per_100g"],
                        sodium_mg_per_100g=row.nutrients["sodium_mg_per_100g"],
                        cholesterol_mg_per_100g=row.nutrients["cholesterol_mg_per_100g"],
                        omega_3_g_per_100g=row.nutrients["omega_3_g_per_100g"],
                        omega_6_g_per_100g=row.nutrients["omega_6_g_per_100g"],
                        calcium_mg_per_100g=row.nutrients["calcium_mg_per_100g"],
                        potassium_mg_per_100g=row.nutrients["potassium_mg_per_100g"],
                        zinc_mg_per_100g=row.nutrients["zinc_mg_per_100g"],
                        iron_mg_per_100g=row.nutrients["iron_mg_per_100g"],
                        magnesium_mg_per_100g=row.nutrients["magnesium_mg_per_100g"],
                        phosphorus_mg_per_100g=row.nutrients["phosphorus_mg_per_100g"],
                        vitamin_b6_mg_per_100g=row.nutrients["vitamin_b6_mg_per_100g"],
                        niacin_mg_per_100g=row.nutrients["niacin_mg_per_100g"],
                        vitamin_a_mcg_rae_per_100g=row.nutrients["vitamin_a_mcg_rae_per_100g"],
                        vitamin_b12_mcg_per_100g=row.nutrients["vitamin_b12_mcg_per_100g"],
                        vitamin_c_mg_per_100g=row.nutrients["vitamin_c_mg_per_100g"],
                        vitamin_d_mcg_per_100g=row.nutrients["vitamin_d_mcg_per_100g"],
                        folate_mcg_dfe_per_100g=row.nutrients["folate_mcg_dfe_per_100g"],
                        source_name=row.source_name,
                        source_type=row.source_type,
                        source_reference=row.source_reference,
                        is_verified=row.is_verified,
                    )
                    self._session.add(food)
                    self._session.flush()
                    self._session.add_all(
                        FoodAlias(food_id=food.id, alias=alias)
                        for alias, _ in row.aliases
                    )
                self._session.flush()
        except SQLAlchemyError as exception:
            raise FoodIngestionExecutionError("Food import could not be saved safely.") from exception

        return FoodImportReport(
            rows_processed=report.rows_processed,
            valid=report.valid,
            invalid=0,
            planned_inserts=report.planned_inserts,
            planned_aliases=report.planned_aliases,
            inserted=len(rows),
            aliases_inserted=sum(len(row.aliases) for row in rows),
        )

    def _parse_csv(self, path: Path) -> tuple[list[_FoodRow], list[FoodImportIssue], int]:
        parsed_rows: list[_FoodRow] = []
        errors: list[FoodImportIssue] = []
        rows_processed = 0
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as file:
                reader = csv.DictReader(file)
                if reader.fieldnames is None:
                    return [], [FoodImportIssue(None, None, "CSV file must include a header row.")], 0
                missing_headers = [header for header in REQUIRED_HEADERS if header not in reader.fieldnames]
                if missing_headers:
                    return [], [FoodImportIssue(None, None, f"Missing required columns: {', '.join(missing_headers)}.")], 0
                for row_number, values in enumerate(reader, start=2):
                    rows_processed += 1
                    row, row_errors = self._parse_row(row_number, values)
                    errors.extend(row_errors)
                    if row is not None:
                        parsed_rows.append(row)
        except UnicodeDecodeError:
            errors.append(FoodImportIssue(None, None, "CSV must be UTF-8 encoded."))
        except csv.Error:
            errors.append(FoodImportIssue(None, None, "CSV file could not be parsed."))
        return parsed_rows, errors, rows_processed

    def _parse_row(
        self, row_number: int, values: dict[str, str | None]
    ) -> tuple[_FoodRow | None, list[FoodImportIssue]]:
        errors: list[FoodImportIssue] = []

        def required(field: str, maximum_length: int | None = None) -> str | None:
            value = (values.get(field) or "").strip()
            if not value:
                errors.append(FoodImportIssue(row_number, field, "Value is required."))
                return None
            if maximum_length is not None and len(value) > maximum_length:
                errors.append(FoodImportIssue(row_number, field, f"Value must be at most {maximum_length} characters."))
                return None
            return value

        raw_name = required("name", 160)
        name = None
        normalized_name = None
        if raw_name is not None:
            try:
                name = clean_food_name(raw_name)
                normalized_name = normalize_food_name(name)
            except ValueError as exception:
                errors.append(FoodImportIssue(row_number, "name", str(exception)))

        category_raw = (values.get("category") or "").strip()
        category = category_raw or None
        if category is not None and len(category) > 80:
            errors.append(FoodImportIssue(row_number, "category", "Value must be at most 80 characters."))
        nutrients = {
            field: self._parse_decimal(
                row_number,
                field,
                values.get(field),
                precision,
                scale,
                errors,
                required=field in MANDATORY_NUTRIENT_FIELDS,
            )
            for field, (precision, scale) in _NUTRIENT_SPECS.items()
        }
        source_name = required("source_name", 160)
        source_type = required("source_type", 32)
        if source_type is not None and source_type not in NUTRITION_SOURCE_TYPES:
            errors.append(FoodImportIssue(row_number, "source_type", "Unsupported source category."))
        source_reference = required("source_reference")
        is_verified = self._parse_boolean(row_number, values.get("is_verified"), errors)
        if source_type == "AI_estimate" and is_verified:
            errors.append(FoodImportIssue(row_number, "is_verified", "AI_estimate records must not be marked verified."))
        aliases = self._parse_aliases(row_number, values.get("aliases"), errors)

        if errors or name is None or normalized_name is None or source_name is None or source_type is None or source_reference is None or is_verified is None:
            return None, errors
        return _FoodRow(row_number, name, normalized_name, category, nutrients, source_name, source_type, source_reference, is_verified, aliases), errors

    @staticmethod
    def _parse_decimal(
        row_number: int, field: str, value: str | None, precision: int, scale: int,
        errors: list[FoodImportIssue],
        *,
        required: bool,
    ) -> Decimal | None:
        raw_value = (value or "").strip()
        if not raw_value:
            if required:
                errors.append(FoodImportIssue(row_number, field, "Value is required."))
            return None
        try:
            decimal_value = Decimal(raw_value)
        except (InvalidOperation, ValueError):
            errors.append(FoodImportIssue(row_number, field, "Value must be a valid Decimal."))
            return None
        if not decimal_value.is_finite():
            errors.append(FoodImportIssue(row_number, field, "Value must be finite."))
        elif decimal_value < 0:
            errors.append(FoodImportIssue(row_number, field, "Value must not be negative."))
        else:
            sign, digits, exponent = decimal_value.as_tuple()
            decimal_places = max(0, -exponent)
            integer_digits = max(0, len(digits) + exponent)
            if decimal_places > scale or integer_digits > precision - scale:
                errors.append(FoodImportIssue(row_number, field, f"Value exceeds NUMERIC({precision}, {scale}) precision."))
        return decimal_value

    @staticmethod
    def _parse_boolean(row_number: int, value: str | None, errors: list[FoodImportIssue]) -> bool | None:
        normalized = (value or "").strip().casefold()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
        errors.append(FoodImportIssue(row_number, "is_verified", "Value must be explicitly true or false."))
        return None

    @staticmethod
    def _parse_aliases(row_number: int, value: str | None, errors: list[FoodImportIssue]) -> tuple[tuple[str, str], ...]:
        aliases: list[tuple[str, str]] = []
        for raw_alias in (value or "").split("|"):
            if not raw_alias.strip():
                continue
            try:
                alias = clean_food_name(raw_alias)
                if len(alias) > 160:
                    raise ValueError("Alias must be at most 160 characters.")
                aliases.append((alias, normalize_food_name(alias)))
            except ValueError as exception:
                errors.append(FoodImportIssue(row_number, "aliases", str(exception)))
        return tuple(aliases)

    def _validate_conflicts(self, rows: list[_FoodRow]) -> list[FoodImportIssue]:
        errors: list[FoodImportIssue] = []
        canonical_rows: dict[str, int] = {}
        alias_rows: dict[str, int] = {}
        for row in rows:
            self._record_duplicate(canonical_rows, row.normalized_name, row.row_number, "name", errors)
            for _, normalized_alias in row.aliases:
                if normalized_alias == row.normalized_name:
                    errors.append(FoodImportIssue(row.row_number, "aliases", "Alias duplicates its canonical name."))
                self._record_duplicate(alias_rows, normalized_alias, row.row_number, "aliases", errors)
                if normalized_alias in canonical_rows:
                    errors.append(FoodImportIssue(row.row_number, "aliases", "Alias conflicts with a canonical name in this file."))
        for normalized_name, row_number in canonical_rows.items():
            if normalized_name in alias_rows:
                errors.append(FoodImportIssue(row_number, "name", "Canonical name conflicts with an alias in this file."))

        names = set(canonical_rows)
        aliases = set(alias_rows)
        if names or aliases:
            existing_names = set(self._session.scalars(select(Food.normalized_name).where(Food.normalized_name.in_(names | aliases))))
            existing_aliases = set(self._session.scalars(select(FoodAlias.normalized_alias).where(FoodAlias.normalized_alias.in_(names | aliases))))
            for normalized_name, row_number in canonical_rows.items():
                if normalized_name in existing_names or normalized_name in existing_aliases:
                    errors.append(FoodImportIssue(row_number, "name", "Canonical name already resolves to an existing food."))
            for normalized_alias, row_number in alias_rows.items():
                if normalized_alias in existing_names or normalized_alias in existing_aliases:
                    errors.append(FoodImportIssue(row_number, "aliases", "Alias already resolves to an existing food."))
        return errors

    @staticmethod
    def _record_duplicate(
        seen: dict[str, int], value: str, row_number: int, field: str, errors: list[FoodImportIssue]) -> None:
        prior_row = seen.get(value)
        if prior_row is not None:
            errors.append(FoodImportIssue(row_number, field, f"Duplicate normalized value; first appears on row {prior_row}."))
            return
        seen[value] = row_number
