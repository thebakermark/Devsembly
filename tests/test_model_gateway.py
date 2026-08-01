from __future__ import annotations

import json

import httpx
import pytest

from devsembly.model_gateway import (
    ModelGatewayConfiguration,
    ModelGatewayTokenCodec,
    create_model_gateway_app,
)

SECRET = "gateway-signing-secret-that-is-at-least-32-bytes"


def configuration(**overrides: object) -> ModelGatewayConfiguration:
    values: dict[str, object] = {
        "provider_base_url": "https://api.anthropic.com",
        "provider_api_key": "provider-secret",
        "signing_secret": SECRET,
        "allowed_models": frozenset({"claude-sonnet-fixture"}),
    }
    values.update(overrides)
    return ModelGatewayConfiguration(**values)  # type: ignore[arg-type]


def test_task_token_is_scoped_signed_and_short_lived() -> None:
    codec = ModelGatewayTokenCodec(SECRET, ttl_seconds=60)
    token = codec.issue("task-123", now=1_000)

    claims = codec.verify(token, now=1_059)

    assert claims.task_id == "task-123"
    assert claims.provider == "anthropic"
    with pytest.raises(ValueError, match="Expired"):
        codec.verify(token, now=1_060)
    with pytest.raises(ValueError, match="Invalid"):
        codec.verify(f"{token}tampered", now=1_001)


def test_provider_destination_must_be_allowlisted_https() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        configuration(provider_base_url="http://api.anthropic.com")
    with pytest.raises(ValueError, match="allowlisted"):
        configuration(provider_base_url="https://example.invalid")


@pytest.mark.asyncio
async def test_gateway_replaces_task_auth_and_forwards_only_to_fixed_provider() -> None:
    observed: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        observed.append(request)
        return httpx.Response(200, json={"content": [{"type": "text", "text": "ok"}]})

    def client_factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(handler))

    config = configuration()
    app = create_model_gateway_app(config, client_factory=client_factory)
    token = ModelGatewayTokenCodec(SECRET).issue("task-123")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://gateway"
    ) as client:
        response = await client.post(
            "/v1/messages",
            headers={
                "authorization": f"Bearer {token}",
                "anthropic-version": "2023-06-01",
                "x-untrusted-header": "drop-me",
            },
            json={"model": "claude-sonnet-fixture", "messages": []},
        )

    assert response.status_code == 200
    assert len(observed) == 1
    assert str(observed[0].url) == "https://api.anthropic.com/v1/messages"
    assert observed[0].headers["x-api-key"] == "provider-secret"
    assert "authorization" not in observed[0].headers
    assert "x-untrusted-header" not in observed[0].headers


@pytest.mark.asyncio
async def test_gateway_rejects_invalid_token_and_disallowed_model_without_egress() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200)

    def client_factory() -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(handler))

    app = create_model_gateway_app(configuration(), client_factory=client_factory)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://gateway") as client:
        invalid = await client.post(
            "/v1/messages", headers={"authorization": "Bearer invalid"}, json={"model": "x"}
        )
        token = ModelGatewayTokenCodec(SECRET).issue("task-123")
        disallowed = await client.post(
            "/v1/messages",
            headers={"authorization": f"Bearer {token}"},
            content=json.dumps({"model": "not-allowed", "messages": []}),
        )

    assert invalid.status_code == 401
    assert disallowed.status_code == 403
    assert calls == 0
