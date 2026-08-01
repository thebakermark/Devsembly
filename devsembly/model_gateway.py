from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import hmac
import json
import os
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, Header, HTTPException, Request, Response

_ALLOWED_PATHS = frozenset({"/v1/messages", "/v1/messages/count_tokens"})
_FORWARDED_HEADERS = frozenset({"anthropic-beta", "anthropic-version", "content-type"})


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


@dataclass(frozen=True)
class ModelGatewayClaims:
    task_id: str
    provider: str
    expires_at: int
    nonce: str


class ModelGatewayTokenCodec:
    """Issue and verify short-lived task tokens without exposing the provider API key."""

    def __init__(self, secret: str, *, ttl_seconds: int = 300) -> None:
        if len(secret.encode()) < 32:
            raise ValueError("Model-gateway signing secret must contain at least 32 bytes")
        if not 1 <= ttl_seconds <= 900:
            raise ValueError("Model-gateway task-token TTL must be between 1 and 900 seconds")
        self._secret = secret.encode()
        self._ttl_seconds = ttl_seconds

    def issue(self, task_id: str, *, now: int | None = None) -> str:
        issued_at = int(time.time()) if now is None else now
        payload = {
            "exp": issued_at + self._ttl_seconds,
            "nonce": secrets.token_urlsafe(16),
            "provider": "anthropic",
            "task_id": task_id,
        }
        body = _encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
        signature = _encode(hmac.new(self._secret, body.encode(), hashlib.sha256).digest())
        return f"{body}.{signature}"

    def verify(self, token: str, *, now: int | None = None) -> ModelGatewayClaims:
        if len(token) > 4096:
            raise ValueError("Invalid model-gateway task token")
        try:
            body, supplied_signature = token.split(".", 1)
            expected_signature = _encode(
                hmac.new(self._secret, body.encode(), hashlib.sha256).digest()
            )
            if not hmac.compare_digest(supplied_signature, expected_signature):
                raise ValueError("invalid signature")
            payload = json.loads(_decode(body))
            claims = ModelGatewayClaims(
                task_id=str(payload["task_id"]),
                provider=str(payload["provider"]),
                expires_at=int(payload["exp"]),
                nonce=str(payload["nonce"]),
            )
        except (
            binascii.Error,
            KeyError,
            TypeError,
            UnicodeDecodeError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            raise ValueError("Invalid model-gateway task token") from exc
        observed_at = int(time.time()) if now is None else now
        if claims.provider != "anthropic" or claims.expires_at <= observed_at:
            raise ValueError("Expired or unsupported model-gateway task token")
        return claims


@dataclass(frozen=True)
class ModelGatewayConfiguration:
    provider_base_url: str
    provider_api_key: str
    signing_secret: str
    allowed_models: frozenset[str]
    allowed_hosts: frozenset[str] = frozenset({"api.anthropic.com"})
    max_request_bytes: int = 2_097_152
    max_response_bytes: int = 33_554_432
    timeout_seconds: float = 600.0
    max_requests_per_token: int = 64
    max_output_tokens_per_request: int = 32_768

    def __post_init__(self) -> None:
        parsed = urlsplit(self.provider_base_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Model provider base URL must be a credential-free HTTPS origin")
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise ValueError("Model provider base URL must not contain a path, query, or fragment")
        if parsed.hostname not in self.allowed_hosts:
            raise ValueError("Model provider host is not allowlisted")
        ModelGatewayTokenCodec(self.signing_secret)
        if not self.provider_api_key:
            raise ValueError("Model provider API key is required")
        if not self.allowed_models:
            raise ValueError("At least one allowed model is required")
        if not 1 <= self.max_requests_per_token <= 256:
            raise ValueError("Model request limit must be between 1 and 256")
        if not 1 <= self.max_output_tokens_per_request <= 65_536:
            raise ValueError("Model output-token limit must be between 1 and 65536")

    @classmethod
    def from_environment(cls) -> ModelGatewayConfiguration:
        models = frozenset(
            item.strip()
            for item in os.getenv("DEVSEMBLY_MODEL_GATEWAY_ALLOWED_MODELS", "").split(",")
            if item.strip()
        )
        hosts = frozenset(
            item.strip().lower()
            for item in os.getenv(
                "DEVSEMBLY_MODEL_PROVIDER_ALLOWED_HOSTS", "api.anthropic.com"
            ).split(",")
            if item.strip()
        )
        return cls(
            provider_base_url=os.getenv(
                "DEVSEMBLY_MODEL_PROVIDER_BASE_URL", "https://api.anthropic.com"
            ).rstrip("/"),
            provider_api_key=os.getenv("DEVSEMBLY_MODEL_PROVIDER_API_KEY", ""),
            signing_secret=os.getenv("DEVSEMBLY_MODEL_GATEWAY_SECRET", ""),
            allowed_models=models,
            allowed_hosts=hosts,
        )


ClientFactory = Callable[[], httpx.AsyncClient]


def create_model_gateway_app(
    configuration: ModelGatewayConfiguration | None = None,
    *,
    client_factory: ClientFactory | None = None,
) -> FastAPI:
    app = FastAPI(title="Devsembly Model Egress Gateway", docs_url=None, redoc_url=None)
    usage: dict[str, tuple[int, int]] = {}
    usage_lock = asyncio.Lock()

    def config() -> ModelGatewayConfiguration:
        try:
            return configuration or ModelGatewayConfiguration.from_environment()
        except ValueError as exc:
            raise HTTPException(status_code=503, detail="Model gateway is not configured") from exc

    @app.get("/health/live")
    async def health() -> dict[str, str]:
        config()
        return {"status": "ok"}

    async def proxy(path: str, request: Request, authorization: str | None) -> Response:
        gateway = config()
        if path not in _ALLOWED_PATHS:
            raise HTTPException(status_code=404, detail="Unsupported model-provider operation")
        if authorization is None or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing task token")
        token = authorization.removeprefix("Bearer ")
        try:
            claims = ModelGatewayTokenCodec(gateway.signing_secret).verify(token)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail="Invalid task token") from exc
        token_key = hashlib.sha256(token.encode()).hexdigest()
        observed_at = int(time.time())
        async with usage_lock:
            expired = [key for key, (_, expires_at) in usage.items() if expires_at <= observed_at]
            for key in expired:
                del usage[key]
            request_count, _ = usage.get(token_key, (0, claims.expires_at))
            if request_count >= gateway.max_requests_per_token:
                raise HTTPException(status_code=429, detail="Task model-request limit reached")
            usage[token_key] = (request_count + 1, claims.expires_at)
        body = await request.body()
        if len(body) > gateway.max_request_bytes:
            raise HTTPException(status_code=413, detail="Model request exceeds configured limit")
        try:
            payload: Any = json.loads(body)
            model = payload["model"]
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=400, detail="Model request must contain JSON model"
            ) from exc
        if not isinstance(model, str) or model not in gateway.allowed_models:
            raise HTTPException(status_code=403, detail="Requested model is not allowed")
        if path == "/v1/messages":
            max_tokens = payload.get("max_tokens")
            if (
                not isinstance(max_tokens, int)
                or isinstance(max_tokens, bool)
                or not 1 <= max_tokens <= gateway.max_output_tokens_per_request
            ):
                raise HTTPException(
                    status_code=403, detail="Requested output-token limit is not allowed"
                )

        headers = {
            name: value
            for name, value in request.headers.items()
            if name.lower() in _FORWARDED_HEADERS
        }
        headers["x-api-key"] = gateway.provider_api_key
        factory = client_factory or (lambda: httpx.AsyncClient(timeout=gateway.timeout_seconds))
        try:
            async with (
                factory() as client,
                client.stream(
                    "POST",
                    f"{gateway.provider_base_url.rstrip('/')}{path}",
                    content=body,
                    headers=headers,
                ) as upstream,
            ):
                response_body = bytearray()
                async for chunk in upstream.aiter_bytes():
                    response_body.extend(chunk)
                    if len(response_body) > gateway.max_response_bytes:
                        raise HTTPException(
                            status_code=502, detail="Model response exceeds configured limit"
                        )
                response_headers = {}
                content_type = upstream.headers.get("content-type")
                if content_type:
                    response_headers["content-type"] = content_type
                return Response(
                    content=bytes(response_body),
                    status_code=upstream.status_code,
                    headers=response_headers,
                )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail="Model provider request failed") from exc

    @app.post("/v1/messages")
    async def messages(
        request: Request, authorization: str | None = Header(default=None)
    ) -> Response:
        return await proxy("/v1/messages", request, authorization)

    @app.post("/v1/messages/count_tokens")
    async def count_tokens(
        request: Request, authorization: str | None = Header(default=None)
    ) -> Response:
        return await proxy("/v1/messages/count_tokens", request, authorization)

    return app


app = create_model_gateway_app()
