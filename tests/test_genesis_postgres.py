from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from devsembly import models
from devsembly.cost_service import CostGovernanceService
from devsembly.domain import (
    BudgetEnforcementMode,
    CostCadence,
    CostEvaluationOutcome,
    CostLineItem,
    CostOptionDefinition,
    DecisionRisk,
    DecisionStatus,
    InitiativeStatus,
    Organization,
    OutboxMessage,
    ProjectStatus,
    WorkflowAttemptStatus,
    WorkflowRunStatus,
    WorkflowStepDefinition,
)
from devsembly.errors import (
    DuplicateResourceError,
    IdempotencyConflictError,
    InvalidTransitionError,
    ResourceNotFoundError,
    StaleVersionError,
)
from devsembly.genesis_service import GenesisService
from devsembly.unit_of_work import SqlAlchemyUnitOfWork
from devsembly.workflow_service import WorkflowService

TEST_DATABASE_URL = os.getenv("DEVSEMBLY_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="DEVSEMBLY_TEST_DATABASE_URL is required for PostgreSQL integration tests",
)


@pytest.fixture
async def postgres_factory() -> async_sessionmaker[AsyncSession]:
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE outbox_events, audit_events, workflow_step_attempts, "
                "workflow_steps, workflow_runs, decisions, cost_evaluations, "
                "authorization_delegations, organization_memberships, external_identities, "
                "principals, budgets, projects, initiatives, organizations CASCADE"
            )
        )
    try:
        yield factory
    finally:
        await engine.dispose()


async def test_sqlalchemy_repositories_scope_events_and_concurrency(
    postgres_factory: async_sessionmaker[AsyncSession],
) -> None:
    service = GenesisService(lambda: SqlAlchemyUnitOfWork(postgres_factory))

    organization = await service.create_organization("Devsembly")
    initiative = await service.create_initiative(
        organization.id,
        name="Genesis",
        objective="Deliver Genesis v0.1.",
        status=InitiativeStatus.ACTIVE,
    )
    project = await service.create_project(
        organization.id,
        initiative.id,
        name="Control Plane",
        repository="thebakermark/Devsembly",
        status=ProjectStatus.ACTIVE,
    )
    budget = await service.create_budget(
        organization.id,
        initiative.id,
        project.id,
        monthly_limit=Decimal("50.00"),
        currency="USD",
        enforcement_mode=BudgetEnforcementMode.WARN,
    )

    assert budget.monthly_limit == Decimal("50.00")
    assert len(await service.list_budgets(organization.id, initiative.id, project.id)) == 1

    updated = await service.update_budget(
        organization.id,
        initiative.id,
        project.id,
        budget.id,
        1,
        monthly_limit=Decimal("75.00"),
        currency="USD",
        enforcement_mode=BudgetEnforcementMode.BLOCK,
    )
    assert updated.version == 2
    assert updated.enforcement_mode is BudgetEnforcementMode.BLOCK

    with pytest.raises(StaleVersionError):
        await service.update_budget(
            organization.id,
            initiative.id,
            project.id,
            budget.id,
            1,
            monthly_limit=Decimal("80.00"),
            currency="USD",
            enforcement_mode=BudgetEnforcementMode.WARN,
        )

    other_organization = await service.create_organization("Other")
    with pytest.raises(ResourceNotFoundError):
        await service.get_project(other_organization.id, initiative.id, project.id)

    with pytest.raises(DuplicateResourceError):
        await service.create_budget(
            organization.id,
            initiative.id,
            project.id,
            monthly_limit=Decimal("100.00"),
            currency="USD",
            enforcement_mode=BudgetEnforcementMode.OBSERVE,
        )

    async with postgres_factory() as session:
        event_count = await session.scalar(select(func.count()).select_from(models.OutboxEvent))
    assert event_count == 6


async def test_unit_of_work_rolls_back_domain_and_outbox_together(
    postgres_factory: async_sessionmaker[AsyncSession],
) -> None:
    now = datetime.now(UTC)
    organization_id = uuid.uuid4()
    organization = Organization(
        id=organization_id,
        name="Rolled Back",
        version=1,
        created_at=now,
        updated_at=now,
    )
    event = OutboxMessage(
        id=uuid.uuid4(),
        occurred_at=now,
        topic="genesis.organization.created",
        aggregate_id=str(organization_id),
        payload={"organization_id": str(organization_id), "version": 1},
    )

    async with SqlAlchemyUnitOfWork(postgres_factory) as unit:
        await unit.organizations.add(organization)
        await unit.outbox.add(event)

    async with postgres_factory() as session:
        stored_organization = await session.get(models.Organization, organization_id)
        stored_event = await session.get(models.OutboxEvent, event.id)
        audit_count = await session.scalar(select(func.count()).select_from(models.AuditEvent))
    assert stored_organization is None
    assert stored_event is None
    assert audit_count == 0


async def test_workflow_repositories_persist_scope_idempotency_attempts_and_retry(
    postgres_factory: async_sessionmaker[AsyncSession],
) -> None:
    factory = lambda: SqlAlchemyUnitOfWork(postgres_factory)
    genesis = GenesisService(factory)
    workflows = WorkflowService(factory)
    organization = await genesis.create_organization("Devsembly")
    initiative = await genesis.create_initiative(
        organization.id,
        name="Genesis",
        objective="Persist workflow intent.",
        status=InitiativeStatus.ACTIVE,
    )
    project = await genesis.create_project(
        organization.id,
        initiative.id,
        name="Control Plane",
        repository="thebakermark/Devsembly",
        status=ProjectStatus.ACTIVE,
    )
    definitions = (
        WorkflowStepDefinition(key="build", name="Build"),
        WorkflowStepDefinition(key="validate", name="Validate"),
    )

    created, was_created = await workflows.create_workflow_run(
        organization.id,
        initiative.id,
        project.id,
        workflow_kind="software_change",
        idempotency_key="postgres-issue-22",
        input_payload={"issue_number": 22},
        steps=definitions,
    )
    replay, replay_created = await workflows.create_workflow_run(
        organization.id,
        initiative.id,
        project.id,
        workflow_kind="software_change",
        idempotency_key="postgres-issue-22",
        input_payload={"issue_number": 22},
        steps=definitions,
    )
    assert was_created is True
    assert replay_created is False
    assert replay.run.id == created.run.id

    with pytest.raises(IdempotencyConflictError):
        await workflows.create_workflow_run(
            organization.id,
            initiative.id,
            project.id,
            workflow_kind="software_change",
            idempotency_key="postgres-issue-22",
            input_payload={"issue_number": 23},
            steps=definitions,
        )

    queued = await workflows.update_workflow_run_status(
        organization.id,
        initiative.id,
        project.id,
        created.run.id,
        1,
        target_status=WorkflowRunStatus.QUEUED,
        temporal_workflow_id="postgres-workflow-22",
    )
    conflicting_run, _ = await workflows.create_workflow_run(
        organization.id,
        initiative.id,
        project.id,
        workflow_kind="software_change",
        idempotency_key="postgres-provider-conflict",
        input_payload={"issue_number": 22},
        steps=definitions,
    )
    with pytest.raises(DuplicateResourceError):
        await workflows.update_workflow_run_status(
            organization.id,
            initiative.id,
            project.id,
            conflicting_run.run.id,
            1,
            target_status=WorkflowRunStatus.QUEUED,
            temporal_workflow_id="postgres-workflow-22",
        )
    running = await workflows.update_workflow_run_status(
        organization.id,
        initiative.id,
        project.id,
        created.run.id,
        queued.run.version,
        target_status=WorkflowRunStatus.RUNNING,
        temporal_workflow_id=None,
    )
    first_step = running.steps[0].step
    failed_step = await workflows.record_workflow_step_attempt(
        organization.id,
        initiative.id,
        project.id,
        created.run.id,
        first_step.id,
        first_step.version,
        status=WorkflowAttemptStatus.FAILED,
        result_payload=None,
        error_payload={"code": "build_failed"},
        started_at=None,
    )
    recovered_step = await workflows.record_workflow_step_attempt(
        organization.id,
        initiative.id,
        project.id,
        created.run.id,
        first_step.id,
        failed_step.step.version,
        status=WorkflowAttemptStatus.SUCCEEDED,
        result_payload={"commit": "abc123"},
        error_payload=None,
        started_at=None,
    )
    assert [attempt.attempt_number for attempt in recovered_step.attempts] == [1, 2]

    with pytest.raises(StaleVersionError):
        await workflows.update_workflow_run_status(
            organization.id,
            initiative.id,
            project.id,
            created.run.id,
            1,
            target_status=WorkflowRunStatus.FAILED,
            temporal_workflow_id=None,
        )

    failed_run = await workflows.update_workflow_run_status(
        organization.id,
        initiative.id,
        project.id,
        created.run.id,
        running.run.version,
        target_status=WorkflowRunStatus.FAILED,
        temporal_workflow_id=None,
    )
    retry, retry_created = await workflows.retry_workflow_run(
        organization.id,
        initiative.id,
        project.id,
        created.run.id,
        failed_run.run.version,
        idempotency_key="postgres-issue-22-retry",
    )
    assert retry_created is True
    assert retry.run.retry_of_run_id == created.run.id
    assert len(retry.steps) == 2
    assert all(not item.attempts for item in retry.steps)

    other_organization = await genesis.create_organization("Other")
    with pytest.raises(ResourceNotFoundError):
        await workflows.get_workflow_run(
            other_organization.id,
            initiative.id,
            project.id,
            created.run.id,
        )

    async with postgres_factory() as session:
        run_count = await session.scalar(select(func.count()).select_from(models.WorkflowRun))
        step_count = await session.scalar(select(func.count()).select_from(models.WorkflowStep))
        attempt_count = await session.scalar(
            select(func.count()).select_from(models.WorkflowStepAttempt)
        )
        workflow_event_count = await session.scalar(
            select(func.count())
            .select_from(models.OutboxEvent)
            .where(models.OutboxEvent.topic.like("genesis.workflow%"))
        )
    assert run_count == 3
    assert step_count == 6
    assert attempt_count == 2
    assert workflow_event_count == 8


async def test_cost_governance_persists_recommendations_decisions_and_budget_guards(
    postgres_factory: async_sessionmaker[AsyncSession],
) -> None:
    factory = lambda: SqlAlchemyUnitOfWork(postgres_factory)
    genesis = GenesisService(factory)
    costs = CostGovernanceService(factory)
    organization = await genesis.create_organization("Devsembly")
    initiative = await genesis.create_initiative(
        organization.id,
        name="Genesis",
        objective="Prove budget governance.",
        status=InitiativeStatus.ACTIVE,
    )
    project = await genesis.create_project(
        organization.id,
        initiative.id,
        name="Control Plane",
        repository="thebakermark/Devsembly",
        status=ProjectStatus.ACTIVE,
    )
    budget = await genesis.create_budget(
        organization.id,
        initiative.id,
        project.id,
        monthly_limit=Decimal("50.00"),
        currency="USD",
        enforcement_mode=BudgetEnforcementMode.WARN,
    )
    selected = CostOptionDefinition(
        key="standard",
        name="Standard",
        satisfies_acceptance_criteria=True,
        line_items=(
            CostLineItem(
                category="infrastructure",
                description="Standard runtime",
                cadence=CostCadence.MONTHLY,
                quantity=Decimal(2),
                unit_cost=Decimal("40.00"),
            ),
            CostLineItem(
                category="setup",
                description="Setup",
                cadence=CostCadence.ONE_TIME,
                quantity=Decimal(1),
                unit_cost=Decimal("10.00"),
            ),
        ),
    )
    lean = CostOptionDefinition(
        key="lean",
        name="Lean",
        satisfies_acceptance_criteria=True,
        line_items=(
            CostLineItem(
                category="infrastructure",
                description="Lean runtime",
                cadence=CostCadence.MONTHLY,
                quantity=Decimal(1),
                unit_cost=Decimal("40.00"),
            ),
        ),
    )

    evaluation, created = await costs.evaluate_costs(
        organization.id,
        initiative.id,
        project.id,
        idempotency_key="postgres-cost-23",
        workflow_run_id=None,
        selected_option=selected,
        alternatives=(lean,),
    )
    replay, replay_created = await costs.evaluate_costs(
        organization.id,
        initiative.id,
        project.id,
        idempotency_key="postgres-cost-23",
        workflow_run_id=None,
        selected_option=selected,
        alternatives=(lean,),
    )
    assert created is True
    assert replay_created is False
    assert replay.id == evaluation.id
    assert evaluation.outcome is CostEvaluationOutcome.APPROVAL_REQUIRED
    assert evaluation.selected_option.monthly_cost == Decimal("80.0000")
    assert evaluation.recommendation is not None
    assert evaluation.recommendation.option_key == "lean"

    proposed = await costs.create_decision(
        organization.id,
        initiative.id,
        project.id,
        cost_evaluation_id=evaluation.id,
        title="Choose a runtime",
        context="Select the runtime under the project budget.",
        selected_option=None,
        alternatives=(),
        currency=None,
        estimated_one_time_cost=None,
        estimated_monthly_cost=None,
        risk=DecisionRisk.MODERATE,
        confidence=Decimal("0.9000"),
        rationale="The standard option meets the requirements.",
    )
    approved = await costs.resolve_decision(
        organization.id,
        initiative.id,
        project.id,
        proposed.id,
        1,
        status=DecisionStatus.APPROVED,
        decided_by="human:mark",
        decision_note="Approve the bounded overage.",
        outcome="Approved for the Genesis proof.",
    )
    assert approved.status is DecisionStatus.APPROVED
    assert approved.authorization_budget_version == 1
    with pytest.raises(StaleVersionError):
        await costs.resolve_decision(
            organization.id,
            initiative.id,
            project.id,
            proposed.id,
            1,
            status=DecisionStatus.REJECTED,
            decided_by="human:mark",
            decision_note="Stale rewrite.",
            outcome="No change.",
        )

    blocked_budget = await genesis.update_budget(
        organization.id,
        initiative.id,
        project.id,
        budget.id,
        1,
        monthly_limit=Decimal("50.00"),
        currency="USD",
        enforcement_mode=BudgetEnforcementMode.BLOCK,
    )
    blocked_evaluation, _ = await costs.evaluate_costs(
        organization.id,
        initiative.id,
        project.id,
        idempotency_key="postgres-cost-blocked",
        workflow_run_id=None,
        selected_option=selected,
        alternatives=(lean,),
    )
    assert blocked_evaluation.outcome is CostEvaluationOutcome.BLOCKED
    blocked_decision = await costs.create_decision(
        organization.id,
        initiative.id,
        project.id,
        cost_evaluation_id=blocked_evaluation.id,
        title="Blocked runtime",
        context="Attempt selection under a hard limit.",
        selected_option=None,
        alternatives=(),
        currency=None,
        estimated_one_time_cost=None,
        estimated_monthly_cost=None,
        risk=DecisionRisk.HIGH,
        confidence=Decimal("0.8000"),
        rationale="Exercise the block guard.",
    )
    with pytest.raises(InvalidTransitionError):
        await costs.resolve_decision(
            organization.id,
            initiative.id,
            project.id,
            blocked_decision.id,
            1,
            status=DecisionStatus.APPROVED,
            decided_by="human:mark",
            decision_note="This must not pass.",
            outcome="Blocked.",
        )

    revised_budget = await genesis.update_budget(
        organization.id,
        initiative.id,
        project.id,
        budget.id,
        blocked_budget.version,
        monthly_limit=Decimal("100.00"),
        currency="USD",
        enforcement_mode=BudgetEnforcementMode.BLOCK,
    )
    resolved = await costs.resolve_decision(
        organization.id,
        initiative.id,
        project.id,
        blocked_decision.id,
        1,
        status=DecisionStatus.APPROVED,
        decided_by="human:mark",
        decision_note="The revised budget now permits this option.",
        outcome="Approved under the revised limit.",
    )
    assert resolved.authorization_budget_version == revised_budget.version
    assert resolved.authorization_monthly_limit == Decimal("100.0000")

    other_organization = await genesis.create_organization("Other")
    with pytest.raises(ResourceNotFoundError):
        await costs.get_cost_evaluation(
            other_organization.id,
            initiative.id,
            project.id,
            evaluation.id,
        )

    async with postgres_factory() as session:
        evaluation_count = await session.scalar(
            select(func.count()).select_from(models.CostEvaluation)
        )
        decision_count = await session.scalar(select(func.count()).select_from(models.Decision))
        cost_event_count = await session.scalar(
            select(func.count())
            .select_from(models.OutboxEvent)
            .where(
                (models.OutboxEvent.topic.like("genesis.cost_evaluation%"))
                | (models.OutboxEvent.topic.like("genesis.decision%"))
            )
        )
    assert evaluation_count == 2
    assert decision_count == 2
    assert cost_event_count == 6
