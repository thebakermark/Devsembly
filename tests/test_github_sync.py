from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from devsembly.github_sync import (
    InvalidGitHubEvent,
    InvalidGitHubSignature,
    normalize_event,
    normalize_snapshot_entity,
    verify_signature,
)


def _body(updated_at: str = "2026-07-31T17:00:00Z", title: str = "Synchronize GitHub") -> bytes:
    return json.dumps(
        {
            "action": "edited",
            "repository": {"id": 991, "full_name": "thebakermark/Devsembly"},
            "issue": {
                "id": 2600,
                "node_id": "I_kw26",
                "number": 26,
                "title": title,
                "updated_at": updated_at,
            },
        }
    ).encode()


def test_signature_requires_exact_sha256_hmac() -> None:
    body = _body()
    signature = "sha256=" + hmac.new(b"secret", body, hashlib.sha256).hexdigest()
    verify_signature(body, signature, "secret")
    with pytest.raises(InvalidGitHubSignature):
        verify_signature(body + b" ", signature, "secret")
    with pytest.raises(InvalidGitHubSignature):
        verify_signature(body, None, "secret")


def test_normalization_uses_stable_provider_ids_and_canonical_hashes() -> None:
    first = normalize_event(_body(), "delivery-1", "issues")
    replay = normalize_event(_body(), "delivery-1", "issues")
    changed = normalize_event(_body(title="Changed"), "delivery-2", "issues")
    assert first.repository_id == "991"
    assert first.entity_kind == "issue"
    assert first.entity_id == "github:991:issue:I_kw26"
    assert first.payload_sha256 == replay.payload_sha256
    assert first.payload_sha256 != changed.payload_sha256
    assert first.occurred_at is not None
    assert first.occurred_at.isoformat() == "2026-07-31T17:00:00+00:00"


def test_normalization_rejects_events_without_repository_or_entity_identity() -> None:
    with pytest.raises(InvalidGitHubEvent):
        normalize_event(b"{}", "delivery-1", "issues")
    body = json.dumps({"repository": {"id": 991}, "issue": {"title": "missing id"}}).encode()
    with pytest.raises(InvalidGitHubEvent):
        normalize_event(body, "delivery-1", "issues")


def test_snapshot_normalization_is_retry_safe_and_uses_provider_identity() -> None:
    entity = {
        "id": 2600,
        "node_id": "I_kw26",
        "number": 26,
        "title": "Synchronize GitHub",
        "updated_at": "2026-07-31T17:00:00Z",
    }
    first = normalize_snapshot_entity("991", "issue", entity)
    replay = normalize_snapshot_entity("991", "issue", entity)
    assert first.delivery_id == replay.delivery_id
    assert first.delivery_id.startswith("snapshot:991:")
    assert first.entity_id == "github:991:issue:I_kw26"


def test_snapshot_normalization_changes_delivery_when_facts_change() -> None:
    original = normalize_snapshot_entity(
        "991", "milestone", {"id": 32, "title": "PIE", "updated_at": "2026-07-31T17:00:00Z"}
    )
    changed = normalize_snapshot_entity(
        "991", "milestone", {"id": 32, "title": "PIE v2", "updated_at": "2026-07-31T18:00:00Z"}
    )
    assert original.entity_id == changed.entity_id
    assert original.delivery_id != changed.delivery_id
