from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.cli.import_foods import main as import_foods_main
from app.models.food import Food
from app.models.food_alias import FoodAlias
from app.repositories.food_alias_repository import FoodAliasRepository
from app.repositories.food_repository import FoodRepository
from app.services.food_ingestion_service import FoodIngestionService, FoodIngestionValidationError
from app.services.food_recognition_provider import FoodRecognitionProvider, FoodRecognitionResult
from app.services.meal_analysis_service import MealAnalysisService
from app.services.nutrition_service import NutritionService


CSV_FIELDS = (
    "name", "category", "calories_per_100g", "protein_g_per_100g",
    "carbohydrates_g_per_100g", "fat_g_per_100g", "fiber_g_per_100g",
    "saturated_fat_g_per_100g", "sugars_g_per_100g", "sodium_mg_per_100g",
    "cholesterol_mg_per_100g", "omega_3_g_per_100g", "omega_6_g_per_100g",
    "calcium_mg_per_100g", "potassium_mg_per_100g", "zinc_mg_per_100g",
    "iron_mg_per_100g", "magnesium_mg_per_100g", "phosphorus_mg_per_100g",
    "vitamin_b6_mg_per_100g", "niacin_mg_per_100g", "vitamin_a_mcg_rae_per_100g",
    "vitamin_b12_mcg_per_100g", "vitamin_c_mg_per_100g", "vitamin_d_mcg_per_100g",
    "folate_mcg_dfe_per_100g", "source_name", "source_type", "source_reference",
    "is_verified", "aliases",
)
HEADERS = ",".join(CSV_FIELDS) + "\n"
DEFAULT_ROW = {
    "name": "Curated Test Food", "category": "Test", "calories_per_100g": "123.45",
    "protein_g_per_100g": "10.123", "carbohydrates_g_per_100g": "20.000",
    "fat_g_per_100g": "5.000", "fiber_g_per_100g": "3.000",
    "saturated_fat_g_per_100g": "1.000", "sugars_g_per_100g": "2.000",
    "sodium_mg_per_100g": "10.000", "cholesterol_mg_per_100g": "0.000",
    "omega_3_g_per_100g": "", "omega_6_g_per_100g": "", "calcium_mg_per_100g": "",
    "potassium_mg_per_100g": "", "zinc_mg_per_100g": "", "iron_mg_per_100g": "",
    "magnesium_mg_per_100g": "", "phosphorus_mg_per_100g": "",
    "vitamin_b6_mg_per_100g": "", "niacin_mg_per_100g": "", "vitamin_a_mcg_rae_per_100g": "",
    "vitamin_b12_mcg_per_100g": "", "vitamin_c_mg_per_100g": "",
    "vitamin_d_mcg_per_100g": "", "folate_mcg_dfe_per_100g": "",
    "source_name": "TEST_SOURCE", "source_type": "local_database",
    "source_reference": "TEST-001", "is_verified": "false",
    "aliases": "Test Alias|Other Alias",
}


def make_row(**overrides: str) -> str:
    values = DEFAULT_ROW | overrides
    return ",".join(values[field] for field in CSV_FIELDS) + "\n"


VALID_ROW = make_row()


def write_csv(tmp_path, rows: str, name: str = "foods.csv"):
    path = tmp_path / name
    path.write_text(HEADERS + rows, encoding="utf-8")
    return path


def food_count(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Food)) or 0


def test_valid_csv_dry_run_parses_decimals_and_writes_nothing(database_session: Session, tmp_path) -> None:
    report = FoodIngestionService(database_session).import_csv(write_csv(tmp_path, VALID_ROW), dry_run=True)

    assert report.rows_processed == 1
    assert report.planned_inserts == 1
    assert report.planned_aliases == 2
    assert report.inserted == 0
    assert food_count(database_session) == 0


@pytest.mark.parametrize(
    "row, expected",
    [
        (make_row(name="Bad", calories_per_100g="not-a-number"), "valid Decimal"),
        (make_row(name="Bad", calories_per_100g="-1"), "must not be negative"),
        (make_row(name=""), "Value is required"),
        (make_row(source_name=""), "Value is required"),
        (make_row(name="Bad", calories_per_100g="NaN"), "must be finite"),
    ],
)
def test_invalid_food_values_are_rejected(database_session: Session, tmp_path, row: str, expected: str) -> None:
    with pytest.raises(FoodIngestionValidationError) as exception:
        FoodIngestionService(database_session).import_csv(write_csv(tmp_path, row), dry_run=True)

    assert any(expected in issue.message for issue in exception.value.report.errors)
    assert food_count(database_session) == 0


def test_real_import_adds_food_and_normalized_aliases(database_session: Session, tmp_path) -> None:
    report = FoodIngestionService(database_session).import_csv(write_csv(tmp_path, VALID_ROW))

    food = database_session.scalar(select(Food))
    aliases = list(database_session.scalars(select(FoodAlias).order_by(FoodAlias.alias)))
    assert report.inserted == 1
    assert report.aliases_inserted == 2
    assert food is not None
    assert food.calories_per_100g == Decimal("123.45")
    assert food.saturated_fat_g_per_100g == Decimal("1.000")
    assert food.omega_3_g_per_100g is None
    assert food.cholesterol_mg_per_100g == Decimal("0.000")
    assert food.source_type == "local_database"
    assert [(alias.alias, alias.normalized_alias) for alias in aliases] == [
        ("Other Alias", "other alias"),
        ("Test Alias", "test alias"),
    ]


def test_invalid_file_rolls_back_all_rows(database_session: Session, tmp_path) -> None:
    rows = VALID_ROW + make_row(name="Broken", calories_per_100g="-1")
    with pytest.raises(FoodIngestionValidationError):
        FoodIngestionService(database_session).import_csv(write_csv(tmp_path, rows))

    assert food_count(database_session) == 0


def test_duplicate_canonical_and_alias_conflicts_are_rejected(database_session: Session, tmp_path) -> None:
    rows = (
        VALID_ROW
        + make_row(name="  curated   test food ", aliases="")
        + make_row(name="Other Food", aliases="Test Alias")
    )
    with pytest.raises(FoodIngestionValidationError) as exception:
        FoodIngestionService(database_session).import_csv(write_csv(tmp_path, rows), dry_run=True)

    assert any("Duplicate normalized" in issue.message for issue in exception.value.report.errors)
    assert any("Duplicate normalized" in issue.message for issue in exception.value.report.errors)


def test_duplicate_alias_in_one_row_is_rejected(database_session: Session, tmp_path) -> None:
    duplicate_alias_row = make_row(name="Food", aliases="Same Alias| same   alias ")
    with pytest.raises(FoodIngestionValidationError) as exception:
        FoodIngestionService(database_session).import_csv(write_csv(tmp_path, duplicate_alias_row), dry_run=True)

    assert any("Duplicate normalized" in issue.message for issue in exception.value.report.errors)


def test_existing_canonical_and_alias_conflicts_are_rejected(database_session: Session, tmp_path) -> None:
    FoodIngestionService(database_session).import_csv(write_csv(tmp_path, VALID_ROW))
    conflicting = make_row(name="New Food", aliases="Other Alias")
    with pytest.raises(FoodIngestionValidationError) as exception:
        FoodIngestionService(database_session).import_csv(write_csv(tmp_path, conflicting, "conflict.csv"), dry_run=True)

    assert any("already resolves" in issue.message for issue in exception.value.report.errors)


def test_exact_canonical_and_alias_resolution_and_search(database_session: Session, client, tmp_path) -> None:
    FoodIngestionService(database_session).import_csv(write_csv(tmp_path, VALID_ROW))
    service = NutritionService(FoodRepository(database_session), food_alias_repository=FoodAliasRepository(database_session))

    assert service.resolve_food_name(" CURATED  TEST FOOD ").name == "Curated Test Food"
    assert service.resolve_food_name(" test alias ").name == "Curated Test Food"
    assert service.resolve_food_name("unknown food") is None
    search = client.get("/api/nutrition/search", params={"q": "alias"})
    assert search.status_code == 200
    assert [food["name"] for food in search.json()["foods"]] == ["Curated Test Food"]


def test_meal_analysis_resolves_a_recognized_alias_to_its_canonical_food(database_session: Session, tmp_path) -> None:
    class AliasRecognitionProvider(FoodRecognitionProvider):
        def recognize_food(self, *, image_bytes: bytes, content_type: str) -> FoodRecognitionResult:
            return FoodRecognitionResult(food_names=("test alias",), source="simulated")

    FoodIngestionService(database_session).import_csv(write_csv(tmp_path, VALID_ROW))
    nutrition_service = NutritionService(
        FoodRepository(database_session), food_alias_repository=FoodAliasRepository(database_session)
    )
    result = MealAnalysisService(AliasRecognitionProvider(), nutrition_service).analyze(
        image_bytes=b"test", content_type="image/jpeg", weight_grams=Decimal("100")
    )

    assert result.status == "calculated"
    assert result.food.name == "Curated Test Food"


def test_cli_dry_run_missing_file_and_success(database_session: Session, tmp_path, capsys) -> None:
    path = write_csv(tmp_path, VALID_ROW)
    session_factory = lambda: database_session
    assert import_foods_main([str(path), "--dry-run"], session_factory=session_factory) == 0
    assert food_count(database_session) == 0
    assert import_foods_main([str(tmp_path / "missing.csv")], session_factory=session_factory) == 1
    # A real CLI run commits its owning session; use the transaction-isolated test session
    # only for its validation-compatible command path.
    assert "Rows processed: 1" in capsys.readouterr().out


def test_blank_core_nutrient_is_rejected_but_blank_optional_is_null(
    database_session: Session, tmp_path
) -> None:
    with pytest.raises(FoodIngestionValidationError) as exception:
        FoodIngestionService(database_session).import_csv(
            write_csv(tmp_path, make_row(protein_g_per_100g="")), dry_run=True
        )

    assert any(issue.field == "protein_g_per_100g" for issue in exception.value.report.errors)
    FoodIngestionService(database_session).import_csv(
        write_csv(tmp_path, make_row(omega_3_g_per_100g=""))
    )
    food = database_session.scalar(select(Food))
    assert food is not None
    assert food.omega_3_g_per_100g is None


@pytest.mark.parametrize("field", ["omega_3_g_per_100g", "vitamin_d_mcg_per_100g"])
@pytest.mark.parametrize("value", ["-0.001", "NaN", "Infinity"])
def test_optional_v2_nutrients_reject_invalid_nonblank_values(
    database_session: Session, tmp_path, field: str, value: str
) -> None:
    with pytest.raises(FoodIngestionValidationError):
        FoodIngestionService(database_session).import_csv(
            write_csv(tmp_path, make_row(**{field: value})), dry_run=True
        )


def test_missing_optional_v2_header_is_allowed(database_session: Session, tmp_path) -> None:
    path = tmp_path / "missing-header.csv"
    fields = tuple(field for field in CSV_FIELDS if field != "sodium_mg_per_100g")
    path.write_text(
        ",".join(fields) + "\n" + ",".join(DEFAULT_ROW[field] for field in fields) + "\n",
        encoding="utf-8",
    )

    report = FoodIngestionService(database_session).import_csv(path, dry_run=True)
    assert report.valid == 1


@pytest.mark.parametrize("field", ["phosphorus_mg_per_100g", "vitamin_b6_mg_per_100g", "niacin_mg_per_100g"])
@pytest.mark.parametrize("value", ["-0.001", "NaN", "Infinity", "1.0001"])
def test_new_optional_nutrients_reject_invalid_values(database_session: Session, tmp_path, field: str, value: str) -> None:
    with pytest.raises(FoodIngestionValidationError):
        FoodIngestionService(database_session).import_csv(write_csv(tmp_path, make_row(**{field: value})), dry_run=True)


@pytest.mark.parametrize(
    "source_type",
    ["canteen_recipe", "local_database", "USDA", "AI_estimate"],
)
def test_import_accepts_each_approved_source_category(
    database_session: Session, tmp_path, source_type: str
) -> None:
    report = FoodIngestionService(database_session).import_csv(
        write_csv(
            tmp_path,
            make_row(
                name=f"Source {source_type}",
                source_type=source_type,
                is_verified="false",
                aliases="",
            ),
        )
    )

    assert report.inserted == 1


def test_import_rejects_unsupported_or_verified_ai_source(database_session: Session, tmp_path) -> None:
    for name, source_type, is_verified, message in (
        ("Unsupported", "other", "false", "Unsupported source category"),
        ("Estimated", "AI_estimate", "true", "must not be marked verified"),
    ):
        with pytest.raises(FoodIngestionValidationError) as exception:
            FoodIngestionService(database_session).import_csv(
                write_csv(
                    tmp_path,
                    make_row(
                        name=name,
                        source_type=source_type,
                        is_verified=is_verified,
                        aliases="",
                    ),
                    f"{name}.csv",
                ),
                dry_run=True,
            )
        assert any(message in issue.message for issue in exception.value.report.errors)
