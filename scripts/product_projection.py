#!/usr/bin/env python3
"""Render or verify the canonical product-definition projection.

The canonical input is resolved through ``.devsembly/manifest.json``. The
manifest keeps one governed source-of-truth package while allowing large,
independently changing domains to live in separate schema-controlled modules.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
STATE_ROOT = ROOT / ".devsembly"
MANIFEST_PATH = STATE_ROOT / "manifest.json"
SCHEMA_PATH = ROOT / "docs" / "genesis" / "schemas" / "product-definition.schema.json"
OUTPUT_PATH = ROOT / "docs" / "product" / "product-definition.generated.md"


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def resolve_module(manifest: dict[str, Any], module_name: str) -> Path:
    modules = manifest.get("modules")
    if not isinstance(modules, dict):
        raise SystemExit(".devsembly/manifest.json is missing object 'modules'")
    relative_path = modules.get(module_name)
    if not isinstance(relative_path, str) or not relative_path:
        raise SystemExit(f"manifest is missing module '{module_name}'")

    resolved = (STATE_ROOT / relative_path).resolve()
    state_root = STATE_ROOT.resolve()
    if resolved.parent != state_root:
        raise SystemExit(f"module '{module_name}' must be a direct child of .devsembly")
    return resolved


def render(definition: dict[str, Any]) -> str:
    names = definition["names"]
    audience = "\n".join(f"- {item}" for item in definition["target_audiences"])
    principles = "\n\n".join(
        f"### {item['title']}\n\n{item['statement']}"
        for item in definition["design_principles"]
    )
    naming_rows = "\n".join(
        f"| `{binding['stable_id']}` | {binding['display_name']} | {binding['technical_term']} |"
        for binding in names.values()
    )
    return f"""<!-- GENERATED FILE: edit .devsembly/product-definition.json, not this file. -->
# {definition['display_name']} Product Definition

**Stable ID:** `{definition['stable_id']}`  
**Category:** {definition['category']}  
**Tagline:** {definition['tagline']}

## General description

{definition['general_description']}

## Plain-language description

{definition['plain_language_description']}

## Technical description

{definition['technical_description']}

## Mission

{definition['mission']}

## Target audiences

{audience}

## Design principles

{principles}

## Naming configuration

| Stable identifier | Display name | Industry-standard term |
| --- | --- | --- |
{naming_rows}
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="write the generated projection")
    mode.add_argument("--check", action="store_true", help="fail when the projection has drifted")
    args = parser.parse_args()

    manifest = load_json(MANIFEST_PATH)
    definition_path = resolve_module(manifest, "product_definition")
    definition = load_json(definition_path)

    schema = load_json(SCHEMA_PATH)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(definition),
        key=lambda item: list(item.path),
    )
    if errors:
        formatted = "\n".join(
            f"- {'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
            for error in errors
        )
        raise SystemExit(f"product definition is invalid:\n{formatted}")

    expected = render(definition)
    if args.write:
        OUTPUT_PATH.write_text(expected, encoding="utf-8")
        return 0

    actual = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else ""
    if actual != expected:
        raise SystemExit(
            "generated product definition is stale; run "
            "'python scripts/product_projection.py --write' and commit the result"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
