from __future__ import annotations
import json
from pathlib import Path
from typing import Any
import jsonschema


def load_schema(schema_filename: str) -> dict[str, Any]:
    """Load JSON Schema from the schemas/ directory."""
    # Find repository root
    base_dir = Path(__file__).resolve().parent.parent.parent
    schema_path = base_dir / "schemas" / schema_filename
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found at: {schema_path}")
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_contract(data: Any, schema_filename: str) -> None:
    """
    Validate JSON payload against a specified JSON Schema file.
    Raises jsonschema.exceptions.ValidationError with detailed error path on mismatch.
    """
    schema = load_schema(schema_filename)
    jsonschema.validate(instance=data, schema=schema)
