"""Import curated nutrition reference foods from a local CSV file."""

from __future__ import annotations

import argparse
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.services.food_ingestion_service import FoodIngestionService, FoodIngestionValidationError


def _print_report(report) -> None:
    print(f"Rows processed: {report.rows_processed}")
    print(f"Valid: {report.valid}")
    print(f"Invalid: {report.invalid}")
    print(f"Planned inserts: {report.planned_inserts}")
    print(f"Planned aliases: {report.planned_aliases}")
    print(f"Inserted: {report.inserted}")
    print(f"Updated: {report.updated}")
    print(f"Skipped: {report.skipped}")
    print(f"Aliases inserted: {report.aliases_inserted}")
    print(f"Warnings: {len(report.warnings)}")
    for issue in report.errors:
        location = f"row {issue.row_number}" if issue.row_number is not None else "file"
        field = f" ({issue.field})" if issue.field else ""
        print(f"ERROR {location}{field}: {issue.message}")


def main(argv: list[str] | None = None, session_factory: Callable[[], Session] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import curated Nutri-Box food CSV data.")
    parser.add_argument("path", help="Path to a UTF-8 CSV file.")
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing to PostgreSQL.")
    args = parser.parse_args(argv)
    factory = session_factory or SessionLocal
    if factory is None:
        print("DATABASE_URL must be configured before importing foods.")
        return 1
    session = factory()
    try:
        report = FoodIngestionService(session).import_csv(args.path, dry_run=args.dry_run)
        if not args.dry_run:
            session.commit()
        _print_report(report)
        if args.dry_run:
            print("Dry run completed: PostgreSQL was not modified.")
        return 0
    except FoodIngestionValidationError as exception:
        _print_report(exception.report)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
