from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]


def test_project_intelligence_schema_and_bootstrap_state() -> None:
    schema = json.loads(
        (ROOT / "docs/genesis/schemas/project-intelligence-state.schema.json").read_text()
    )
    state = json.loads((ROOT / ".devsembly/project-state.json").read_text())

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(state)
