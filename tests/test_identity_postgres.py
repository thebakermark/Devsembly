from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from devsembly import models
from devsembly.api import app
from devsembly.auth import TokenVerifier, VerifiedIdentity, get_token_verifier
from devsembly.database import SessionFactory

TEST_DATABASE_URL = os.getenv("DEVSEMBLY_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="DEVSEMBLY_TEST_DATABASE_URL is required for PostgreSQL integration tests",
)


class DeterministicVerifier(TokenVerifier):
    async def verify(self, token: str) -> VerifiedIdentity:
        identities = {
            "alice": VerifiedIdentity("https://issuer.test", "alice", "Alice Owner"),
            "bob": VerifiedIdentity("https://issuer.test", "bob", "Bob Operator"),
        }
        if token not in identities:
            raise ValueError("invalid token")
        return identities[token]


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_oidc_memberships_delegation_and_audit_are_enforced() -> None:
    async with SessionFactory() as session, session.begin():
        await session.execute(
            text(
                "TRUNCATE outbox_events, audit_events, workflow_step_attempts, "
                "workflow_steps, workflow_runs, decisions, cost_evaluations, "
                "authorization_delegations, organization_memberships, external_identities, "
                "principals, budgets, projects, initiatives, organizations CASCADE"
            )
        )

    app.dependency_overrides.clear()
    app.dependency_overrides[get_token_verifier] = DeterministicVerifier
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.get("/api/v1/me")).status_code == 401
            assert (await client.get("/api/v1/me", headers=_headers("invalid"))).status_code == 401

            created = await client.post(
                "/api/v1/organizations",
                headers=_headers("alice"),
                json={"name": "Secured"},
            )
            assert created.status_code == 201
            organization_id = created.json()["id"]

            alice = (await client.get("/api/v1/me", headers=_headers("alice"))).json()
            repeated = (await client.get("/api/v1/me", headers=_headers("alice"))).json()
            assert repeated["id"] == alice["id"]
            memberships = await client.get(
                f"/api/v1/organizations/{organization_id}/memberships",
                headers=_headers("alice"),
            )
            owner_membership = memberships.json()[0]
            last_owner = await client.put(
                (f"/api/v1/organizations/{organization_id}/memberships/{owner_membership['id']}"),
                headers=_headers("alice"),
                json={"role": "viewer", "status": "active"},
            )
            assert last_owner.status_code == 409
            assert last_owner.json()["detail"]["code"] == "last_owner_required"

            bob = (await client.get("/api/v1/me", headers=_headers("bob"))).json()
            assert (
                await client.get(
                    f"/api/v1/organizations/{organization_id}",
                    headers=_headers("bob"),
                )
            ).status_code == 404
            assert (await client.get("/api/v1/organizations", headers=_headers("bob"))).json() == []

            membership = await client.post(
                f"/api/v1/organizations/{organization_id}/memberships",
                headers=_headers("alice"),
                json={"principal_id": bob["id"], "role": "viewer"},
            )
            assert membership.status_code == 201
            membership_id = membership.json()["id"]
            assert (
                await client.get(
                    f"/api/v1/organizations/{organization_id}",
                    headers=_headers("bob"),
                )
            ).status_code == 200
            initiative_path = f"/api/v1/organizations/{organization_id}/initiatives"
            assert (
                await client.post(
                    initiative_path,
                    headers=_headers("bob"),
                    json={"name": "Denied", "objective": "Viewer cannot write."},
                )
            ).status_code == 404

            now = datetime.now(UTC)
            delegation = await client.post(
                f"/api/v1/organizations/{organization_id}/delegations",
                headers=_headers("alice"),
                json={
                    "recipient_principal_id": bob["id"],
                    "action": "write",
                    "starts_at": (now - timedelta(minutes=1)).isoformat(),
                    "expires_at": (now + timedelta(minutes=10)).isoformat(),
                },
            )
            assert delegation.status_code == 201
            allowed = await client.post(
                initiative_path,
                headers=_headers("bob"),
                json={"name": "Delegated", "objective": "Bounded write authority."},
            )
            assert allowed.status_code == 201

            revoked = await client.post(
                (
                    f"/api/v1/organizations/{organization_id}/delegations/"
                    f"{delegation.json()['id']}/revoke"
                ),
                headers=_headers("alice"),
            )
            assert revoked.status_code == 200
            assert (
                await client.post(
                    initiative_path,
                    headers=_headers("bob"),
                    json={"name": "Denied again", "objective": "Delegation is revoked."},
                )
            ).status_code == 404

            suspended = await client.put(
                (f"/api/v1/organizations/{organization_id}/memberships/{membership_id}"),
                headers=_headers("alice"),
                json={"role": "viewer", "status": "suspended"},
            )
            assert suspended.status_code == 200
            assert (
                await client.get(
                    f"/api/v1/organizations/{organization_id}",
                    headers=_headers("bob"),
                )
            ).status_code == 404
    finally:
        app.dependency_overrides.clear()

    async with SessionFactory() as session:
        audit_events = list(await session.scalars(select(models.AuditEvent)))
        assert audit_events
        serialized = " ".join(str(event.payload) for event in audit_events)
        assert "alice" not in serialized
        assert "bob" not in serialized
