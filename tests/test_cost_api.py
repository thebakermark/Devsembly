from __future__ import annotations

from typing import cast

from httpx import ASGITransport, AsyncClient

from devsembly.api import app
from devsembly.cost_api import get_cost_governance_service
from devsembly.cost_service import CostGovernanceService
from devsembly.genesis_api import get_genesis_service
from devsembly.genesis_service import GenesisService
from devsembly.workflow_api import get_workflow_service
from devsembly.workflow_service import WorkflowService
from tests.genesis_fakes import MemoryUnitOfWorkFactory

ORGANIZATIONS_PATH = "/api/v1/organizations"


async def _create_project(
    client: AsyncClient,
    *,
    organization_name: str = "Devsembly",
    project_name: str = "Control Plane",
    monthly_limit: str = "50.00",
    enforcement_mode: str = "warn",
) -> tuple[str, str, str, dict[str, object]]:
    organization = (await client.post(ORGANIZATIONS_PATH, json={"name": organization_name})).json()
    initiative = (
        await client.post(
            f"{ORGANIZATIONS_PATH}/{organization['id']}/initiatives",
            json={"name": "Genesis", "objective": "Govern cost and material decisions."},
        )
    ).json()
    project = (
        await client.post(
            f"{ORGANIZATIONS_PATH}/{organization['id']}/initiatives/{initiative['id']}/projects",
            json={"name": project_name},
        )
    ).json()
    budget = (
        await client.post(
            f"{ORGANIZATIONS_PATH}/{organization['id']}"
            f"/initiatives/{initiative['id']}/projects/{project['id']}/budgets",
            json={
                "monthly_limit": monthly_limit,
                "currency": "USD",
                "enforcement_mode": enforcement_mode,
            },
        )
    ).json()
    return organization["id"], initiative["id"], project["id"], budget


def _evaluation_payload(
    *,
    idempotency_key: str,
    selected_monthly: str = "80.00",
    workflow_run_id: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "idempotency_key": idempotency_key,
        "selected_option": {
            "key": "standard",
            "name": "Standard stack",
            "satisfies_acceptance_criteria": True,
            "line_items": [
                {
                    "category": "infrastructure",
                    "description": "Monthly services",
                    "cadence": "monthly",
                    "quantity": "2",
                    "unit_cost": str(float(selected_monthly) / 2),
                },
                {
                    "category": "setup",
                    "description": "Initial setup",
                    "cadence": "one_time",
                    "unit_cost": "10.00",
                },
            ],
        },
        "alternatives": [
            {
                "key": "lean",
                "name": "Lean stack",
                "satisfies_acceptance_criteria": True,
                "line_items": [
                    {
                        "category": "infrastructure",
                        "description": "Open-source services",
                        "cadence": "monthly",
                        "unit_cost": "40.00",
                    },
                    {
                        "category": "setup",
                        "description": "Lean setup",
                        "cadence": "one_time",
                        "unit_cost": "5.00",
                    },
                ],
            },
            {
                "key": "incomplete",
                "name": "Incomplete option",
                "satisfies_acceptance_criteria": False,
                "line_items": [
                    {
                        "category": "infrastructure",
                        "description": "Missing requirements",
                        "cadence": "monthly",
                        "unit_cost": "10.00",
                    }
                ],
            },
        ],
    }
    if workflow_run_id is not None:
        payload["workflow_run_id"] = workflow_run_id
    return payload


def _decision_payload(cost_evaluation_id: str) -> dict[str, object]:
    return {
        "cost_evaluation_id": cost_evaluation_id,
        "title": "Select the Genesis operating stack",
        "context": "Choose a stack while preserving the approved monthly budget.",
        "risk": "moderate",
        "confidence": "0.90",
        "rationale": "The selected option meets the functional acceptance criteria.",
    }


async def test_warn_evaluation_recommendation_decision_and_idempotency() -> None:
    factory = MemoryUnitOfWorkFactory()
    app.dependency_overrides[get_genesis_service] = lambda: GenesisService(factory)
    app.dependency_overrides[get_cost_governance_service] = lambda: CostGovernanceService(factory)

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            organization_id, initiative_id, project_id, _ = await _create_project(client)
            project_path = (
                f"{ORGANIZATIONS_PATH}/{organization_id}/initiatives/{initiative_id}"
                f"/projects/{project_id}"
            )
            evaluations_path = f"{project_path}/cost-evaluations"
            payload = _evaluation_payload(idempotency_key="issue-23")

            response = await client.post(evaluations_path, json=payload)
            assert response.status_code == 201
            evaluation = response.json()
            assert evaluation["outcome"] == "approval_required"
            assert evaluation["selected_option"]["one_time_cost"] == "10.0000"
            assert evaluation["selected_option"]["monthly_cost"] == "80.0000"
            assert evaluation["monthly_overage"] == "30.0000"
            assert evaluation["recommendation"]["option_key"] == "lean"
            assert evaluation["recommendation"]["monthly_savings"] == "40.0000"
            assert "50.00 monthly limit" in evaluation["recommendation"]["rationale"]

            replay = await client.post(evaluations_path, json=payload)
            assert replay.status_code == 200
            assert replay.json()["id"] == evaluation["id"]
            assert len(factory.store.cost_evaluations) == 1

            conflict_payload = _evaluation_payload(
                idempotency_key="issue-23",
                selected_monthly="82.00",
            )
            conflict = await client.post(evaluations_path, json=conflict_payload)
            assert conflict.status_code == 409
            assert conflict.json()["code"] == "idempotency_conflict"

            assert (await client.get(evaluations_path)).json() == [evaluation]
            assert (await client.get(f"{evaluations_path}/{evaluation['id']}")).json() == evaluation

            decisions_path = f"{project_path}/decisions"
            proposed_response = await client.post(
                decisions_path,
                json=_decision_payload(evaluation["id"]),
            )
            assert proposed_response.status_code == 201
            proposed = proposed_response.json()
            assert proposed["status"] == "proposed"
            assert proposed["selected_option"] == "standard"
            assert proposed["estimated_monthly_cost"] == "80.0000"
            assert proposed["decided_by"] is None

            approved_response = await client.post(
                f"{decisions_path}/{proposed['id']}/resolve",
                json={
                    "expected_version": 1,
                    "status": "approved",
                    "decided_by": "human:mark",
                    "decision_note": "Approve the overage for this bounded proof.",
                    "outcome": "Approved to proceed with human oversight.",
                },
            )
            assert approved_response.status_code == 200
            approved = approved_response.json()
            assert approved["status"] == "approved"
            assert approved["decided_by"] == "00000000-0000-4000-8000-000000000001"
            assert approved["version"] == 2
            assert approved["authorization_budget_version"] == 1
            assert approved["authorization_monthly_limit"] == "50.0000"

            stale = await client.post(
                f"{decisions_path}/{proposed['id']}/resolve",
                json={
                    "expected_version": 1,
                    "status": "rejected",
                    "decided_by": "human:mark",
                    "decision_note": "Stale reversal.",
                    "outcome": "No change.",
                },
            )
            assert stale.status_code == 409
            assert stale.json()["code"] == "stale_version"

            immutable = await client.post(
                f"{decisions_path}/{proposed['id']}/resolve",
                json={
                    "expected_version": 2,
                    "status": "rejected",
                    "decided_by": "human:mark",
                    "decision_note": "Attempted final-record rewrite.",
                    "outcome": "No change.",
                },
            )
            assert immutable.status_code == 409
            assert immutable.json()["code"] == "invalid_transition"
            assert (await client.get(decisions_path)).json() == [approved]
    finally:
        app.dependency_overrides.clear()

    topics = [event.topic for event in factory.store.outbox]
    assert topics.count("genesis.cost_evaluation.created") == 1
    assert topics.count("genesis.decision.proposed") == 1
    assert topics.count("genesis.decision.approved") == 1


async def test_blocked_approval_budget_revision_and_scope_guards() -> None:
    factory = MemoryUnitOfWorkFactory()
    app.dependency_overrides[get_genesis_service] = lambda: GenesisService(factory)
    app.dependency_overrides[get_workflow_service] = lambda: WorkflowService(factory)
    app.dependency_overrides[get_cost_governance_service] = lambda: CostGovernanceService(factory)

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            organization_id, initiative_id, project_id, budget = await _create_project(
                client,
                enforcement_mode="block",
            )
            project_path = (
                f"{ORGANIZATIONS_PATH}/{organization_id}/initiatives/{initiative_id}"
                f"/projects/{project_id}"
            )
            evaluations_path = f"{project_path}/cost-evaluations"
            evaluation = (
                await client.post(
                    evaluations_path,
                    json=_evaluation_payload(idempotency_key="blocked"),
                )
            ).json()
            assert evaluation["outcome"] == "blocked"

            decisions_path = f"{project_path}/decisions"
            proposed = (
                await client.post(
                    decisions_path,
                    json=_decision_payload(evaluation["id"]),
                )
            ).json()
            blocked = await client.post(
                f"{decisions_path}/{proposed['id']}/resolve",
                json={
                    "expected_version": 1,
                    "status": "approved",
                    "decided_by": "human:mark",
                    "decision_note": "Try to exceed the hard limit.",
                    "outcome": "Must remain blocked.",
                },
            )
            assert blocked.status_code == 409
            assert blocked.json()["resource"] == "cost evaluation"

            budget_update = await client.put(
                f"{project_path}/budgets/{budget['id']}",
                json={
                    "expected_version": 1,
                    "monthly_limit": "100.00",
                    "currency": "USD",
                    "enforcement_mode": "block",
                },
            )
            assert budget_update.status_code == 200
            approved = await client.post(
                f"{decisions_path}/{proposed['id']}/resolve",
                json={
                    "expected_version": 1,
                    "status": "approved",
                    "decided_by": "human:mark",
                    "decision_note": "Approve under the revised budget.",
                    "outcome": "Approved after budget revision.",
                },
            )
            assert approved.status_code == 200
            assert approved.json()["authorization_budget_version"] == 2
            assert approved.json()["authorization_monthly_limit"] == "100.0000"

            run = (
                await client.post(
                    f"{project_path}/workflow-runs",
                    json={
                        "workflow_kind": "cost_scope",
                        "idempotency_key": "workflow-for-first-project",
                        "steps": [{"key": "evaluate", "name": "Evaluate"}],
                    },
                )
            ).json()
            second_project = (
                await client.post(
                    f"{ORGANIZATIONS_PATH}/{organization_id}/initiatives/{initiative_id}/projects",
                    json={"name": "Second Project"},
                )
            ).json()
            second_path = (
                f"{ORGANIZATIONS_PATH}/{organization_id}/initiatives/{initiative_id}"
                f"/projects/{second_project['id']}"
            )
            await client.post(
                f"{second_path}/budgets",
                json={"monthly_limit": "50.00", "enforcement_mode": "warn"},
            )
            hardened_evaluation = (
                await client.post(
                    f"{second_path}/cost-evaluations",
                    json=_evaluation_payload(idempotency_key="hardened-after-evaluation"),
                )
            ).json()
            hardened_decision = (
                await client.post(
                    f"{second_path}/decisions",
                    json=_decision_payload(hardened_evaluation["id"]),
                )
            ).json()
            second_budget = (await client.get(f"{second_path}/budgets")).json()[0]
            await client.put(
                f"{second_path}/budgets/{second_budget['id']}",
                json={
                    "expected_version": 1,
                    "monthly_limit": "50.00",
                    "currency": "USD",
                    "enforcement_mode": "block",
                },
            )
            hardened_approval = await client.post(
                f"{second_path}/decisions/{hardened_decision['id']}/resolve",
                json={
                    "expected_version": 1,
                    "status": "approved",
                    "decided_by": "human:mark",
                    "decision_note": "Try an approval after the budget hardened.",
                    "outcome": "Must be blocked by the current policy.",
                },
            )
            assert hardened_approval.status_code == 409
            assert hardened_approval.json()["resource"] == "project budget"

            cross_workflow = await client.post(
                f"{second_path}/cost-evaluations",
                json=_evaluation_payload(
                    idempotency_key="wrong-workflow-scope",
                    workflow_run_id=run["run"]["id"],
                ),
            )
            assert cross_workflow.status_code == 404
            assert cross_workflow.json()["resource"] == "workflow run"

            other_organization = (
                await client.post(ORGANIZATIONS_PATH, json={"name": "Other"})
            ).json()
            cross_organization = await client.get(
                f"{ORGANIZATIONS_PATH}/{other_organization['id']}"
                f"/initiatives/{initiative_id}/projects/{project_id}"
                f"/cost-evaluations/{evaluation['id']}"
            )
            assert cross_organization.status_code == 404
    finally:
        app.dependency_overrides.clear()


async def test_observe_mode_direct_decision_validation_and_openapi() -> None:
    factory = MemoryUnitOfWorkFactory()
    app.dependency_overrides[get_genesis_service] = lambda: GenesisService(factory)
    app.dependency_overrides[get_cost_governance_service] = lambda: CostGovernanceService(factory)

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            organization_id, initiative_id, project_id, _ = await _create_project(
                client,
                enforcement_mode="observe",
            )
            project_path = (
                f"{ORGANIZATIONS_PATH}/{organization_id}/initiatives/{initiative_id}"
                f"/projects/{project_id}"
            )
            evaluation = await client.post(
                f"{project_path}/cost-evaluations",
                json=_evaluation_payload(idempotency_key="observed"),
            )
            assert evaluation.status_code == 201
            assert evaluation.json()["outcome"] == "observed_overage"

            noncompliant_payload = _evaluation_payload(idempotency_key="noncompliant")
            selected_option = cast(dict[str, object], noncompliant_payload["selected_option"])
            selected_option["satisfies_acceptance_criteria"] = False
            noncompliant_evaluation = (
                await client.post(
                    f"{project_path}/cost-evaluations",
                    json=noncompliant_payload,
                )
            ).json()
            noncompliant_decision = (
                await client.post(
                    f"{project_path}/decisions",
                    json=_decision_payload(noncompliant_evaluation["id"]),
                )
            ).json()
            noncompliant_approval = await client.post(
                f"{project_path}/decisions/{noncompliant_decision['id']}/resolve",
                json={
                    "expected_version": 1,
                    "status": "approved",
                    "decided_by": "human:mark",
                    "decision_note": "Try a functionally incomplete option.",
                    "outcome": "Must not be approved.",
                },
            )
            assert noncompliant_approval.status_code == 409
            assert noncompliant_approval.json()["resource"] == "cost evaluation acceptance"

            duplicate_options = _evaluation_payload(idempotency_key="duplicates")
            duplicate_alternatives = cast(
                list[dict[str, object]], duplicate_options["alternatives"]
            )
            duplicate_alternatives[0]["key"] = "standard"
            assert (
                await client.post(
                    f"{project_path}/cost-evaluations",
                    json=duplicate_options,
                )
            ).status_code == 422

            decisions_path = f"{project_path}/decisions"
            incomplete_direct = await client.post(
                decisions_path,
                json={
                    "title": "Incomplete",
                    "context": "No explicit costs.",
                    "selected_option": "manual",
                    "risk": "low",
                    "confidence": "0.8",
                    "rationale": "Test validation.",
                },
            )
            assert incomplete_direct.status_code == 422

            direct = await client.post(
                decisions_path,
                json={
                    "title": "Record a non-cost-model choice",
                    "context": "Preserve a material choice without a linked evaluation.",
                    "selected_option": "manual-review",
                    "alternatives": [{"key": "automatic", "description": "Automate immediately."}],
                    "currency": "USD",
                    "estimated_one_time_cost": "2.50",
                    "estimated_monthly_cost": "0",
                    "risk": "low",
                    "confidence": "0.75",
                    "rationale": "Manual review preserves human authority.",
                },
            )
            assert direct.status_code == 201
            rejected = await client.post(
                f"{decisions_path}/{direct.json()['id']}/resolve",
                json={
                    "expected_version": 1,
                    "status": "rejected",
                    "decided_by": "human:mark",
                    "decision_note": "Do not proceed.",
                    "outcome": "Rejected and retained for provenance.",
                },
            )
            assert rejected.status_code == 200
            assert rejected.json()["status"] == "rejected"
            assert rejected.json()["authorization_budget_version"] is None
    finally:
        app.dependency_overrides.clear()

    paths = app.openapi()["paths"]
    cost_path = (
        "/api/v1/organizations/{organization_id}/initiatives/{initiative_id}"
        "/projects/{project_id}/cost-evaluations"
    )
    decision_path = (
        "/api/v1/organizations/{organization_id}/initiatives/{initiative_id}"
        "/projects/{project_id}/decisions"
    )
    assert {"get", "post"}.issubset(paths[cost_path])
    assert {"get", "post"}.issubset(paths[decision_path])
