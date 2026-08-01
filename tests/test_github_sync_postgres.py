from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from devsembly import models
from devsembly.domain import InitiativeStatus, Project, ProjectStatus
from devsembly.genesis_service import GenesisService
from devsembly.github_sync import (
    GitHubSynchronizationService,
    InvalidGitHubEvent,
    normalize_snapshot_entity,
)
from devsembly.unit_of_work import SqlAlchemyUnitOfWork

TEST_DATABASE_URL = os.getenv("DEVSEMBLY_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="DEVSEMBLY_TEST_DATABASE_URL is required for PostgreSQL integration tests",
)


@pytest.fixture
async def postgres_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE github_reconciliation_conflicts, github_source_states, "
                "github_deliveries, outbox_events, audit_events, projects, initiatives, "
                "organizations CASCADE"
            )
        )
    try:
        yield factory
    finally:
        await engine.dispose()


async def _project(
    factory: async_sessionmaker[AsyncSession],
) -> tuple[Project, models.Organization, models.Initiative]:
    genesis = GenesisService(lambda: SqlAlchemyUnitOfWork(factory))
    organization = await genesis.create_organization("GitHub synchronization")
    initiative = await genesis.create_initiative(
        organization.id,
        name="PIE",
        objective="Repair provider state.",
        status=InitiativeStatus.ACTIVE,
    )
    project = await genesis.create_project(
        organization.id,
        initiative.id,
        name="Devsembly",
        repository="thebakermark/Devsembly",
        status=ProjectStatus.ACTIVE,
    )
    async with factory() as session:
        organization_record = await session.get(models.Organization, organization.id)
        initiative_record = await session.get(models.Initiative, initiative.id)
        assert organization_record is not None and initiative_record is not None
        session.expunge(organization_record)
        session.expunge(initiative_record)
    return project, organization_record, initiative_record


async def test_snapshot_retry_is_idempotent_and_stale_detection_is_once_only(
    postgres_factory: async_sessionmaker[AsyncSession],
) -> None:
    project, _, _ = await _project(postgres_factory)
    service = GitHubSynchronizationService(postgres_factory)
    observed = datetime(2026, 7, 31, 17, tzinfo=UTC)
    event = normalize_snapshot_entity(
        "991",
        "issue",
        {"node_id": "I_kw26", "updated_at": "2026-07-31T17:00:00Z"},
    )

    first = await service.reconcile_snapshot(project.id, "991", [event], observed_at=observed)
    replay = await service.reconcile_snapshot(project.id, "991", [event], observed_at=observed)
    assert first.processed == 1 and first.duplicates == 0
    assert replay.processed == 1 and replay.duplicates == 1

    stale_at = observed + timedelta(minutes=31)
    assert await service.mark_stale_sources(project.id, "991", now=stale_at) == 1
    assert await service.mark_stale_sources(project.id, "991", now=stale_at) == 1
    async with postgres_factory() as session:
        stale_events = await session.scalar(
            select(func.count())
            .select_from(models.OutboxEvent)
            .where(models.OutboxEvent.topic == "genesis.project-intelligence.github-sources-stale")
        )
        source = await session.scalar(select(models.GitHubSourceState))
    assert stale_events == 1
    assert source is not None and source.reconciliation_required is True


async def test_delivery_identity_cannot_be_reused_for_different_content(
    postgres_factory: async_sessionmaker[AsyncSession],
) -> None:
    project, _, _ = await _project(postgres_factory)
    service = GitHubSynchronizationService(postgres_factory)
    original = normalize_snapshot_entity("991", "issue", {"node_id": "I_kw26", "title": "A"})
    await service.ingest(project.id, original)
    forged = normalize_snapshot_entity("991", "issue", {"node_id": "I_kw26", "title": "B"})
    forged = type(forged)(
        repository_id=forged.repository_id,
        delivery_id=original.delivery_id,
        event_name=forged.event_name,
        action=forged.action,
        entity_kind=forged.entity_kind,
        entity_id=forged.entity_id,
        occurred_at=forged.occurred_at,
        payload_sha256=forged.payload_sha256,
        payload=forged.payload,
    )
    with pytest.raises(InvalidGitHubEvent, match="different content"):
        await service.ingest(project.id, forged)


async def test_conflict_resolution_is_authorized_evidenced_and_idempotent(
    postgres_factory: async_sessionmaker[AsyncSession],
) -> None:
    project, organization, initiative = await _project(postgres_factory)
    service = GitHubSynchronizationService(postgres_factory)
    observed = datetime(2026, 7, 31, 20, tzinfo=UTC)
    current = normalize_snapshot_entity(
        "991", "issue", {"node_id": "I_kw26", "updated_at": observed.isoformat(), "state": "open"}
    )
    incoming = normalize_snapshot_entity(
        "991", "issue", {"node_id": "I_kw26", "updated_at": observed.isoformat(), "state": "closed"}
    )
    await service.ingest(project.id, current, observed_at=observed)
    result = await service.ingest(project.id, incoming, observed_at=observed)
    assert result.conflict_id is not None
    async with postgres_factory() as session, session.begin():
        principal = models.Principal(display_name="PIE approver")
        session.add(principal)
        await session.flush()
        principal_id = principal.id

    open_conflicts = await service.list_conflicts(organization.id, initiative.id, project.id)
    assert [item.id for item in open_conflicts] == [result.conflict_id]
    resolved = await service.resolve_conflict(
        organization.id,
        initiative.id,
        project.id,
        result.conflict_id,
        resolution="accept_incoming",
        reason="GitHub is authoritative for issue state.",
        principal_id=principal_id,
        resolved_at=observed + timedelta(minutes=1),
    )
    replay = await service.resolve_conflict(
        organization.id,
        initiative.id,
        project.id,
        result.conflict_id,
        resolution="accept_incoming",
        reason="GitHub is authoritative for issue state.",
        principal_id=principal_id,
        resolved_at=observed + timedelta(minutes=2),
    )
    assert resolved.status == replay.status == "resolved"
    assert resolved.resolved_by == principal_id
    async with postgres_factory() as session:
        source = await session.scalar(select(models.GitHubSourceState))
        evidence_count = await session.scalar(
            select(func.count())
            .select_from(models.OutboxEvent)
            .where(
                models.OutboxEvent.topic == "genesis.project-intelligence.github-conflict-resolved"
            )
        )
        audit_count = await session.scalar(
            select(func.count())
            .select_from(models.AuditEvent)
            .where(
                models.AuditEvent.action == "genesis.project-intelligence.github-conflict-resolved"
            )
        )
    assert source is not None
    assert source.payload_sha256 == incoming.payload_sha256
    assert source.authority == "approved"
    assert source.reconciliation_required is False
    assert evidence_count == audit_count == 1
