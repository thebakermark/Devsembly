from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text

from devsembly import models
from devsembly.api import app
from devsembly.auth import PrincipalContext, TokenVerifier, VerifiedIdentity, get_token_verifier
from devsembly.database import SessionFactory
from devsembly.identity_api import update_membership
from devsembly.identity_schemas import MembershipUpdate

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
    app.dependency_overrides[get_token_verifier] = lambda: DeterministicVerifier()
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


async def test_concurrent_owner_removal_preserves_one_active_owner() -> None:
    async with SessionFactory() as session, session.begin():
        await session.execute(
            text(
                "TRUNCATE outbox_events, audit_events, workflow_step_attempts, "
                "workflow_steps, workflow_runs, decisions, cost_evaluations, "
                "authorization_delegations, organization_memberships, external_identities, "
                "principals, budgets, projects, initiatives, organizations CASCADE"
            )
        )
        organization = models.Organization(name="Serialized owners")
        first_principal = models.Principal(display_name="First Owner")
        second_principal = models.Principal(display_name="Second Owner")
        session.add_all([organization, first_principal, second_principal])
        await session.flush()
        first_membership = models.OrganizationMembership(
            organization_id=organization.id,
            principal_id=first_principal.id,
            role="owner",
            status="active",
        )
        second_membership = models.OrganizationMembership(
            organization_id=organization.id,
            principal_id=second_principal.id,
            role="owner",
            status="active",
        )
        session.add_all([first_membership, second_membership])
        await session.flush()
        organization_id = organization.id
        membership_ids = (first_membership.id, second_membership.id)
        principal_id = first_principal.id

    principal = PrincipalContext(
        principal_id=principal_id,
        issuer="https://issuer.test",
        subject="first-owner",
        display_name="First Owner",
    )
    payload = MembershipUpdate(role="viewer", status="active")
    results = await asyncio.gather(
        update_membership(organization_id, membership_ids[0], payload, principal),
        update_membership(organization_id, membership_ids[1], payload, principal),
        return_exceptions=True,
    )
    failures = [result for result in results if isinstance(result, HTTPException)]
    assert len(failures) == 1
    assert len([result for result in results if not isinstance(result, BaseException)]) == 1
    assert failures[0].status_code == 409
    assert failures[0].detail == {"code": "last_owner_required"}

    async with SessionFactory() as session:
        owner_count = await session.scalar(
            select(func.count())
            .select_from(models.OrganizationMembership)
            .where(
                models.OrganizationMembership.organization_id == organization_id,
                models.OrganizationMembership.role == "owner",
                models.OrganizationMembership.status == "active",
            )
        )
    assert owner_count == 1
