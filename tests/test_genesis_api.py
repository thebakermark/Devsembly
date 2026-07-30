from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from devsembly.api import app
from devsembly.genesis_api import get_genesis_service
from devsembly.genesis_service import GenesisService
from tests.genesis_fakes import MemoryUnitOfWorkFactory


async def test_genesis_api_full_hierarchy_and_conflicts() -> None:
    factory = MemoryUnitOfWorkFactory()
    app.dependency_overrides[get_genesis_service] = lambda: GenesisService(factory)
    organizations_path = "/api/v1/organizations"

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            organization_response = await client.post(
                organizations_path, json={"name": "  Devsembly Labs  "}
            )
            assert organization_response.status_code == 201
            organization = organization_response.json()
            assert organization["name"] == "Devsembly Labs"
            organization_id = organization["id"]

            initiative_response = await client.post(
                f"{organizations_path}/{organization_id}/initiatives",
                json={
                    "name": "Genesis",
                    "objective": "Deliver the reference implementation.",
                },
            )
            assert initiative_response.status_code == 201
            initiative = initiative_response.json()
            initiative_id = initiative["id"]
            assert initiative["status"] == "proposed"

            project_response = await client.post(
                (f"{organizations_path}/{organization_id}/initiatives/{initiative_id}/projects"),
                json={
                    "name": "Control Plane",
                    "repository": "  thebakermark/Devsembly  ",
                },
            )
            assert project_response.status_code == 201
            project = project_response.json()
            project_id = project["id"]
            assert project["repository"] == "thebakermark/Devsembly"

            budget_path = (
                f"{organizations_path}/{organization_id}/initiatives/{initiative_id}"
                f"/projects/{project_id}/budgets"
            )
            budget_response = await client.post(
                budget_path,
                json={"monthly_limit": "50.00", "currency": "usd"},
            )
            assert budget_response.status_code == 201
            budget = budget_response.json()
            assert budget["currency"] == "USD"
            assert budget["enforcement_mode"] == "warn"

            assert (await client.get(organizations_path)).json() == [organization]
            assert (
                await client.get(f"{organizations_path}/{organization_id}")
            ).json() == organization
            assert (
                await client.get(f"{organizations_path}/{organization_id}/initiatives")
            ).json() == [initiative]
            assert (
                await client.get(
                    f"{organizations_path}/{organization_id}/initiatives/{initiative_id}"
                )
            ).json() == initiative
            assert (
                await client.get(
                    f"{organizations_path}/{organization_id}/initiatives/{initiative_id}/projects"
                )
            ).json() == [project]
            project_path = (
                f"{organizations_path}/{organization_id}/initiatives/{initiative_id}"
                f"/projects/{project_id}"
            )
            assert (await client.get(project_path)).json() == project
            assert (await client.get(budget_path)).json() == [budget]
            assert (await client.get(f"{budget_path}/{budget['id']}")).json() == budget

            initiative_update = await client.put(
                f"{organizations_path}/{organization_id}/initiatives/{initiative_id}",
                json={
                    "expected_version": 1,
                    "name": "Genesis v0.1",
                    "objective": "Ship the governed foundation.",
                    "status": "active",
                },
            )
            assert initiative_update.status_code == 200
            assert initiative_update.json()["version"] == 2
            assert initiative_update.json()["status"] == "active"

            project_update = await client.put(
                project_path,
                json={
                    "expected_version": 1,
                    "name": "Genesis Control Plane",
                    "repository": "thebakermark/Devsembly",
                    "status": "active",
                },
            )
            assert project_update.status_code == 200
            assert project_update.json()["version"] == 2

            budget_update = await client.put(
                f"{budget_path}/{budget['id']}",
                json={
                    "expected_version": 1,
                    "monthly_limit": "75.00",
                    "currency": "usd",
                    "enforcement_mode": "block",
                },
            )
            assert budget_update.status_code == 200
            assert budget_update.json()["version"] == 2
            assert budget_update.json()["enforcement_mode"] == "block"

            update_response = await client.put(
                f"{organizations_path}/{organization_id}",
                json={"expected_version": 1, "name": "Devsembly"},
            )
            assert update_response.status_code == 200
            assert update_response.json()["version"] == 2

            stale_response = await client.put(
                f"{organizations_path}/{organization_id}",
                json={"expected_version": 1, "name": "Stale update"},
            )
            assert stale_response.status_code == 409
            assert "reload" in stale_response.json()["detail"]

            duplicate_budget = await client.post(
                budget_path,
                json={"monthly_limit": "75.00"},
            )
            assert duplicate_budget.status_code == 409
    finally:
        app.dependency_overrides.clear()

    assert factory.store.commits == 8
    assert [event.topic for event in factory.store.outbox] == [
        "genesis.organization.created",
        "genesis.initiative.created",
        "genesis.project.created",
        "genesis.budget.created",
        "genesis.initiative.updated",
        "genesis.project.updated",
        "genesis.budget.updated",
        "genesis.organization.updated",
    ]


async def test_genesis_api_enforces_parent_scope_and_validation() -> None:
    factory = MemoryUnitOfWorkFactory()
    app.dependency_overrides[get_genesis_service] = lambda: GenesisService(factory)
    organizations_path = "/api/v1/organizations"

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            first = (await client.post(organizations_path, json={"name": "First"})).json()
            second = (await client.post(organizations_path, json={"name": "Second"})).json()
            initiative = (
                await client.post(
                    f"{organizations_path}/{first['id']}/initiatives",
                    json={"name": "Scoped", "objective": "Stay isolated."},
                )
            ).json()

            cross_scope = await client.get(
                f"{organizations_path}/{second['id']}/initiatives/{initiative['id']}"
            )
            assert cross_scope.status_code == 404

            invalid_budget = await client.post(
                (
                    f"{organizations_path}/{first['id']}/initiatives/{initiative['id']}"
                    "/projects/00000000-0000-0000-0000-000000000000/budgets"
                ),
                json={"monthly_limit": "0"},
            )
            assert invalid_budget.status_code == 422
            assert (await client.post(organizations_path, json={"name": "   "})).status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_openapi_exposes_all_genesis_resource_operations() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    expected = {
        "/api/v1/organizations": {"get", "post"},
        "/api/v1/organizations/{organization_id}": {"get", "put"},
        "/api/v1/organizations/{organization_id}/initiatives": {"get", "post"},
        "/api/v1/organizations/{organization_id}/initiatives/{initiative_id}": {
            "get",
            "put",
        },
        "/api/v1/organizations/{organization_id}/initiatives/{initiative_id}/projects": {
            "get",
            "post",
        },
        (
            "/api/v1/organizations/{organization_id}/initiatives/{initiative_id}"
            "/projects/{project_id}"
        ): {"get", "put"},
        (
            "/api/v1/organizations/{organization_id}/initiatives/{initiative_id}"
            "/projects/{project_id}/budgets"
        ): {"get", "post"},
        (
            "/api/v1/organizations/{organization_id}/initiatives/{initiative_id}"
            "/projects/{project_id}/budgets/{budget_id}"
        ): {"get", "put"},
    }

    for path, methods in expected.items():
        assert methods.issubset(paths[path])
