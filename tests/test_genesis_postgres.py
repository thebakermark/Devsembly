from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from devsembly import models
from devsembly.domain import (
    BudgetEnforcementMode,
    InitiativeStatus,
    Organization,
    OutboxMessage,
    ProjectStatus,
)
from devsembly.errors import (
    DuplicateResourceError,
    ResourceNotFoundError,
    StaleVersionError,
)
from devsembly.genesis_service import GenesisService
from devsembly.unit_of_work import SqlAlchemyUnitOfWork

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
                "TRUNCATE outbox_events, audit_events, workflow_runs, decisions, "
                "budgets, projects, initiatives, organizations CASCADE"
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
    assert stored_organization is None
    assert stored_event is None
