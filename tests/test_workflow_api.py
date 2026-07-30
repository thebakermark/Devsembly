from __future__ import annotations

from httpx import ASGITransport, AsyncClient

from devsembly.api import app
from devsembly.genesis_api import get_genesis_service
from devsembly.genesis_service import GenesisService
from devsembly.workflow_api import get_workflow_service
from devsembly.workflow_service import WorkflowService
from tests.genesis_fakes import MemoryUnitOfWorkFactory


async def _create_project(client: AsyncClient, organizations_path: str) -> tuple[str, str, str]:
    organization = (await client.post(organizations_path, json={"name": "Devsembly"})).json()
    initiative = (
        await client.post(
            f"{organizations_path}/{organization['id']}/initiatives",
            json={"name": "Genesis", "objective": "Build the governed runtime."},
        )
    ).json()
    project = (
        await client.post(
            (f"{organizations_path}/{organization['id']}/initiatives/{initiative['id']}/projects"),
            json={"name": "Control Plane"},
        )
    ).json()
    return organization["id"], initiative["id"], project["id"]


async def test_workflow_run_api_lifecycle_idempotency_attempts_and_retry() -> None:
    factory = MemoryUnitOfWorkFactory()
    app.dependency_overrides[get_genesis_service] = lambda: GenesisService(factory)
    app.dependency_overrides[get_workflow_service] = lambda: WorkflowService(factory)
    organizations_path = "/api/v1/organizations"

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            organization_id, initiative_id, project_id = await _create_project(
                client, organizations_path
            )
            runs_path = (
                f"{organizations_path}/{organization_id}/initiatives/{initiative_id}"
                f"/projects/{project_id}/workflow-runs"
            )
            create_payload = {
                "workflow_kind": "software_change",
                "idempotency_key": "issue-22",
                "input_payload": {"issue_number": 22},
                "steps": [
                    {"key": "build", "name": "Build the change"},
                    {"key": "validate", "name": "Validate independently"},
                ],
            }

            created_response = await client.post(runs_path, json=create_payload)
            assert created_response.status_code == 201
            created = created_response.json()
            workflow_run_id = created["run"]["id"]
            first_step_id = created["steps"][0]["step"]["id"]
            second_step_id = created["steps"][1]["step"]["id"]
            assert created["run"]["status"] == "accepted"
            assert created["run"]["temporal_workflow_id"] is None
            assert [item["step"]["position"] for item in created["steps"]] == [0, 1]

            replay_response = await client.post(runs_path, json=create_payload)
            assert replay_response.status_code == 200
            assert replay_response.json()["run"]["id"] == workflow_run_id
            assert len(factory.store.workflow_runs) == 1

            conflict_payload = {**create_payload, "input_payload": {"issue_number": 23}}
            conflict = await client.post(runs_path, json=conflict_payload)
            assert conflict.status_code == 409
            assert conflict.json()["code"] == "idempotency_conflict"

            assert len((await client.get(runs_path)).json()) == 1
            inspected = (await client.get(f"{runs_path}/{workflow_run_id}")).json()
            assert inspected == created

            missing_provider_id = await client.put(
                f"{runs_path}/{workflow_run_id}/status",
                json={"expected_version": 1, "status": "queued"},
            )
            assert missing_provider_id.status_code == 409
            assert missing_provider_id.json()["code"] == "invalid_transition"

            queued = await client.put(
                f"{runs_path}/{workflow_run_id}/status",
                json={
                    "expected_version": 1,
                    "status": "queued",
                    "temporal_workflow_id": "genesis-issue-22",
                },
            )
            assert queued.status_code == 200
            assert queued.json()["run"]["version"] == 2

            stale = await client.put(
                f"{runs_path}/{workflow_run_id}/status",
                json={
                    "expected_version": 1,
                    "status": "running",
                },
            )
            assert stale.status_code == 409
            assert stale.json()["code"] == "stale_version"

            running = await client.put(
                f"{runs_path}/{workflow_run_id}/status",
                json={"expected_version": 2, "status": "running"},
            )
            assert running.status_code == 200
            assert running.json()["run"]["status"] == "running"
            assert running.json()["run"]["started_at"] is not None

            internal_base = (
                f"/api/v1/internal/organizations/{organization_id}"
                f"/initiatives/{initiative_id}/projects/{project_id}"
                f"/workflow-runs/{workflow_run_id}/steps"
            )
            first_attempt = await client.post(
                f"{internal_base}/{first_step_id}/attempts",
                json={
                    "expected_step_version": 1,
                    "status": "succeeded",
                    "result_payload": {"commit": "abc123"},
                },
            )
            assert first_attempt.status_code == 201
            assert first_attempt.json()["step"]["status"] == "succeeded"
            assert first_attempt.json()["attempts"][0]["attempt_number"] == 1

            failed_attempt = await client.post(
                f"{internal_base}/{second_step_id}/attempts",
                json={
                    "expected_step_version": 1,
                    "status": "failed",
                    "error_payload": {"code": "tests_failed"},
                },
            )
            assert failed_attempt.status_code == 201
            assert failed_attempt.json()["step"]["status"] == "failed"

            recovered_attempt = await client.post(
                f"{internal_base}/{second_step_id}/attempts",
                json={
                    "expected_step_version": 2,
                    "status": "succeeded",
                    "result_payload": {"tests": "passed"},
                },
            )
            assert recovered_attempt.status_code == 201
            assert len(recovered_attempt.json()["attempts"]) == 2
            assert recovered_attempt.json()["step"]["version"] == 3

            failed_run = await client.put(
                f"{runs_path}/{workflow_run_id}/status",
                json={"expected_version": 3, "status": "failed"},
            )
            assert failed_run.status_code == 200
            assert failed_run.json()["run"]["completed_at"] is not None

            retry_payload = {
                "expected_version": 4,
                "idempotency_key": "issue-22-retry-1",
            }
            retried_response = await client.post(
                f"{runs_path}/{workflow_run_id}/retry", json=retry_payload
            )
            assert retried_response.status_code == 201
            retried = retried_response.json()
            retried_run_id = retried["run"]["id"]
            assert retried["run"]["retry_of_run_id"] == workflow_run_id
            assert retried["run"]["status"] == "accepted"
            assert all(not item["attempts"] for item in retried["steps"])

            retry_replay = await client.post(
                f"{runs_path}/{workflow_run_id}/retry", json=retry_payload
            )
            assert retry_replay.status_code == 200
            assert retry_replay.json()["run"]["id"] == retried_run_id

            cancellation = await client.post(
                f"{runs_path}/{retried_run_id}/cancel",
                json={"expected_version": 1},
            )
            assert cancellation.status_code == 200
            assert cancellation.json()["run"]["status"] == "cancellation_requested"

            cancelled = await client.put(
                f"{runs_path}/{retried_run_id}/status",
                json={"expected_version": 2, "status": "cancelled"},
            )
            assert cancelled.status_code == 200
            assert cancelled.json()["run"]["status"] == "cancelled"

            other_organization = (
                await client.post(organizations_path, json={"name": "Other"})
            ).json()
            cross_scope = await client.get(
                f"{organizations_path}/{other_organization['id']}"
                f"/initiatives/{initiative_id}/projects/{project_id}"
                f"/workflow-runs/{workflow_run_id}"
            )
            assert cross_scope.status_code == 404
    finally:
        app.dependency_overrides.clear()

    topics = [event.topic for event in factory.store.outbox]
    assert topics.count("genesis.workflow_run.created") == 1
    assert topics.count("genesis.workflow_run.retry_created") == 1
    assert topics.count("genesis.workflow_step.attempt_recorded") == 3


async def test_workflow_run_api_validation_and_terminal_guards() -> None:
    factory = MemoryUnitOfWorkFactory()
    app.dependency_overrides[get_genesis_service] = lambda: GenesisService(factory)
    app.dependency_overrides[get_workflow_service] = lambda: WorkflowService(factory)
    organizations_path = "/api/v1/organizations"

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            organization_id, initiative_id, project_id = await _create_project(
                client, organizations_path
            )
            runs_path = (
                f"{organizations_path}/{organization_id}/initiatives/{initiative_id}"
                f"/projects/{project_id}/workflow-runs"
            )
            duplicate_steps = await client.post(
                runs_path,
                json={
                    "workflow_kind": "test",
                    "idempotency_key": "duplicate-steps",
                    "steps": [
                        {"key": "same", "name": "First"},
                        {"key": "same", "name": "Second"},
                    ],
                },
            )
            assert duplicate_steps.status_code == 422

            created = (
                await client.post(
                    runs_path,
                    json={
                        "workflow_kind": "test",
                        "idempotency_key": "terminal-guard",
                        "steps": [{"key": "one", "name": "One"}],
                    },
                )
            ).json()
            workflow_run_id = created["run"]["id"]
            early_retry = await client.post(
                f"{runs_path}/{workflow_run_id}/retry",
                json={"expected_version": 1, "idempotency_key": "too-early"},
            )
            assert early_retry.status_code == 409
            assert early_retry.json()["code"] == "invalid_transition"

            direct_cancellation_state = await client.put(
                f"{runs_path}/{workflow_run_id}/status",
                json={"expected_version": 1, "status": "cancellation_requested"},
            )
            assert direct_cancellation_state.status_code == 422

            queued = await client.put(
                f"{runs_path}/{workflow_run_id}/status",
                json={
                    "expected_version": 1,
                    "status": "queued",
                    "temporal_workflow_id": "terminal-guard",
                },
            )
            assert queued.status_code == 200
            running = await client.put(
                f"{runs_path}/{workflow_run_id}/status",
                json={"expected_version": 2, "status": "running"},
            )
            assert running.status_code == 200
            unfinished_success = await client.put(
                f"{runs_path}/{workflow_run_id}/status",
                json={"expected_version": 3, "status": "succeeded"},
            )
            assert unfinished_success.status_code == 409
            assert unfinished_success.json()["resource"] == "workflow run steps"

            second_run = (
                await client.post(
                    runs_path,
                    json={
                        "workflow_kind": "test",
                        "idempotency_key": "provider-id-conflict",
                        "steps": [{"key": "one", "name": "One"}],
                    },
                )
            ).json()
            provider_id_conflict = await client.put(
                f"{runs_path}/{second_run['run']['id']}/status",
                json={
                    "expected_version": 1,
                    "status": "queued",
                    "temporal_workflow_id": "terminal-guard",
                },
            )
            assert provider_id_conflict.status_code == 409
            assert provider_id_conflict.json()["code"] == "duplicate_resource"

            invalid_attempt = await client.post(
                (
                    f"/api/v1/internal/organizations/{organization_id}"
                    f"/initiatives/{initiative_id}/projects/{project_id}"
                    f"/workflow-runs/{workflow_run_id}/steps/"
                    f"{created['steps'][0]['step']['id']}/attempts"
                ),
                json={
                    "expected_step_version": 1,
                    "status": "failed",
                },
            )
            assert invalid_attempt.status_code == 422

            naive_timestamp = await client.post(
                (
                    f"/api/v1/internal/organizations/{organization_id}"
                    f"/initiatives/{initiative_id}/projects/{project_id}"
                    f"/workflow-runs/{workflow_run_id}/steps/"
                    f"{created['steps'][0]['step']['id']}/attempts"
                ),
                json={
                    "expected_step_version": 1,
                    "status": "succeeded",
                    "result_payload": {},
                    "started_at": "2026-07-30T12:00:00",
                },
            )
            assert naive_timestamp.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_openapi_exposes_persisted_workflow_operations_and_no_direct_start() -> None:
    paths = app.openapi()["paths"]
    base = (
        "/api/v1/organizations/{organization_id}/initiatives/{initiative_id}"
        "/projects/{project_id}/workflow-runs"
    )

    assert {"get", "post"}.issubset(paths[base])
    assert "get" in paths[f"{base}/{{workflow_run_id}}"]
    assert "put" in paths[f"{base}/{{workflow_run_id}}/status"]
    assert "post" in paths[f"{base}/{{workflow_run_id}}/cancel"]
    assert "post" in paths[f"{base}/{{workflow_run_id}}/retry"]
    assert (
        "post"
        in paths[
            (
                "/api/v1/internal/organizations/{organization_id}"
                "/initiatives/{initiative_id}/projects/{project_id}"
                "/workflow-runs/{workflow_run_id}/steps/{workflow_step_id}/attempts"
            )
        ]
    )
    assert "/runs" not in paths
