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


HEADERS = "name,category,calories_per_100g,protein_g_per_100g,carbohydrates_g_per_100g,fat_g_per_100g,fiber_g_per_100g,source_name,source_reference,is_verified,aliases\n"
VALID_ROW = "Curated Test Food,Test,123.45,10.123,20.000,5.000,3.000,TEST_SOURCE,TEST-001,false,Test Alias|Other Alias\n"


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
        ("Bad,Test,not-a-number,1,1,1,1,S,R,false,\n", "valid Decimal"),
        ("Bad,Test,-1,1,1,1,1,S,R,false,\n", "must not be negative"),
        (",Test,1,1,1,1,1,S,R,false,\n", "Value is required"),
        ("Bad,Test,1,1,1,1,1,,R,false,\n", "Value is required"),
        ("Bad,Test,NaN,1,1,1,1,S,R,false,\n", "must be finite"),
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
    assert [(alias.alias, alias.normalized_alias) for alias in aliases] == [
        ("Other Alias", "other alias"),
        ("Test Alias", "test alias"),
    ]


def test_invalid_file_rolls_back_all_rows(database_session: Session, tmp_path) -> None:
    rows = VALID_ROW + "Broken,Test,-1,1,1,1,1,S,R,false,\n"
    with pytest.raises(FoodIngestionValidationError):
        FoodIngestionService(database_session).import_csv(write_csv(tmp_path, rows))

    assert food_count(database_session) == 0


def test_duplicate_canonical_and_alias_conflicts_are_rejected(database_session: Session, tmp_path) -> None:
    rows = (
        VALID_ROW
        + "  curated   test food ,Test,1,1,1,1,1,S,R,false,\n"
        + "Other Food,Test,1,1,1,1,1,S,R,false,Test Alias\n"
    )
    with pytest.raises(FoodIngestionValidationError) as exception:
        FoodIngestionService(database_session).import_csv(write_csv(tmp_path, rows), dry_run=True)

    assert any("Duplicate normalized" in issue.message for issue in exception.value.report.errors)
    assert any("Duplicate normalized" in issue.message for issue in exception.value.report.errors)


def test_duplicate_alias_in_one_row_is_rejected(database_session: Session, tmp_path) -> None:
    duplicate_alias_row = "Food,Test,1,1,1,1,1,S,R,false,Same Alias| same   alias \n"
    with pytest.raises(FoodIngestionValidationError) as exception:
        FoodIngestionService(database_session).import_csv(write_csv(tmp_path, duplicate_alias_row), dry_run=True)

    assert any("Duplicate normalized" in issue.message for issue in exception.value.report.errors)


def test_existing_canonical_and_alias_conflicts_are_rejected(database_session: Session, tmp_path) -> None:
    FoodIngestionService(database_session).import_csv(write_csv(tmp_path, VALID_ROW))
    conflicting = "New Food,Test,1,1,1,1,1,S,R,false,Other Alias\n"
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
