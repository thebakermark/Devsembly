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

from devsembly import models
from devsembly.database import SessionFactory

Clock = Callable[[], datetime]
WORKER_NAME = "outbox-publisher"


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class PublisherConfig:
    batch_size: int = 50
    lease_seconds: int = 30
    retry_base_seconds: int = 1
    retry_max_seconds: int = 300


class EventSink(Protocol):
    async def publish(
        self,
        session: AsyncSession,
        event: models.OutboxEvent,
        published_at: datetime,
    ) -> None: ...


class PostgresEventFeed:
    """Idempotently publishes an outbox event to the durable Genesis event feed."""

    async def publish(
        self,
        session: AsyncSession,
        event: models.OutboxEvent,
        published_at: datetime,
    ) -> None:
        statement = (
            insert(models.PublishedEvent)
            .values(
                event_id=event.id,
                occurred_at=event.occurred_at,
                published_at=published_at,
                topic=event.topic,
                aggregate_id=event.aggregate_id,
                payload=event.payload,
            )
            .on_conflict_do_nothing(index_elements=[models.PublishedEvent.event_id])
        )
        await session.execute(statement)


class OutboxPublisher:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] = SessionFactory,
        *,
        worker_id: str | None = None,
        sink: EventSink | None = None,
        config: PublisherConfig | None = None,
        clock: Clock = _utc_now,
    ) -> None:
        self._session_factory = session_factory
        self.worker_id = worker_id or f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4()}"
        self._sink = sink or PostgresEventFeed()
        self._config = config or PublisherConfig()
        self._clock = clock

    async def claim_batch(self) -> Sequence[uuid.UUID]:
        now = self._clock()
        claimed_until = now + timedelta(seconds=self._config.lease_seconds)
        async with self._session_factory() as session, session.begin():
            result = await session.scalars(
                select(models.OutboxEvent)
                .where(
                    models.OutboxEvent.published_at.is_(None),
                    models.OutboxEvent.available_at <= now,
                    or_(
                        models.OutboxEvent.claimed_until.is_(None),
                        models.OutboxEvent.claimed_until <= now,
                    ),
                )
                .order_by(models.OutboxEvent.occurred_at, models.OutboxEvent.id)
                .with_for_update(skip_locked=True)
                .limit(self._config.batch_size)
            )
            events = list(result)
            for event in events:
                event.claimed_by = self.worker_id
                event.claimed_until = claimed_until
                event.attempt_count += 1
            await session.flush()
            return [event.id for event in events]

    async def publish_claimed(self, event_ids: Sequence[uuid.UUID]) -> tuple[int, int]:
        published = 0
        failed = 0
        for event_id in event_ids:
            try:
                if await self._publish_one(event_id):
                    published += 1
            except Exception as exc:  # noqa: BLE001 - failures are persisted for retry
                failed += 1
                await self._record_failure(event_id, exc)
        return published, failed

    async def run_batch(self) -> tuple[int, int]:
        return await self.publish_claimed(await self.claim_batch())

    async def _publish_one(self, event_id: uuid.UUID) -> bool:
        now = self._clock()
        async with self._session_factory() as session, session.begin():
            event = await session.scalar(
                select(models.OutboxEvent)
                .where(models.OutboxEvent.id == event_id)
                .with_for_update()
            )
            if event is None or event.published_at is not None:
                return False
            if event.claimed_by != self.worker_id:
                return False
            await self._sink.publish(session, event, now)
            event.published_at = now
            event.claimed_by = None
            event.claimed_until = None
            event.last_error = None
            await session.flush()
            return True

    async def _record_failure(self, event_id: uuid.UUID, exc: Exception) -> None:
        now = self._clock()
        async with self._session_factory() as session, session.begin():
            event = await session.scalar(
                select(models.OutboxEvent)
                .where(models.OutboxEvent.id == event_id)
                .with_for_update()
            )
            if event is None or event.published_at is not None:
                return
            exponent = min(30, max(0, event.attempt_count - 1))
            delay = min(
                self._config.retry_max_seconds,
                self._config.retry_base_seconds * (2**exponent),
            )
            event.available_at = now + timedelta(seconds=delay)
            event.claimed_by = None
            event.claimed_until = None
            event.last_error = type(exc).__name__[:200]
            await session.flush()

    async def pending_count(self) -> int:
        async with self._session_factory() as session:
            count = await session.scalar(
                select(func.count())
                .select_from(models.OutboxEvent)
                .where(models.OutboxEvent.published_at.is_(None))
            )
            return int(count or 0)


class OutboxWorker:
    def __init__(
        self,
        publisher: OutboxPublisher,
        session_factory: async_sessionmaker[AsyncSession] = SessionFactory,
        *,
        clock: Clock = _utc_now,
    ) -> None:
        self._publisher = publisher
        self._session_factory = session_factory
        self._clock = clock
        self._started_at = clock()

    async def heartbeat(self, status: str, detail: dict[str, object]) -> None:
        now = self._clock()
        statement = (
            insert(models.WorkerHeartbeat)
            .values(
                worker_name=WORKER_NAME,
                worker_id=self._publisher.worker_id,
                status=status,
                started_at=self._started_at,
                last_seen_at=now,
                detail=detail,
            )
            .on_conflict_do_update(
                index_elements=[models.WorkerHeartbeat.worker_name],
                set_={
                    "worker_id": self._publisher.worker_id,
                    "status": status,
                    "started_at": self._started_at,
                    "last_seen_at": now,
                    "detail": detail,
                },
            )
        )
        async with self._session_factory() as session, session.begin():
            await session.execute(statement)

    async def run_once(self) -> tuple[int, int]:
        try:
            published, failed = await self._publisher.run_batch()
            pending = await self._publisher.pending_count()
            status = "ready" if failed == 0 else "degraded"
            await self.heartbeat(
                status,
                {"published": published, "failed": failed, "pending": pending},
            )
            return published, failed
        except Exception as exc:
            await self.heartbeat("degraded", {"error": type(exc).__name__})
            raise


async def worker_readiness(
    session_factory: async_sessionmaker[AsyncSession] = SessionFactory,
    *,
    worker_name: str = WORKER_NAME,
    max_age_seconds: int = 30,
    clock: Clock = _utc_now,
) -> dict[str, object]:
    async with session_factory() as session:
        heartbeat = await session.get(models.WorkerHeartbeat, worker_name)
    if heartbeat is None:
        return {"ready": False, "reason": "missing"}
    age_seconds = max(0.0, (clock() - heartbeat.last_seen_at).total_seconds())
    ready = heartbeat.status == "ready" and age_seconds <= max_age_seconds
    return {
        "ready": ready,
        "status": heartbeat.status,
        "worker_id": heartbeat.worker_id,
        "age_seconds": round(age_seconds, 3),
        "detail": heartbeat.detail,
    }


async def _run_worker() -> None:
    poll_seconds = float(os.getenv("DEVSEMBLY_OUTBOX_POLL_SECONDS", "1"))
    publisher = OutboxPublisher()
    worker = OutboxWorker(publisher)
    await worker.heartbeat("starting", {})
    try:
        while True:
            await worker.run_once()
            await asyncio.sleep(poll_seconds)
    finally:
        await worker.heartbeat("stopping", {})


async def _healthcheck() -> int:
    maximum_age = int(os.getenv("DEVSEMBLY_OUTBOX_HEALTH_MAX_AGE_SECONDS", "30"))
    result = await worker_readiness(max_age_seconds=maximum_age)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["ready"] is True else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish the Genesis transactional outbox.")
    parser.add_argument("--healthcheck", action="store_true")
    args = parser.parse_args()
    if args.healthcheck:
        raise SystemExit(asyncio.run(_healthcheck()))
    asyncio.run(_run_worker())


if __name__ == "__main__":
    main()
