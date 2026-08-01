#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {".git", ".venv", "node_modules"}
INLINE_LINK = re.compile(r"!?\[[^\]]*]\(([^)]+)\)")
REFERENCE_LINK = re.compile(r"^\s*\[[^\]]+]:\s*(\S+)")
EXTERNAL_SCHEMES = {"data", "http", "https", "mailto", "tel"}


def markdown_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*.md")
        if not EXCLUDED_PARTS.intersection(path.relative_to(ROOT).parts)
    )


def targets(path: Path) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    in_fence = False
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        found.extend((line_number, match.group(1)) for match in INLINE_LINK.finditer(line))
        reference = REFERENCE_LINK.match(line)
        if reference is not None:
            found.append((line_number, reference.group(1)))
    return found


def clean_target(raw_target: str) -> str | None:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    elif " " in target:
        target = target.split(" ", 1)[0]
    target = target.strip("'\"")
    if not target or target.startswith("#"):
        return None
    parsed = urlsplit(target)
    if parsed.scheme.lower() in EXTERNAL_SCHEMES or target.startswith("//"):
        return None
    return unquote(parsed.path)


def resolves(source: Path, target: str) -> bool:
    candidate = ROOT / target.lstrip("/") if target.startswith("/") else source.parent / target
    candidate = candidate.resolve()
    if not candidate.is_relative_to(ROOT):
        return False
    if candidate.exists():
        return True
    if "wiki" in source.relative_to(ROOT).parts and candidate.suffix == "":
        return candidate.with_suffix(".md").is_file()
    return False


def main() -> int:
    failures: list[str] = []
    files = markdown_files()
    for source in files:
        for line_number, raw_target in targets(source):
            target = clean_target(raw_target)
            if target is not None and not resolves(source, target):
                relative_source = source.relative_to(ROOT)
                failures.append(f"{relative_source}:{line_number}: missing link target {target}")

    if failures:
        print(*failures, sep="\n", file=sys.stderr)
        print(f"Markdown link validation failed with {len(failures)} error(s).", file=sys.stderr)
        return 1

    print(f"Markdown link validation passed for {len(files)} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
