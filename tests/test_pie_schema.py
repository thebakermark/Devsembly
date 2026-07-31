from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from devsembly.domain import ProjectStateAssertionStatus, ProjectStateRevision
from devsembly.pie_projection import build_projection

ROOT = Path(__file__).resolve().parents[1]


def test_project_intelligence_schema_and_bootstrap_state() -> None:
    schema = json.loads(
        (ROOT / "docs/genesis/schemas/project-intelligence-state.schema.json").read_text()
    )
    state = json.loads((ROOT / ".devsembly/project-state.json").read_text())

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(state)

    now = datetime(2026, 7, 31, tzinfo=UTC)
    revision = ProjectStateRevision(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        version=1,
        parent_revision_id=None,
        schema_version="1.0",
        state=state,
        state_sha256="0" * 64,
        idempotency_key="bootstrap",
        request_fingerprint="0" * 64,
        source_provider="repository",
        source_kind="bootstrap",
        source_event_id=None,
        source_uri=None,
        source_occurred_at=None,
        observed_at=now,
        assertion_status=ProjectStateAssertionStatus.VERIFIED,
        confidence=Decimal("1.0000"),
        confidence_explanation="Schema fixture.",
        created_at=now,
    )
    projection = build_projection(revision, now)
    assert len(projection.work_items) == 7
    assert len(projection.aliases) == 7
    assert len(projection.graph_nodes) == 4
    assert len(projection.graph_edges) == 2
    assert len(projection.validation_results) == 6
