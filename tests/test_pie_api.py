from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from devsembly.api import app
from devsembly.genesis_api import get_genesis_service
from devsembly.genesis_service import GenesisService
from devsembly.pie_api import get_project_intelligence_service
from devsembly.pie_service import ProjectIntelligenceService
from tests.genesis_fakes import MemoryUnitOfWorkFactory


async def _project(client: AsyncClient) -> tuple[str, str, str]:
    organization = (await client.post("/api/v1/organizations", json={"name": "PIE Lab"})).json()
    organization_id = organization["id"]
    initiative = (
        await client.post(
            f"/api/v1/organizations/{organization_id}/initiatives",
            json={"name": "Genesis", "objective": "Establish shared project intelligence."},
        )
    ).json()
    initiative_id = initiative["id"]
    project = (
        await client.post(
            f"/api/v1/organizations/{organization_id}/initiatives/{initiative_id}/projects",
            json={"name": "Project Intelligence Engine", "repository": "thebakermark/Devsembly"},
        )
    ).json()
    return organization_id, initiative_id, project["id"]


def _payload(
    expected_version: int, idempotency_key: str, status: str = "active"
) -> dict[str, object]:
    return {
        "expected_version": expected_version,
        "idempotency_key": idempotency_key,
        "schema_version": "1.0",
        "state": {
            "project": {"id": "project:devsembly", "status": status},
            "work_items": [],
            "validation": {"status": "passed"},
        },
        "source": {
            "provider": "github",
            "kind": "pull_request",
            "event_id": f"pr-17-v{expected_version + 1}",
            "uri": "https://github.com/thebakermark/Devsembly/pull/17",
        },
        "assertion": {
            "status": "verified",
            "confidence": "1.0000",
            "explanation": "Observed from the authenticated GitHub pull request and CI result.",
        },
    }


async def test_project_state_reconcile_is_versioned_idempotent_and_audited() -> None:
    factory = MemoryUnitOfWorkFactory()
    app.dependency_overrides[get_genesis_service] = lambda: GenesisService(factory)
    app.dependency_overrides[get_project_intelligence_service] = lambda: ProjectIntelligenceService(
        factory
    )

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            organization_id, initiative_id, project_id = await _project(client)
            path = (
                f"/api/v1/organizations/{organization_id}/initiatives/{initiative_id}"
                f"/projects/{project_id}/project-intelligence"
            )

            missing = await client.get(f"{path}/state")
            assert missing.status_code == 404

            first = await client.post(f"{path}/revisions", json=_payload(0, "github:pr:17:1"))
            assert first.status_code == 201
            assert first.json()["version"] == 1
            assert first.json()["parent_revision_id"] is None
            assert len(first.json()["state_sha256"]) == 64

            repeated = await client.post(f"{path}/revisions", json=_payload(0, "github:pr:17:1"))
            assert repeated.status_code == 201
            assert repeated.json()["id"] == first.json()["id"]

            conflicting = _payload(0, "github:pr:17:1", status="blocked")
            assert (await client.post(f"{path}/revisions", json=conflicting)).status_code == 409

            stale = await client.post(f"{path}/revisions", json=_payload(0, "github:pr:17:2"))
            assert stale.status_code == 409

            second = await client.post(f"{path}/revisions", json=_payload(1, "github:pr:17:2"))
            assert second.status_code == 201
            assert second.json()["version"] == 2
            assert second.json()["parent_revision_id"] == first.json()["id"]

            assert (await client.get(f"{path}/state")).json() == second.json()
            revisions = (await client.get(f"{path}/revisions")).json()
            assert [revision["version"] for revision in revisions] == [1, 2]
            assert (await client.get(f"{path}/revisions/1")).json() == first.json()
    finally:
        app.dependency_overrides.clear()

    assert [event.topic for event in factory.store.outbox[-2:]] == [
        "genesis.project-intelligence.state-reconciled",
        "genesis.project-intelligence.state-reconciled",
    ]
    assert len(factory.store.project_state_revisions) == 2


def test_openapi_exposes_project_intelligence_state_contract() -> None:
    paths = app.openapi()["paths"]
    prefix = (
        "/api/v1/organizations/{organization_id}/initiatives/{initiative_id}"
        "/projects/{project_id}/project-intelligence"
    )
    assert "get" in paths[f"{prefix}/state"]
    assert {"get", "post"}.issubset(paths[f"{prefix}/revisions"])
    assert "get" in paths[f"{prefix}/revisions/{{version}}"]
