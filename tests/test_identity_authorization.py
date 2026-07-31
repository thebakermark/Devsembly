from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from devsembly.api import app
from devsembly.auth import (
    ROLE_PERMISSIONS,
    Permission,
    _cached_oidc_verifier,
    decode_oidc_token,
    get_token_verifier,
)


def test_role_permissions_are_least_privilege() -> None:
    assert ROLE_PERMISSIONS["viewer"] == {Permission.READ}
    assert Permission.WRITE in ROLE_PERMISSIONS["operator"]
    assert Permission.APPROVE not in ROLE_PERMISSIONS["operator"]
    assert Permission.APPROVE in ROLE_PERMISSIONS["approver"]
    assert Permission.WRITE not in ROLE_PERMISSIONS["approver"]
    assert ROLE_PERMISSIONS["owner"] == frozenset(Permission)


def test_every_human_organization_route_has_authorization_dependency() -> None:
    paths = app.openapi()["paths"]
    human_paths = {
        path: operations
        for path, operations in paths.items()
        if path.startswith("/api/v1/organizations")
    }
    assert human_paths
    for path, operations in human_paths.items():
        for operation in operations.values():
            assert operation["security"] == [{"HTTPBearer": []}], path


def test_openapi_declares_bearer_auth_and_identity_endpoints() -> None:
    schema = app.openapi()
    bearer = schema["components"]["securitySchemes"]["HTTPBearer"]
    assert bearer == {"type": "http", "scheme": "bearer"}
    assert "/api/v1/me" in schema["paths"]
    assert "/api/v1/organizations/{organization_id}/memberships" in schema["paths"]
    assert "/api/v1/organizations/{organization_id}/delegations" in schema["paths"]


def test_oidc_validation_enforces_signature_issuer_audience_and_expiry() -> None:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(UTC)
    claims = {
        "iss": "https://issuer.test",
        "sub": "human-1",
        "aud": "devsembly",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    token = jwt.encode(claims, key, algorithm="RS256")
    decoded = decode_oidc_token(
        token,
        key=key.public_key(),
        issuer="https://issuer.test/",
        audience="devsembly",
    )
    assert decoded["sub"] == "human-1"

    with pytest.raises(jwt.InvalidIssuerError):
        decode_oidc_token(
            token,
            key=key.public_key(),
            issuer="https://other.test",
            audience="devsembly",
        )

    with pytest.raises(jwt.InvalidAudienceError):
        decode_oidc_token(
            token,
            key=key.public_key(),
            issuer="https://issuer.test",
            audience="other",
        )

    expired = jwt.encode({**claims, "exp": now - timedelta(seconds=1)}, key, algorithm="RS256")
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_oidc_token(
            expired,
            key=key.public_key(),
            issuer="https://issuer.test",
            audience="devsembly",
        )


def test_oidc_verifier_is_reused_for_the_same_provider_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _cached_oidc_verifier.cache_clear()
    monkeypatch.setenv("DEVSEMBLY_OIDC_ISSUER", "https://issuer.cache.test/")
    monkeypatch.setenv("DEVSEMBLY_OIDC_AUDIENCE", "devsembly")
    first = get_token_verifier()
    second = get_token_verifier()
    assert first is second

    monkeypatch.setenv("DEVSEMBLY_OIDC_AUDIENCE", "other")
    assert get_token_verifier() is not first
    _cached_oidc_verifier.cache_clear()
