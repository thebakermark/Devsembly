from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from temporalio.exceptions import WorkflowAlreadyStartedError

from devsembly import models
from devsembly.outbox_publisher import OutboxPublisher, worker_readiness
from devsembly.workflow_dispatcher import (
    WORKER_NAME,
    DispatcherConfig,
    DispatcherWorker,
    WorkflowDispatcher,
)

TEST_DATABASE_URL = os.getenv("DEVSEMBLY_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="DEVSEMBLY_TEST_DATABASE_URL is required for PostgreSQL integration tests",
)


class MutableClock:
    def __init__(self, current: datetime) -> None:
        self.current = current

    def __call__(self) -> datetime:
        return self.current

    def advance(self, seconds: int) -> None:
        self.current += timedelta(seconds=seconds)


class RecordingStarter:
    def __init__(self) -> None:
        self.workflow_ids: set[str] = set()
        self.calls: list[str] = []

    async def start(self, request: dict[str, object], workflow_id: str) -> None:
        assert request["workflow_run_id"] in workflow_id
        self.calls.append(workflow_id)
        if workflow_id in self.workflow_ids:
            raise WorkflowAlreadyStartedError(workflow_id, "CommittedWorkflow")
        self.workflow_ids.add(workflow_id)


class FailOnceStarter(RecordingStarter):
    def __init__(self) -> None:
        super().__init__()
        self.failed = False

    async def start(self, request: dict[str, object], workflow_id: str) -> None:
        if not self.failed:
            self.failed = True
            raise RuntimeError("simulated Temporal outage")
        await super().start(request, workflow_id)


class CrashAfterStartDispatcher(WorkflowDispatcher):
    crashed = False

    async def _acknowledge(self, workflow_run_id: uuid.UUID) -> bool:
        if not self.crashed:
            self.crashed = True
            raise RuntimeError("simulated crash after Temporal accepted the workflow")
        return await super()._acknowledge(workflow_run_id)


@pytest.fixture
async def postgres_factory() -> async_sessionmaker[AsyncSession]:
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE workflow_dispatches, worker_heartbeats, published_events, "
                "outbox_events, audit_events, workflow_step_attempts, workflow_steps, "
                "workflow_runs, decisions, cost_evaluations, authorization_delegations, "
                "organization_memberships, external_identities, principals, budgets, "
                "projects, initiatives, organizations CASCADE"
            )
        )
    try:
        yield factory
    finally:
        await engine.dispose()


async def _seed_committed_run(
    factory: async_sessionmaker[AsyncSession],
    now: datetime,
) -> tuple[uuid.UUID, uuid.UUID]:
    organization_id = uuid.uuid4()
    initiative_id = uuid.uuid4()
    project_id = uuid.uuid4()
    workflow_run_id = uuid.uuid4()
    event_id = uuid.uuid4()
    async with factory() as session, session.begin():
        session.add(
            models.Organization(
                id=organization_id,
                name="Devsembly",
                version=1,
                created_at=now,
                updated_at=now,
            )
        )
        await session.flush()
        session.add(
            models.Initiative(
                id=initiative_id,
                organization_id=organization_id,
                name="Genesis",
                objective="Build the governed runtime.",
                status="active",
                version=1,
                created_at=now,
                updated_at=now,
            )
        )
        await session.flush()
        session.add(
            models.Project(
                id=project_id,
                initiative_id=initiative_id,
                name="Control plane",
                status="active",
                version=1,
                created_at=now,
                updated_at=now,
            )
        )
        await session.flush()
        session.add(
            models.WorkflowRun(
                id=workflow_run_id,
                project_id=project_id,
                workflow_kind="software_change",
                idempotency_key=f"run-{workflow_run_id}",
                input_payload={"issue_number": 25},
                status="accepted",
                version=1,
                created_at=now,
                updated_at=now,
            )
        )
        await session.flush()
        session.add(
            models.WorkflowStep(
                id=uuid.uuid4(),
                workflow_run_id=workflow_run_id,
                key="build",
                name="Build the change",
                position=0,
                status="pending",
                version=1,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            models.OutboxEvent(
                id=event_id,
                occurred_at=now,
                topic="genesis.workflow_run.created",
                aggregate_id=str(workflow_run_id),
                payload={
                    "organization_id": str(organization_id),
                    "initiative_id": str(initiative_id),
                    "project_id": str(project_id),
                    "workflow_run_id": str(workflow_run_id),
                    "workflow_kind": "software_change",
                    "version": 1,
                },
                available_at=now,
            )
        )
    return workflow_run_id, event_id


async def test_only_published_committed_runs_are_dispatched(
    postgres_factory: async_sessionmaker[AsyncSession],
) -> None:
    clock = MutableClock(datetime(2026, 7, 30, 22, tzinfo=UTC))
    workflow_run_id, _ = await _seed_committed_run(postgres_factory, clock())
    starter = RecordingStarter()
    dispatcher = WorkflowDispatcher(postgres_factory, starter, clock=clock)

    assert await dispatcher.run_batch() == (0, 0, 0)
    await OutboxPublisher(postgres_factory, clock=clock).run_batch()
    assert await dispatcher.run_batch() == (1, 0, 0)

    workflow_id = f"genesis-run-{workflow_run_id}"
    assert starter.calls == [workflow_id]
    async with postgres_factory() as session:
        run = await session.get(models.WorkflowRun, workflow_run_id)
        dispatch = await session.get(models.WorkflowDispatch, workflow_run_id)
        status_event_count = await session.scalar(
            select(func.count())
            .select_from(models.OutboxEvent)
            .where(models.OutboxEvent.topic == "genesis.workflow_run.status_changed")
        )
    assert run is not None
    assert run.status == "queued"
    assert run.temporal_workflow_id == workflow_id
    assert run.version == 2
    assert dispatch is not None
    assert dispatch.status == "dispatched"
    assert status_event_count == 1


async def test_restart_recovers_crash_after_temporal_start_without_duplicate(
    postgres_factory: async_sessionmaker[AsyncSession],
) -> None:
    clock = MutableClock(datetime(2026, 7, 30, 22, tzinfo=UTC))
    workflow_run_id, _ = await _seed_committed_run(postgres_factory, clock())
    await OutboxPublisher(postgres_factory, clock=clock).run_batch()
    starter = RecordingStarter()
    crashed = CrashAfterStartDispatcher(
        postgres_factory,
        starter,
        worker_id="dispatcher-crashed",
        config=DispatcherConfig(retry_base_seconds=2),
        clock=clock,
    )

    assert await crashed.run_batch() == (0, 0, 1)
    assert starter.workflow_ids == {f"genesis-run-{workflow_run_id}"}

    clock.advance(2)
    replacement = WorkflowDispatcher(
        postgres_factory,
        starter,
        worker_id="dispatcher-replacement",
        clock=clock,
    )
    assert await replacement.run_batch() == (1, 0, 0)
    assert starter.calls == [
        f"genesis-run-{workflow_run_id}",
        f"genesis-run-{workflow_run_id}",
    ]
    async with postgres_factory() as session:
        dispatch = await session.get(models.WorkflowDispatch, workflow_run_id)
    assert dispatch is not None
    assert dispatch.status == "dispatched"
    assert dispatch.attempt_count == 2


async def test_expired_dispatch_lease_is_taken_over_after_restart(
    postgres_factory: async_sessionmaker[AsyncSession],
) -> None:
    clock = MutableClock(datetime(2026, 7, 30, 22, tzinfo=UTC))
    workflow_run_id, _ = await _seed_committed_run(postgres_factory, clock())
    await OutboxPublisher(postgres_factory, clock=clock).run_batch()
    starter = RecordingStarter()
    crashed = WorkflowDispatcher(
        postgres_factory,
        starter,
        worker_id="dispatcher-crashed",
        config=DispatcherConfig(lease_seconds=5),
        clock=clock,
    )
    assert list(await crashed.claim_batch()) == [workflow_run_id]

    replacement = WorkflowDispatcher(
        postgres_factory,
        starter,
        worker_id="dispatcher-replacement",
        config=DispatcherConfig(lease_seconds=5),
        clock=clock,
    )
    assert await replacement.run_batch() == (0, 0, 0)
    clock.advance(5)
    assert await replacement.run_batch() == (1, 0, 0)


async def test_temporal_failure_uses_backoff_then_recovers(
    postgres_factory: async_sessionmaker[AsyncSession],
) -> None:
    clock = MutableClock(datetime(2026, 7, 30, 22, tzinfo=UTC))
    workflow_run_id, _ = await _seed_committed_run(postgres_factory, clock())
    await OutboxPublisher(postgres_factory, clock=clock).run_batch()
    dispatcher = WorkflowDispatcher(
        postgres_factory,
        FailOnceStarter(),
        config=DispatcherConfig(retry_base_seconds=2),
        clock=clock,
    )

    assert await dispatcher.run_batch() == (0, 0, 1)
    async with postgres_factory() as session:
        failed = await session.get(models.WorkflowDispatch, workflow_run_id)
    assert failed is not None
    assert failed.available_at == clock() + timedelta(seconds=2)
    assert failed.last_error == "RuntimeError"

    clock.advance(1)
    assert await dispatcher.run_batch() == (0, 0, 0)
    clock.advance(1)
    assert await dispatcher.run_batch() == (1, 0, 0)


async def test_dispatcher_heartbeat_reports_restart_readiness(
    postgres_factory: async_sessionmaker[AsyncSession],
) -> None:
    clock = MutableClock(datetime(2026, 7, 30, 22, tzinfo=UTC))
    dispatcher = WorkflowDispatcher(postgres_factory, RecordingStarter(), clock=clock)
    worker = DispatcherWorker(dispatcher, postgres_factory, clock=clock)

    assert await worker.run_once() == (0, 0, 0)
    ready = await worker_readiness(
        postgres_factory,
        worker_name=WORKER_NAME,
        clock=clock,
    )
    assert ready["ready"] is True
    clock.advance(31)
    stale = await worker_readiness(
        postgres_factory,
        worker_name=WORKER_NAME,
        clock=clock,
    )
    assert stale["ready"] is False
