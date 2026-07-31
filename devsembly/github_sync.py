from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from devsembly import models
from devsembly.database import SessionFactory

FRESHNESS_WINDOW = timedelta(minutes=30)
_AUTHORITY = {"inferred": 0, "verified": 1, "approved": 2}


class InvalidGitHubSignature(ValueError):
    pass


class InvalidGitHubEvent(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class NormalizedGitHubEvent:
    repository_id: str
    delivery_id: str
    event_name: str
    action: str | None
    entity_kind: str
    entity_id: str
    occurred_at: datetime | None
    payload_sha256: str
    payload: dict[str, object]


@dataclass(frozen=True, slots=True)
class IngestionResult:
    delivery_id: str
    entity_id: str
    status: str
    duplicate: bool
    out_of_order: bool
    conflict_id: uuid.UUID | None
    reconciliation_required: bool


@dataclass(frozen=True, slots=True)
class SnapshotReconciliationResult:
    repository_id: str
    processed: int
    duplicates: int
    conflicts: int
    out_of_order: int
    stale_sources: int


def verify_signature(body: bytes, signature: str | None, secret: str) -> None:
    if not secret:
        raise InvalidGitHubSignature("GitHub webhook secret is not configured")
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if signature is None or not hmac.compare_digest(expected, signature):
        raise InvalidGitHubSignature("GitHub webhook signature is invalid")


def _timestamp(payload: dict[str, Any]) -> datetime | None:
    candidates = [
        payload.get("updated_at"),
        payload.get("created_at"),
        payload.get("submitted_at"),
        payload.get("timestamp"),
    ]
    for value in candidates:
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value)
            return parsed.astimezone(UTC)
    return None


def normalize_event(body: bytes, delivery_id: str, event_name: str) -> NormalizedGitHubEvent:
    try:
        raw = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidGitHubEvent("GitHub webhook body must be valid JSON") from exc
    if not isinstance(raw, dict):
        raise InvalidGitHubEvent("GitHub webhook body must be an object")
    repository = raw.get("repository")
    if not isinstance(repository, dict) or repository.get("id") is None:
        raise InvalidGitHubEvent("GitHub repository.id is required")

    entity: dict[str, Any] | None = None
    entity_kind = event_name
    for key, kind in (
        ("issue", "issue"),
        ("pull_request", "pull_request"),
        ("review", "review"),
        ("workflow_run", "workflow_run"),
        ("workflow_job", "workflow_job"),
        ("milestone", "milestone"),
        ("check_run", "check_run"),
        ("ref", "ref"),
        ("head_commit", "commit"),
    ):
        value = raw.get(key)
        if isinstance(value, dict):
            entity, entity_kind = value, kind
            break
        if key == "ref" and isinstance(value, str):
            entity, entity_kind = {"ref": value}, kind
            break
    if entity is None:
        entity = raw

    external_id = (
        entity.get("node_id") or entity.get("id") or entity.get("sha") or entity.get("ref")
    )
    if external_id is None:
        raise InvalidGitHubEvent(f"GitHub {entity_kind} stable identifier is required")
    repository_id = str(repository["id"])
    entity_id = f"github:{repository_id}:{entity_kind}:{external_id}"
    canonical = json.dumps(raw, sort_keys=True, separators=(",", ":")).encode()
    return NormalizedGitHubEvent(
        repository_id=repository_id,
        delivery_id=delivery_id,
        event_name=event_name,
        action=str(raw["action"]) if raw.get("action") is not None else None,
        entity_kind=entity_kind,
        entity_id=entity_id,
        occurred_at=_timestamp(entity),
        payload_sha256=hashlib.sha256(canonical).hexdigest(),
        payload=raw,
    )


class GitHubSynchronizationService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] = SessionFactory,
    ) -> None:
        self._session_factory = session_factory

    async def ingest(
        self,
        project_id: uuid.UUID,
        event: NormalizedGitHubEvent,
        *,
        authority: str = "verified",
        observed_at: datetime | None = None,
    ) -> IngestionResult:
        if authority not in _AUTHORITY:
            raise InvalidGitHubEvent("authority must be inferred, verified, or approved")
        now = observed_at or datetime.now(UTC)
        async with self._session_factory() as session:
            existing = await session.scalar(
                select(models.GitHubDelivery).where(
                    models.GitHubDelivery.repository_id == event.repository_id,
                    models.GitHubDelivery.delivery_id == event.delivery_id,
                )
            )
            existing_snapshot = None
            if existing is not None:
                if (
                    existing.project_id != project_id
                    or existing.payload_sha256 != event.payload_sha256
                ):
                    raise InvalidGitHubEvent(
                        "GitHub delivery identity was already used for different content"
                    )
                source = await session.scalar(
                    select(models.GitHubSourceState).where(
                        models.GitHubSourceState.project_id == project_id,
                        models.GitHubSourceState.entity_id == existing.entity_id,
                    )
                )
                existing_snapshot = (
                    existing.entity_id,
                    existing.status,
                    existing.out_of_order,
                    bool(source and source.reconciliation_required),
                )
        if existing_snapshot is not None:
            entity_id, existing_status, existing_out_of_order, reconciliation_required = (
                existing_snapshot
            )
            if existing_status != "processed":
                return await self._process(project_id, event, authority, now)
            return IngestionResult(
                event.delivery_id,
                entity_id,
                existing_status,
                True,
                existing_out_of_order,
                None,
                reconciliation_required,
            )

        async with self._session_factory() as session:
            delivery = models.GitHubDelivery(
                id=uuid.uuid4(),
                project_id=project_id,
                repository_id=event.repository_id,
                delivery_id=event.delivery_id,
                event_name=event.event_name,
                action=event.action,
                entity_kind=event.entity_kind,
                entity_id=event.entity_id,
                payload_sha256=event.payload_sha256,
                payload=event.payload,
                provider_occurred_at=event.occurred_at,
                observed_at=now,
                status="received",
                out_of_order=False,
            )
            session.add(delivery)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                return await self.ingest(
                    project_id, event, authority=authority, observed_at=observed_at
                )

        return await self._process(project_id, event, authority, now)

    async def _process(
        self,
        project_id: uuid.UUID,
        event: NormalizedGitHubEvent,
        authority: str,
        now: datetime,
    ) -> IngestionResult:
        async with self._session_factory() as session:
            delivery = await session.scalar(
                select(models.GitHubDelivery)
                .where(
                    models.GitHubDelivery.repository_id == event.repository_id,
                    models.GitHubDelivery.delivery_id == event.delivery_id,
                )
                .with_for_update()
            )
            assert delivery is not None
            source = await session.scalar(
                select(models.GitHubSourceState)
                .where(
                    models.GitHubSourceState.project_id == project_id,
                    models.GitHubSourceState.entity_id == event.entity_id,
                )
                .with_for_update()
            )
            out_of_order = bool(
                source
                and source.provider_occurred_at
                and event.occurred_at
                and event.occurred_at < source.provider_occurred_at
            )
            conflict: models.GitHubReconciliationConflict | None = None
            apply_incoming = source is None or (
                not out_of_order and _AUTHORITY[authority] >= _AUTHORITY[source.authority]
            )
            if source and source.payload_sha256 != event.payload_sha256:
                same_position = (
                    source.provider_occurred_at == event.occurred_at
                    and source.authority == authority
                )
                protected = _AUTHORITY[authority] < _AUTHORITY[source.authority]
                if same_position or protected:
                    conflict = models.GitHubReconciliationConflict(
                        id=uuid.uuid4(),
                        project_id=project_id,
                        entity_id=event.entity_id,
                        current_sha256=source.payload_sha256,
                        incoming_sha256=event.payload_sha256,
                        current_authority=source.authority,
                        incoming_authority=authority,
                        reason=(
                            "same-authority position contains different facts"
                            if same_position
                            else "lower-authority input cannot overwrite canonical facts"
                        ),
                        status="open",
                        created_at=now,
                    )
                    session.add(conflict)
                    apply_incoming = False

            if source is None:
                source = models.GitHubSourceState(
                    id=uuid.uuid4(),
                    project_id=project_id,
                    repository_id=event.repository_id,
                    entity_kind=event.entity_kind,
                    entity_id=event.entity_id,
                    payload_sha256=event.payload_sha256,
                    authority=authority,
                    last_delivery_id=event.delivery_id,
                    provider_occurred_at=event.occurred_at,
                    observed_at=now,
                    stale_after=now + FRESHNESS_WINDOW,
                    reconciliation_required=out_of_order,
                )
                session.add(source)
            elif apply_incoming:
                source.payload_sha256 = event.payload_sha256
                source.authority = authority
                source.last_delivery_id = event.delivery_id
                source.provider_occurred_at = event.occurred_at
                source.observed_at = now
                source.stale_after = now + FRESHNESS_WINDOW
            if source is not None:
                source.reconciliation_required = bool(
                    source.reconciliation_required or out_of_order or conflict
                )

            delivery.status = "processed"
            delivery.processed_at = now
            delivery.out_of_order = out_of_order
            event_id = uuid.uuid4()
            payload: dict[str, object] = {
                "project_id": str(project_id),
                "repository_id": event.repository_id,
                "delivery_id": event.delivery_id,
                "event_name": event.event_name,
                "entity_id": event.entity_id,
                "payload_sha256": event.payload_sha256,
                "authority": authority,
                "out_of_order": out_of_order,
                "conflict_id": None if conflict is None else str(conflict.id),
                "reconciliation_required": source.reconciliation_required,
            }
            session.add(
                models.OutboxEvent(
                    id=event_id,
                    occurred_at=now,
                    topic="genesis.project-intelligence.github-event-ingested",
                    aggregate_id=event.entity_id,
                    payload=payload,
                    available_at=now,
                )
            )
            session.add(
                models.AuditEvent(
                    id=uuid.uuid4(),
                    occurred_at=now,
                    actor_type="provider",
                    actor_id=f"github:{event.repository_id}",
                    action="genesis.project-intelligence.github-event-ingested",
                    object_type="project-intelligence.github-event",
                    object_id=event.entity_id,
                    project_id=project_id,
                    correlation_id=str(event_id),
                    outcome="success",
                    payload={"event_id": str(event_id), **payload},
                )
            )
            await session.commit()
            return IngestionResult(
                event.delivery_id,
                event.entity_id,
                delivery.status,
                False,
                out_of_order,
                None if conflict is None else conflict.id,
                source.reconciliation_required,
            )

    async def retry(self, project_id: uuid.UUID, event: NormalizedGitHubEvent) -> IngestionResult:
        """Resume a received/failed delivery after a partial failure without reinserting it."""
        return await self._process(project_id, event, "verified", datetime.now(UTC))

    async def reconcile_snapshot(
        self,
        project_id: uuid.UUID,
        repository_id: str,
        events: list[NormalizedGitHubEvent],
        *,
        observed_at: datetime | None = None,
    ) -> SnapshotReconciliationResult:
        """Apply a provider snapshot with stable, retry-safe synthetic delivery identities.

        Each entity commits independently. A provider outage can therefore resume the same page
        without replaying successful mutations, while ordinary event ordering and authority rules
        remain shared with webhook ingestion.
        """
        now = observed_at or datetime.now(UTC)
        if any(event.repository_id != repository_id for event in events):
            raise InvalidGitHubEvent("snapshot entities must belong to the requested repository")
        processed = duplicates = conflicts = out_of_order = 0
        for event in events:
            result = await self.ingest(project_id, event, authority="verified", observed_at=now)
            processed += 1
            duplicates += int(result.duplicate)
            conflicts += int(result.conflict_id is not None)
            out_of_order += int(result.out_of_order)
        return SnapshotReconciliationResult(
            repository_id=repository_id,
            processed=processed,
            duplicates=duplicates,
            conflicts=conflicts,
            out_of_order=out_of_order,
            stale_sources=await self.mark_stale_sources(project_id, repository_id, now=now),
        )

    async def mark_stale_sources(
        self,
        project_id: uuid.UUID,
        repository_id: str,
        *,
        now: datetime | None = None,
    ) -> int:
        """Flag expired provider state for snapshot repair without changing canonical facts."""
        checked_at = now or datetime.now(UTC)
        async with self._session_factory() as session:
            sources = list(
                (
                    await session.scalars(
                        select(models.GitHubSourceState)
                        .where(
                            models.GitHubSourceState.project_id == project_id,
                            models.GitHubSourceState.repository_id == repository_id,
                            models.GitHubSourceState.stale_after <= checked_at,
                        )
                        .with_for_update()
                    )
                ).all()
            )
            newly_stale = [source for source in sources if not source.reconciliation_required]
            for source in sources:
                source.reconciliation_required = True
            if newly_stale:
                event_id = uuid.uuid4()
                payload: dict[str, object] = {
                    "project_id": str(project_id),
                    "repository_id": repository_id,
                    "entity_ids": [source.entity_id for source in newly_stale],
                    "stale_count": len(newly_stale),
                }
                session.add(
                    models.OutboxEvent(
                        id=event_id,
                        occurred_at=checked_at,
                        topic="genesis.project-intelligence.github-sources-stale",
                        aggregate_id=f"github:{repository_id}",
                        payload=payload,
                        available_at=checked_at,
                    )
                )
                session.add(
                    models.AuditEvent(
                        id=uuid.uuid4(),
                        occurred_at=checked_at,
                        actor_type="service",
                        actor_id="github-snapshot-reconciler",
                        action="genesis.project-intelligence.github-sources-stale",
                        object_type="project-intelligence.github-repository",
                        object_id=f"github:{repository_id}",
                        project_id=project_id,
                        correlation_id=str(event_id),
                        outcome="success",
                        payload={"event_id": str(event_id), **payload},
                    )
                )
            await session.commit()
            return len(sources)


def normalize_snapshot_entity(
    repository_id: str,
    entity_kind: str,
    entity: dict[str, object],
) -> NormalizedGitHubEvent:
    """Normalize one authenticated snapshot entity through the webhook contract."""
    envelope = {"repository": {"id": repository_id}, entity_kind: entity}
    canonical = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(canonical).hexdigest()
    event = normalize_event(canonical, f"snapshot:{repository_id}:{digest}", entity_kind)
    return event
