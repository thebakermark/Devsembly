from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError

from devsembly import models
from devsembly.database import SessionFactory
from devsembly.factory import GovernedFactoryWorkflow
from devsembly.temporal_workflows import CommittedWorkflow

Clock = Callable[[], datetime]
WORKER_NAME = "temporal-dispatcher"
DISPATCH_TOPICS = (
    "genesis.workflow_run.created",
    "genesis.workflow_run.retry_created",
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class DispatcherConfig:
    batch_size: int = 25
    lease_seconds: int = 30
    retry_base_seconds: int = 1
    retry_max_seconds: int = 300
    task_queue: str = "devsembly-factory"


class WorkflowStarter(Protocol):
    async def start(self, request: dict[str, object], workflow_id: str) -> None: ...


class TemporalWorkflowStarter:
    def __init__(self, client: Client, task_queue: str) -> None:
        self._client = client
        self._task_queue = task_queue

    async def start(self, request: dict[str, object], workflow_id: str) -> None:
        workflow_entrypoint = (
            GovernedFactoryWorkflow.run
            if request.get("workflow_kind") == "software_delivery"
            else CommittedWorkflow.run
        )
        await self._client.start_workflow(
            workflow_entrypoint,
            request,
            id=workflow_id,
            task_queue=self._task_queue,
            id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
        )


class WorkflowDispatcher:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        starter: WorkflowStarter,
        *,
        worker_id: str | None = None,
        config: DispatcherConfig | None = None,
        clock: Clock = _utc_now,
    ) -> None:
        self._session_factory = session_factory
        self._starter = starter
        self.worker_id = worker_id or f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4()}"
        self._config = config or DispatcherConfig()
        self._clock = clock

    async def materialize_committed_runs(self) -> int:
        async with self._session_factory() as session, session.begin():
            result = await session.scalars(
                select(models.PublishedEvent)
                .outerjoin(
                    models.WorkflowDispatch,
                    models.WorkflowDispatch.source_event_id == models.PublishedEvent.event_id,
                )
                .where(
                    models.PublishedEvent.topic.in_(DISPATCH_TOPICS),
                    models.WorkflowDispatch.source_event_id.is_(None),
                )
                .order_by(models.PublishedEvent.sequence)
                .limit(self._config.batch_size)
            )
            events = list(result)
            inserted = 0
            for event in events:
                workflow_run_id = uuid.UUID(event.aggregate_id)
                statement = (
                    insert(models.WorkflowDispatch)
                    .values(
                        workflow_run_id=workflow_run_id,
                        source_event_id=event.event_id,
                        temporal_workflow_id=f"genesis-run-{workflow_run_id}",
                        status="pending",
                        available_at=self._clock(),
                    )
                    .on_conflict_do_nothing()
                )
                await session.execute(statement)
                inserted += 1
            return inserted

    async def claim_batch(self) -> Sequence[uuid.UUID]:
        await self.materialize_committed_runs()
        now = self._clock()
        claimed_until = now + timedelta(seconds=self._config.lease_seconds)
        async with self._session_factory() as session, session.begin():
            result = await session.scalars(
                select(models.WorkflowDispatch)
                .where(
                    models.WorkflowDispatch.status == "pending",
                    models.WorkflowDispatch.available_at <= now,
                    or_(
                        models.WorkflowDispatch.claimed_until.is_(None),
                        models.WorkflowDispatch.claimed_until <= now,
                    ),
                )
                .order_by(
                    models.WorkflowDispatch.available_at,
                    models.WorkflowDispatch.created_at,
                    models.WorkflowDispatch.workflow_run_id,
                )
                .with_for_update(skip_locked=True)
                .limit(self._config.batch_size)
            )
            dispatches = list(result)
            for dispatch in dispatches:
                dispatch.claimed_by = self.worker_id
                dispatch.claimed_until = claimed_until
                dispatch.attempt_count += 1
                dispatch.updated_at = now
            await session.flush()
            return [dispatch.workflow_run_id for dispatch in dispatches]

    async def run_batch(self) -> tuple[int, int, int]:
        dispatched = 0
        skipped = 0
        failed = 0
        for workflow_run_id in await self.claim_batch():
            try:
                request = await self._reserve_and_build_request(workflow_run_id)
                if request is None:
                    skipped += 1
                    continue
                workflow_id = str(request["temporal_workflow_id"])
                try:
                    await self._starter.start(request, workflow_id)
                except WorkflowAlreadyStartedError:
                    pass
                if await self._acknowledge(workflow_run_id):
                    dispatched += 1
            except Exception as exc:  # noqa: BLE001 - failures are persisted for retry
                failed += 1
                await self._record_failure(workflow_run_id, exc)
        return dispatched, skipped, failed

    async def _reserve_and_build_request(
        self, workflow_run_id: uuid.UUID
    ) -> dict[str, object] | None:
        now = self._clock()
        async with self._session_factory() as session, session.begin():
            dispatch = await session.scalar(
                select(models.WorkflowDispatch)
                .where(models.WorkflowDispatch.workflow_run_id == workflow_run_id)
                .with_for_update()
            )
            workflow_run = await session.scalar(
                select(models.WorkflowRun)
                .where(models.WorkflowRun.id == workflow_run_id)
                .with_for_update()
            )
            if (
                dispatch is None
                or workflow_run is None
                or dispatch.status != "pending"
                or dispatch.claimed_by != self.worker_id
            ):
                return None

            source = await session.get(models.PublishedEvent, dispatch.source_event_id)
            if source is None:
                raise RuntimeError("dispatch source event is missing")

            if workflow_run.status == "accepted":
                previous_version = workflow_run.version
                workflow_run.status = "queued"
                workflow_run.temporal_workflow_id = dispatch.temporal_workflow_id
                workflow_run.version += 1
                workflow_run.updated_at = now
                payload = {
                    **source.payload,
                    "previous_status": "accepted",
                    "status": "queued",
                    "version": previous_version + 1,
                }
                event_id = uuid.uuid4()
                session.add(
                    models.OutboxEvent(
                        id=event_id,
                        occurred_at=now,
                        topic="genesis.workflow_run.status_changed",
                        aggregate_id=str(workflow_run_id),
                        payload=payload,
                        available_at=now,
                    )
                )
                session.add(
                    models.AuditEvent(
                        occurred_at=now,
                        actor_type="service",
                        actor_id=WORKER_NAME,
                        action="genesis.workflow_run.status_changed",
                        object_type="workflow_run",
                        object_id=str(workflow_run_id),
                        organization_id=uuid.UUID(str(source.payload["organization_id"])),
                        project_id=workflow_run.project_id,
                        correlation_id=str(event_id),
                        outcome="success",
                        payload={"event_id": str(event_id), **payload},
                    )
                )
            elif (
                workflow_run.temporal_workflow_id != dispatch.temporal_workflow_id
                or workflow_run.status
                in {
                    "succeeded",
                    "failed",
                    "cancelled",
                }
            ):
                dispatch.status = "skipped"
                dispatch.claimed_by = None
                dispatch.claimed_until = None
                dispatch.last_error = None
                dispatch.updated_at = now
                return None

            steps = list(
                await session.scalars(
                    select(models.WorkflowStep)
                    .where(models.WorkflowStep.workflow_run_id == workflow_run_id)
                    .order_by(models.WorkflowStep.position, models.WorkflowStep.id)
                )
            )
            return {
                "organization_id": source.payload["organization_id"],
                "initiative_id": source.payload["initiative_id"],
                "project_id": source.payload["project_id"],
                "workflow_run_id": str(workflow_run.id),
                "workflow_kind": workflow_run.workflow_kind,
                "input_payload": workflow_run.input_payload,
                "steps": [
                    {
                        "id": str(step.id),
                        "key": step.key,
                        "name": step.name,
                        "position": step.position,
                    }
                    for step in steps
                ],
                "temporal_workflow_id": dispatch.temporal_workflow_id,
            }

    async def _acknowledge(self, workflow_run_id: uuid.UUID) -> bool:
        now = self._clock()
        async with self._session_factory() as session, session.begin():
            dispatch = await session.scalar(
                select(models.WorkflowDispatch)
                .where(models.WorkflowDispatch.workflow_run_id == workflow_run_id)
                .with_for_update()
            )
            if (
                dispatch is None
                or dispatch.status != "pending"
                or dispatch.claimed_by != self.worker_id
            ):
                return False
            dispatch.status = "dispatched"
            dispatch.dispatched_at = now
            dispatch.claimed_by = None
            dispatch.claimed_until = None
            dispatch.last_error = None
            dispatch.updated_at = now
            return True

    async def _record_failure(self, workflow_run_id: uuid.UUID, exc: Exception) -> None:
        now = self._clock()
        async with self._session_factory() as session, session.begin():
            dispatch = await session.scalar(
                select(models.WorkflowDispatch)
                .where(models.WorkflowDispatch.workflow_run_id == workflow_run_id)
                .with_for_update()
            )
            if dispatch is None or dispatch.status != "pending":
                return
            exponent = min(30, max(0, dispatch.attempt_count - 1))
            delay = min(
                self._config.retry_max_seconds,
                self._config.retry_base_seconds * (2**exponent),
            )
            dispatch.available_at = now + timedelta(seconds=delay)
            dispatch.claimed_by = None
            dispatch.claimed_until = None
            dispatch.last_error = type(exc).__name__[:200]
            dispatch.updated_at = now

    async def pending_count(self) -> int:
        async with self._session_factory() as session:
            count = await session.scalar(
                select(func.count())
                .select_from(models.WorkflowDispatch)
                .where(models.WorkflowDispatch.status == "pending")
            )
        return int(count or 0)


class DispatcherWorker:
    def __init__(
        self,
        dispatcher: WorkflowDispatcher,
        session_factory: async_sessionmaker[AsyncSession] = SessionFactory,
        *,
        clock: Clock = _utc_now,
    ) -> None:
        self._dispatcher = dispatcher
        self._session_factory = session_factory
        self._clock = clock
        self._started_at = clock()

    async def heartbeat(self, status: str, detail: dict[str, object]) -> None:
        now = self._clock()
        statement = (
            insert(models.WorkerHeartbeat)
            .values(
                worker_name=WORKER_NAME,
                worker_id=self._dispatcher.worker_id,
                status=status,
                started_at=self._started_at,
                last_seen_at=now,
                detail=detail,
            )
            .on_conflict_do_update(
                index_elements=[models.WorkerHeartbeat.worker_name],
                set_={
                    "worker_id": self._dispatcher.worker_id,
                    "status": status,
                    "started_at": self._started_at,
                    "last_seen_at": now,
                    "detail": detail,
                },
            )
        )
        async with self._session_factory() as session, session.begin():
            await session.execute(statement)

    async def run_once(self) -> tuple[int, int, int]:
        try:
            dispatched, skipped, failed = await self._dispatcher.run_batch()
            pending = await self._dispatcher.pending_count()
            status = "ready" if failed == 0 else "degraded"
            await self.heartbeat(
                status,
                {
                    "dispatched": dispatched,
                    "skipped": skipped,
                    "failed": failed,
                    "pending": pending,
                },
            )
            return dispatched, skipped, failed
        except Exception as exc:
            await self.heartbeat("degraded", {"error": type(exc).__name__})
            raise


async def _run_worker() -> None:
    poll_seconds = float(os.getenv("DEVSEMBLY_DISPATCH_POLL_SECONDS", "1"))
    address = os.getenv("DEVSEMBLY_TEMPORAL_ADDRESS", "localhost:7233")
    task_queue = os.getenv("DEVSEMBLY_TEMPORAL_TASK_QUEUE", "devsembly-factory")
    client = await Client.connect(address)
    dispatcher = WorkflowDispatcher(
        SessionFactory,
        TemporalWorkflowStarter(client, task_queue),
        config=DispatcherConfig(task_queue=task_queue),
    )
    worker = DispatcherWorker(dispatcher)
    await worker.heartbeat("starting", {})
    try:
        while True:
            await worker.run_once()
            await asyncio.sleep(poll_seconds)
    finally:
        await worker.heartbeat("stopping", {})


async def _healthcheck() -> int:
    from devsembly.outbox_publisher import worker_readiness

    maximum_age = int(os.getenv("DEVSEMBLY_DISPATCH_HEALTH_MAX_AGE_SECONDS", "30"))
    result = await worker_readiness(
        worker_name=WORKER_NAME,
        max_age_seconds=maximum_age,
    )
    print(json.dumps(result, sort_keys=True))
    return 0 if result["ready"] is True else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Dispatch committed Genesis runs to Temporal.")
    parser.add_argument("--healthcheck", action="store_true")
    args = parser.parse_args()
    if args.healthcheck:
        raise SystemExit(asyncio.run(_healthcheck()))
    asyncio.run(_run_worker())


if __name__ == "__main__":
    main()
