"""Export the FastAPI-generated OpenAPI contract without starting a server."""

from __future__ import annotations

import json
from pathlib import Path

from app.main import app


DEFAULT_OUTPUT = Path(__file__).resolve().parents[3] / "docs" / "openapi.json"


def export_openapi(output_path: Path = DEFAULT_OUTPUT) -> Path:
    """Write a deterministic JSON representation of the actual application schema."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output_path


def main() -> int:
    output_path = export_openapi()
    print(f"OpenAPI exported to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
