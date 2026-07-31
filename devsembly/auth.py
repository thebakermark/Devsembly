from __future__ import annotations

import asyncio
import hmac
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from functools import lru_cache
from typing import Annotated, Protocol

import httpx
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.algorithms import AllowedPublicKeys
from sqlalchemy import or_, select

from devsembly import models
from devsembly.audit import set_current_audit_actor
from devsembly.database import SessionFactory


class Permission(StrEnum):
    READ = "read"
    WRITE = "write"
    APPROVE = "approve"
    MANAGE_MEMBERS = "manage_members"


ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "owner": frozenset(Permission),
    "administrator": frozenset(
        {Permission.READ, Permission.WRITE, Permission.APPROVE, Permission.MANAGE_MEMBERS}
    ),
    "operator": frozenset({Permission.READ, Permission.WRITE}),
    "approver": frozenset({Permission.READ, Permission.APPROVE}),
    "viewer": frozenset({Permission.READ}),
}


@dataclass(frozen=True, slots=True)
class VerifiedIdentity:
    issuer: str
    subject: str
    display_name: str


@dataclass(frozen=True, slots=True)
class PrincipalContext:
    principal_id: uuid.UUID
    issuer: str
    subject: str
    display_name: str


class TokenVerifier(Protocol):
    async def verify(self, token: str) -> VerifiedIdentity: ...


class OidcTokenVerifier:
    def __init__(self, issuer: str, audience: str) -> None:
        self.issuer = issuer.rstrip("/")
        self.audience = audience
        self._jwks: PyJWKClient | None = None
        self._discovery_lock = asyncio.Lock()

    async def _jwks_client(self) -> PyJWKClient:
        if self._jwks is not None:
            return self._jwks
        async with self._discovery_lock:
            if self._jwks is not None:
                return self._jwks
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.issuer}/.well-known/openid-configuration")
                response.raise_for_status()
                metadata = response.json()
            if metadata.get("issuer", "").rstrip("/") != self.issuer:
                raise jwt.InvalidIssuerError("discovery issuer mismatch")
            jwks_uri = str(metadata.get("jwks_uri", ""))
            if not jwks_uri.startswith("https://"):
                raise jwt.InvalidTokenError("OIDC jwks_uri must use HTTPS")
            self._jwks = PyJWKClient(jwks_uri, cache_jwk_set=True, lifespan=300)
            return self._jwks

    async def verify(self, token: str) -> VerifiedIdentity:
        jwks = await self._jwks_client()

        def decode() -> dict[str, object]:
            key = jwks.get_signing_key_from_jwt(token).key
            return decode_oidc_token(token, key=key, issuer=self.issuer, audience=self.audience)

        claims = await asyncio.to_thread(decode)
        subject = str(claims["sub"]).strip()
        if not subject or len(subject) > 500:
            raise jwt.InvalidTokenError("empty subject")
        display_name = str(
            claims.get("name") or claims.get("preferred_username") or f"OIDC {subject[:12]}"
        ).strip()[:200]
        return VerifiedIdentity(self.issuer, subject, display_name)


def decode_oidc_token(
    token: str, *, key: AllowedPublicKeys, issuer: str, audience: str
) -> dict[str, object]:
    return jwt.decode(
        token,
        key,
        algorithms=["RS256", "ES256"],
        audience=audience,
        issuer=issuer.rstrip("/"),
        options={"require": ["exp", "iat", "iss", "sub", "aud"]},
    )


@lru_cache(maxsize=16)
def _cached_oidc_verifier(issuer: str, audience: str) -> OidcTokenVerifier:
    return OidcTokenVerifier(issuer, audience)


def get_token_verifier() -> TokenVerifier:
    issuer = os.getenv("DEVSEMBLY_OIDC_ISSUER", "").strip()
    audience = os.getenv("DEVSEMBLY_OIDC_AUDIENCE", "").strip()
    if not issuer or not audience:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "identity_provider_unavailable"},
        )
    return _cached_oidc_verifier(issuer, audience)


bearer = HTTPBearer(auto_error=False)


async def authenticated_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    verifier: Annotated[TokenVerifier, Depends(get_token_verifier)],
) -> PrincipalContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "authentication_required"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    if len(credentials.credentials) > 8192:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_access_token"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        identity = await verifier.verify(credentials.credentials)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_access_token"},
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    issuer = identity.issuer.rstrip("/")
    async with SessionFactory() as session, session.begin():
        external = await session.scalar(
            select(models.ExternalIdentity).where(
                models.ExternalIdentity.issuer == issuer,
                models.ExternalIdentity.subject == identity.subject,
            )
        )
        if external is None:
            principal = models.Principal(display_name=identity.display_name)
            session.add(principal)
            await session.flush()
            external = models.ExternalIdentity(
                principal_id=principal.id,
                issuer=issuer,
                subject=identity.subject,
            )
            session.add(external)
        else:
            existing_principal = await session.get(models.Principal, external.principal_id)
            if existing_principal is None:
                raise RuntimeError("external identity has no principal")
            principal = existing_principal
        session.add(
            models.AuditEvent(
                actor_type="human",
                actor_id=str(principal.id),
                action="identity.authenticated",
                object_type="principal",
                object_id=str(principal.id),
                outcome="success",
                payload={"issuer": issuer},
            )
        )
        return PrincipalContext(principal.id, issuer, identity.subject, principal.display_name)


CurrentPrincipal = Annotated[PrincipalContext, Depends(authenticated_principal)]


def required_permission(request: Request) -> Permission:
    if request.url.path.endswith("/memory/context"):
        return Permission.READ
    if (
        request.url.path.endswith("/approve")
        or request.url.path.endswith("/reject")
        or request.url.path.endswith("/resolve")
    ):
        return Permission.APPROVE
    if "/memberships" in request.url.path or "/delegations" in request.url.path:
        return Permission.MANAGE_MEMBERS
    return Permission.READ if request.method == "GET" else Permission.WRITE


async def authorize_request(request: Request, principal: CurrentPrincipal) -> PrincipalContext:
    set_current_audit_actor("human", str(principal.principal_id))
    organization_id = request.path_params.get("organization_id")
    if organization_id is None:
        if request.method == "POST" and request.url.path == "/api/v1/organizations":
            return principal
        return principal
    try:
        parsed_organization_id = uuid.UUID(str(organization_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail={"code": "resource_not_found"}) from exc

    permission = required_permission(request)
    now = datetime.now(UTC)
    project_value = request.path_params.get("project_id")
    project_id = uuid.UUID(str(project_value)) if project_value else None
    async with SessionFactory() as session:
        membership = await session.scalar(
            select(models.OrganizationMembership).where(
                models.OrganizationMembership.organization_id == parsed_organization_id,
                models.OrganizationMembership.principal_id == principal.principal_id,
                models.OrganizationMembership.status == "active",
            )
        )
        allowed = membership is not None and permission in ROLE_PERMISSIONS[membership.role]
        if membership is not None and not allowed:
            delegation = await session.scalar(
                select(models.AuthorizationDelegation).where(
                    models.AuthorizationDelegation.organization_id == parsed_organization_id,
                    models.AuthorizationDelegation.recipient_principal_id == principal.principal_id,
                    models.AuthorizationDelegation.action == permission.value,
                    models.AuthorizationDelegation.starts_at <= now,
                    models.AuthorizationDelegation.expires_at > now,
                    models.AuthorizationDelegation.revoked_at.is_(None),
                    (
                        models.AuthorizationDelegation.project_id.is_(None)
                        if project_id is None
                        else or_(
                            models.AuthorizationDelegation.project_id.is_(None),
                            models.AuthorizationDelegation.project_id == project_id,
                        )
                    ),
                )
            )
            allowed = delegation is not None
    async with SessionFactory() as audit_session, audit_session.begin():
        audit_session.add(
            models.AuditEvent(
                actor_type="human",
                actor_id=str(principal.principal_id),
                action="authorization.evaluated",
                object_type="organization",
                object_id=str(parsed_organization_id),
                organization_id=parsed_organization_id,
                project_id=project_id,
                outcome="allow" if allowed else "deny",
                payload={"permission": permission.value, "outcome": "allow" if allowed else "deny"},
            )
        )
    if not allowed:
        raise HTTPException(status_code=404, detail={"code": "resource_not_found"})
    return principal


AuthorizedPrincipal = Annotated[PrincipalContext, Depends(authorize_request)]


class IdentityManager:
    async def bootstrap_organization_owner(
        self, organization_id: uuid.UUID, principal: PrincipalContext
    ) -> None:
        async with SessionFactory() as session, session.begin():
            session.add(
                models.OrganizationMembership(
                    organization_id=organization_id,
                    principal_id=principal.principal_id,
                    role="owner",
                    status="active",
                )
            )
            session.add(
                models.AuditEvent(
                    actor_type="human",
                    actor_id=str(principal.principal_id),
                    action="organization.owner_bootstrapped",
                    object_type="organization",
                    object_id=str(organization_id),
                    organization_id=organization_id,
                    outcome="success",
                    payload={"role": "owner"},
                )
            )

    async def authorized_organization_ids(self, principal: PrincipalContext) -> set[uuid.UUID]:
        async with SessionFactory() as session:
            values = await session.scalars(
                select(models.OrganizationMembership.organization_id).where(
                    models.OrganizationMembership.principal_id == principal.principal_id,
                    models.OrganizationMembership.status == "active",
                )
            )
            return set(values)


def get_identity_manager() -> IdentityManager:
    return IdentityManager()


IdentityManagerDependency = Annotated[IdentityManager, Depends(get_identity_manager)]


def internal_control_authorized(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> None:
    expected = os.getenv("DEVSEMBLY_INTERNAL_CONTROL_TOKEN", "")
    if not expected:
        raise HTTPException(status_code=503, detail={"code": "machine_identity_unavailable"})
    if credentials is None or not hmac.compare_digest(credentials.credentials, expected):
        raise HTTPException(status_code=401, detail={"code": "invalid_machine_identity"})
