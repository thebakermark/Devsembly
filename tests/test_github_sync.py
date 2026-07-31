from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from devsembly.github_sync import (
    InvalidGitHubEvent,
    InvalidGitHubSignature,
    normalize_event,
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
