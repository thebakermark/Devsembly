from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from devsembly import models
from devsembly.genesis_service import GenesisService
from devsembly.outbox_publisher import (
    OutboxPublisher,
    OutboxWorker,
    PostgresEventFeed,
    PublisherConfig,
    worker_readiness,
)
from devsembly.unit_of_work import SqlAlchemyUnitOfWork

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


class FailOnceFeed(PostgresEventFeed):
    def __init__(self) -> None:
        self.failed = False

    async def publish(
        self,
        session: AsyncSession,
        event: models.OutboxEvent,
        published_at: datetime,
    ) -> None:
        if not self.failed:
            self.failed = True
            raise RuntimeError("simulated publication failure")
        await super().publish(session, event, published_at)


@pytest.fixture
async def postgres_factory() -> async_sessionmaker[AsyncSession]:
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE worker_heartbeats, published_events, outbox_events, "
                "audit_events, workflow_step_attempts, workflow_steps, workflow_runs, "
                "decisions, cost_evaluations, authorization_delegations, "
                "organization_memberships, external_identities, principals, budgets, "
                "projects, initiatives, organizations CASCADE"
            )
        )
    try:
        yield factory
    finally:
        await engine.dispose()


async def _seed_event(factory: async_sessionmaker[AsyncSession], now: datetime) -> uuid.UUID:
    event_id = uuid.uuid4()
    async with factory() as session, session.begin():
        session.add(
            models.OutboxEvent(
                id=event_id,
                occurred_at=now,
                topic="genesis.project.updated",
                aggregate_id=str(uuid.uuid4()),
                payload={"version": 2},
                available_at=now,
            )
        )
    return event_id


async def test_publication_is_idempotent_after_ack_state_is_lost(
    postgres_factory: async_sessionmaker[AsyncSession],
) -> None:
    clock = MutableClock(datetime(2026, 7, 30, 20, tzinfo=UTC))
    event_id = await _seed_event(postgres_factory, clock())
    publisher = OutboxPublisher(postgres_factory, worker_id="publisher-a", clock=clock)

    assert await publisher.run_batch() == (1, 0)

    async with postgres_factory() as session, session.begin():
        event = await session.get(models.OutboxEvent, event_id)
        assert event is not None
        event.published_at = None
        event.available_at = clock()

    assert await publisher.run_batch() == (1, 0)
    async with postgres_factory() as session:
        published_count = await session.scalar(
            select(func.count()).select_from(models.PublishedEvent)
        )
        event = await session.get(models.OutboxEvent, event_id)
    assert published_count == 1
    assert event is not None
    assert event.published_at == clock()


async def test_failure_uses_backoff_then_recovers(
    postgres_factory: async_sessionmaker[AsyncSession],
) -> None:
    clock = MutableClock(datetime(2026, 7, 30, 20, tzinfo=UTC))
    event_id = await _seed_event(postgres_factory, clock())
    publisher = OutboxPublisher(
        postgres_factory,
        worker_id="publisher-retry",
        sink=FailOnceFeed(),
        config=PublisherConfig(retry_base_seconds=2, retry_max_seconds=30),
        clock=clock,
    )

    assert await publisher.run_batch() == (0, 1)
    async with postgres_factory() as session:
        failed = await session.get(models.OutboxEvent, event_id)
    assert failed is not None
    assert failed.attempt_count == 1
    assert failed.available_at == clock() + timedelta(seconds=2)
    assert failed.last_error == "RuntimeError"

    clock.advance(1)
    assert await publisher.run_batch() == (0, 0)
    clock.advance(1)
    assert await publisher.run_batch() == (1, 0)


async def test_expired_claim_is_recovered_after_worker_crash(
    postgres_factory: async_sessionmaker[AsyncSession],
) -> None:
    clock = MutableClock(datetime(2026, 7, 30, 20, tzinfo=UTC))
    event_id = await _seed_event(postgres_factory, clock())
    crashed = OutboxPublisher(
        postgres_factory,
        worker_id="publisher-crashed",
        config=PublisherConfig(lease_seconds=5),
        clock=clock,
    )
    assert list(await crashed.claim_batch()) == [event_id]

    replacement = OutboxPublisher(
        postgres_factory,
        worker_id="publisher-replacement",
        config=PublisherConfig(lease_seconds=5),
        clock=clock,
    )
    assert await replacement.run_batch() == (0, 0)
    clock.advance(5)
    assert await replacement.run_batch() == (1, 0)


async def test_worker_heartbeat_reports_ready_and_stale(
    postgres_factory: async_sessionmaker[AsyncSession],
) -> None:
    clock = MutableClock(datetime(2026, 7, 30, 20, tzinfo=UTC))
    publisher = OutboxPublisher(postgres_factory, worker_id="healthy-publisher", clock=clock)
    worker = OutboxWorker(publisher, postgres_factory, clock=clock)

    assert await worker.run_once() == (0, 0)
    ready = await worker_readiness(postgres_factory, clock=clock)
    assert ready["ready"] is True
    assert ready["status"] == "ready"

    clock.advance(31)
    stale = await worker_readiness(postgres_factory, clock=clock)
    assert stale["ready"] is False


async def test_domain_event_writes_correlated_audit_record(
    postgres_factory: async_sessionmaker[AsyncSession],
) -> None:
    service = GenesisService(lambda: SqlAlchemyUnitOfWork(postgres_factory))
    organization = await service.create_organization("Audited organization")

    async with postgres_factory() as session:
        event = await session.scalar(select(models.OutboxEvent))
        audit = await session.scalar(
            select(models.AuditEvent).where(
                models.AuditEvent.action == "genesis.organization.created"
            )
        )
    assert event is not None
    assert audit is not None
    assert audit.object_id == str(organization.id)
    assert audit.correlation_id == str(event.id)
    assert audit.outcome == "success"
