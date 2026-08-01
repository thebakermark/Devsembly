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


def _item(
    stable_id: str,
    title: str,
    *,
    parent_id: str | None = None,
    aliases: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    item: dict[str, object] = {
        "id": stable_id,
        "title": title,
        "status": "active",
        "provenance": {
            "provider": "github",
            "kind": "issue",
            "external_id": stable_id.rsplit(":", maxsplit=1)[-1],
            "uri": f"https://github.com/thebakermark/Devsembly/issues/{stable_id[-2:]}",
            "observed_at": "2026-07-31T00:00:00Z",
        },
        "confidence": {
            "score": 1,
            "status": "verified",
            "explanation": "Observed from authenticated GitHub state.",
        },
        "aliases": aliases or [],
    }
    if parent_id is not None:
        item["parent_id"] = parent_id
    return item


def _projected_payload() -> dict[str, object]:
    payload = _payload(0, "github:pie:projection:1")
    payload["state"] = {
        "planning": {
            "milestones": [_item("milestone:pie", "PIE foundation")],
            "epics": [_item("epic:pie", "Project Intelligence", parent_id="milestone:pie")],
            "features": [],
            "tasks": [
                _item(
                    "task:25",
                    "Work item projections",
                    parent_id="epic:pie",
                    aliases=[
                        {
                            "provider": "github",
                            "account": "thebakermark/Devsembly",
                            "kind": "issue",
                            "external_id": "25",
                            "uri": "https://github.com/thebakermark/Devsembly/issues/25",
                        }
                    ],
                )
            ],
            "roadmap": [],
            "current_sprint": None,
        },
        "graphs": {
            "capabilities": {
                "nodes": [
                    {**_item("capability:pie", "Project intelligence"), "kind": "capability"},
                    {**_item("component:pie-api", "PIE API"), "kind": "component"},
                ],
                "edges": [
                    {
                        "id": "edge:pie-implements-api",
                        "from": "capability:pie",
                        "to": "component:pie-api",
                        "type": "implements",
                        "provenance": _item("source:x", "source")["provenance"],
                        "confidence": _item("source:x", "source")["confidence"],
                    }
                ],
            },
            "dependencies": {"nodes": [], "edges": []},
        },
        "validation": {
            "status": "partial",
            "results": [
                {
                    **_item("validation:unit", "Unit tests"),
                    "status": "passed",
                    "evidence_ids": ["evidence:test-run-1"],
                    "acceptance_criterion_ids": ["criterion:27-1"],
                    "affected_capability_ids": ["capability:pie"],
                },
                {
                    **_item("validation:security", "Security review"),
                    "status": "unverified",
                    "evidence_ids": [],
                    "acceptance_criterion_ids": ["criterion:27-5"],
                    "affected_capability_ids": ["capability:pie"],
                    "stale_at": "2026-08-01T00:00:00Z",
                },
            ],
        },
        "risks": [
            {
                **_item("risk:stale-evidence", "Stale assurance"),
                "owner_id": "principal:owner",
                "likelihood": 0.5,
                "impact": 0.8,
                "mitigation": "Re-run required gates.",
                "trigger": "Evidence expires.",
                "affected_capability_ids": ["capability:pie"],
                "affected_dependency_ids": [],
            }
        ],
        "technical_debt": [
            {
                **_item("debt:manual-evidence", "Manual evidence mapping"),
                "owner_id": "principal:owner",
                "principal": 3,
                "interest": 0.5,
                "impact": "Slower assurance updates.",
                "retirement_criteria": "Automated evidence mapping is validated.",
                "affected_capability_ids": ["capability:pie"],
                "affected_dependency_ids": [],
            }
        ],
    }
    return payload


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


async def test_project_state_builds_readable_rebuildable_work_and_graph_projections() -> None:
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
            created = await client.post(f"{path}/revisions", json=_projected_payload())
            assert created.status_code == 201, created.text

            work_items = (await client.get(f"{path}/work-items")).json()
            assert [item["id"] for item in work_items] == [
                "milestone:pie",
                "epic:pie",
                "task:25",
            ]
            assert work_items[1]["parent_id"] == "milestone:pie"
            assert work_items[2]["aliases"][0]["external_id"] == "25"

            graph = (await client.get(f"{path}/graphs/capability")).json()
            assert graph["source_version"] == 1
            assert {node["id"] for node in graph["nodes"]} == {
                "capability:pie",
                "component:pie-api",
            }
            assert graph["edges"][0]["relationship"] == "implements"

            assurance = (await client.get(f"{path}/assurance")).json()
            assert assurance["verified_claims"] == 1
            assert assurance["unverified_claims"] == 1
            assert assurance["open_risks"] == 1
            assert assurance["debt_principal"] == "3"
            assert (await client.get(f"{path}/risks")).json()[0]["owner_id"] == "principal:owner"

            factory.store.project_intelligence_projections.clear()
            assert (await client.get(f"{path}/projection")).status_code == 404
            rebuilt = await client.post(f"{path}/projection/rebuild", json={"version": 1})
            assert rebuilt.status_code == 200
            assert rebuilt.json()["source_version"] == 1
            assert len(rebuilt.json()["work_items"]) == 3

            replacement = _payload(1, "github:pie:projection:2")
            assert (await client.post(f"{path}/revisions", json=replacement)).status_code == 201
            assert (await client.get(f"{path}/work-items")).json() == []
            stale_rebuild = await client.post(f"{path}/projection/rebuild", json={"version": 1})
            assert stale_rebuild.status_code == 409
    finally:
        app.dependency_overrides.clear()

    assert any(
        event.topic == "genesis.project-intelligence.projection-rebuilt"
        for event in factory.store.outbox
    )


async def test_projection_rejects_cycles_unknown_endpoints_and_duplicate_aliases() -> None:
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
                f"/projects/{project_id}/project-intelligence/revisions"
            )

            cyclic = _projected_payload()
            planning = cyclic["state"]["planning"]  # type: ignore[index]
            planning["milestones"][0]["parent_id"] = "epic:pie"  # type: ignore[index]
            response = await client.post(path, json=cyclic)
            assert response.status_code == 422
            assert "cannot have" in response.json()["detail"]

            unknown = _projected_payload()
            graphs = unknown["state"]["graphs"]  # type: ignore[index]
            graphs["capabilities"]["edges"][0]["to"] = "component:other-project"  # type: ignore[index]
            response = await client.post(path, json=unknown)
            assert response.status_code == 422
            assert "cross-project endpoint" in response.json()["detail"]

            duplicate = _projected_payload()
            planning = duplicate["state"]["planning"]  # type: ignore[index]
            planning["tasks"].append(  # type: ignore[index]
                _item(
                    "task:26",
                    "GitHub sync",
                    parent_id="epic:pie",
                    aliases=[
                        {
                            "provider": "github",
                            "account": "thebakermark/Devsembly",
                            "kind": "issue",
                            "external_id": "25",
                        }
                    ],
                )
            )
            response = await client.post(path, json=duplicate)
            assert response.status_code == 422
            assert "aliases must be unique" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()

    assert factory.store.project_state_revisions == {}


def test_openapi_exposes_project_intelligence_state_contract() -> None:
    paths = app.openapi()["paths"]
    prefix = (
        "/api/v1/organizations/{organization_id}/initiatives/{initiative_id}"
        "/projects/{project_id}/project-intelligence"
    )
    assert "get" in paths[f"{prefix}/state"]
    assert {"get", "post"}.issubset(paths[f"{prefix}/revisions"])
    assert "get" in paths[f"{prefix}/revisions/{{version}}"]
    assert "get" in paths[f"{prefix}/projection"]
    assert "post" in paths[f"{prefix}/projection/rebuild"]
    assert "get" in paths[f"{prefix}/work-items"]
    assert "get" in paths[f"{prefix}/graphs/{{graph_kind}}"]
    assert "get" in paths[f"{prefix}/assurance"]
    assert "get" in paths[f"{prefix}/validation-results"]
    assert "get" in paths[f"{prefix}/risks"]
    assert "get" in paths[f"{prefix}/technical-debt"]


async def test_verified_validation_requires_evidence_and_impacts_are_project_scoped() -> None:
    factory = MemoryUnitOfWorkFactory()
    app.dependency_overrides[get_genesis_service] = lambda: GenesisService(factory)
    app.dependency_overrides[get_project_intelligence_service] = lambda: ProjectIntelligenceService(
        factory
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            organization_id, initiative_id, project_id = await _project(client)
            path = f"/api/v1/organizations/{organization_id}/initiatives/{initiative_id}/projects/{project_id}/project-intelligence/revisions"
            payload = _projected_payload()
            payload["state"]["validation"]["results"][0]["evidence_ids"] = []  # type: ignore[index]
            response = await client.post(path, json=payload)
            assert response.status_code == 422
            assert "must be unverified" in response.json()["detail"]

            payload = _projected_payload()
            payload["state"]["risks"][0]["affected_capability_ids"] = ["capability:other-tenant"]  # type: ignore[index]
            response = await client.post(path, json=payload)
            assert response.status_code == 422
            assert "unknown capability" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
