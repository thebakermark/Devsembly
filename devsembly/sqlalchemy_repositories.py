from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from devsembly import models
from devsembly.domain import (
    Budget,
    BudgetEnforcementMode,
    Initiative,
    InitiativeStatus,
    Organization,
    OutboxMessage,
    Project,
    ProjectStatus,
)
from devsembly.errors import DuplicateResourceError, StaleVersionError


def _organization(model: models.Organization) -> Organization:
    return Organization(
        id=model.id,
        name=model.name,
        version=model.version,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _initiative(model: models.Initiative) -> Initiative:
    return Initiative(
        id=model.id,
        organization_id=model.organization_id,
        name=model.name,
        objective=model.objective,
        status=InitiativeStatus(model.status),
        version=model.version,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _project(model: models.Project) -> Project:
    return Project(
        id=model.id,
        initiative_id=model.initiative_id,
        name=model.name,
        repository=model.repository,
        status=ProjectStatus(model.status),
        version=model.version,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _budget(model: models.Budget) -> Budget:
    return Budget(
        id=model.id,
        project_id=model.project_id,
        monthly_limit=model.monthly_limit,
        currency=model.currency,
        enforcement_mode=BudgetEnforcementMode(model.enforcement_mode),
        version=model.version,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SqlAlchemyOrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, organization: Organization) -> Organization:
        self._session.add(
            models.Organization(
                id=organization.id,
                name=organization.name,
                version=organization.version,
                created_at=organization.created_at,
                updated_at=organization.updated_at,
            )
        )
        await self._session.flush()
        return organization

    async def get(self, organization_id: uuid.UUID) -> Organization | None:
        model = await self._session.get(models.Organization, organization_id)
        return None if model is None else _organization(model)

    async def list(self) -> Sequence[Organization]:
        result = await self._session.scalars(
            select(models.Organization).order_by(
                models.Organization.created_at, models.Organization.id
            )
        )
        return [_organization(model) for model in result]

    async def update(
        self, organization_id: uuid.UUID, expected_version: int, name: str
    ) -> Organization | None:
        now = datetime.now(UTC)
        result = await self._session.scalars(
            update(models.Organization)
            .where(
                models.Organization.id == organization_id,
                models.Organization.version == expected_version,
            )
            .values(name=name, version=expected_version + 1, updated_at=now)
            .returning(models.Organization)
        )
        model = result.one_or_none()
        if model is not None:
            return _organization(model)
        if await self.get(organization_id) is None:
            return None
        raise StaleVersionError("organization", expected_version)


class SqlAlchemyInitiativeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, initiative: Initiative) -> Initiative:
        self._session.add(
            models.Initiative(
                id=initiative.id,
                organization_id=initiative.organization_id,
                name=initiative.name,
                objective=initiative.objective,
                status=initiative.status.value,
                version=initiative.version,
                created_at=initiative.created_at,
                updated_at=initiative.updated_at,
            )
        )
        await self._session.flush()
        return initiative

    async def get(self, organization_id: uuid.UUID, initiative_id: uuid.UUID) -> Initiative | None:
        result = await self._session.scalars(
            select(models.Initiative).where(
                models.Initiative.id == initiative_id,
                models.Initiative.organization_id == organization_id,
            )
        )
        model = result.one_or_none()
        return None if model is None else _initiative(model)

    async def list(self, organization_id: uuid.UUID) -> Sequence[Initiative]:
        result = await self._session.scalars(
            select(models.Initiative)
            .where(models.Initiative.organization_id == organization_id)
            .order_by(models.Initiative.created_at, models.Initiative.id)
        )
        return [_initiative(model) for model in result]

    async def update(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        expected_version: int,
        *,
        name: str,
        objective: str,
        status: str,
    ) -> Initiative | None:
        now = datetime.now(UTC)
        result = await self._session.scalars(
            update(models.Initiative)
            .where(
                models.Initiative.id == initiative_id,
                models.Initiative.organization_id == organization_id,
                models.Initiative.version == expected_version,
            )
            .values(
                name=name,
                objective=objective,
                status=status,
                version=expected_version + 1,
                updated_at=now,
            )
            .returning(models.Initiative)
        )
        model = result.one_or_none()
        if model is not None:
            return _initiative(model)
        if await self.get(organization_id, initiative_id) is None:
            return None
        raise StaleVersionError("initiative", expected_version)


class SqlAlchemyProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, project: Project) -> Project:
        self._session.add(
            models.Project(
                id=project.id,
                initiative_id=project.initiative_id,
                name=project.name,
                repository=project.repository,
                status=project.status.value,
                version=project.version,
                created_at=project.created_at,
                updated_at=project.updated_at,
            )
        )
        await self._session.flush()
        return project

    async def get(self, initiative_id: uuid.UUID, project_id: uuid.UUID) -> Project | None:
        result = await self._session.scalars(
            select(models.Project).where(
                models.Project.id == project_id,
                models.Project.initiative_id == initiative_id,
            )
        )
        model = result.one_or_none()
        return None if model is None else _project(model)

    async def list(self, initiative_id: uuid.UUID) -> Sequence[Project]:
        result = await self._session.scalars(
            select(models.Project)
            .where(models.Project.initiative_id == initiative_id)
            .order_by(models.Project.created_at, models.Project.id)
        )
        return [_project(model) for model in result]

    async def update(
        self,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
        expected_version: int,
        *,
        name: str,
        repository: str | None,
        status: str,
    ) -> Project | None:
        now = datetime.now(UTC)
        result = await self._session.scalars(
            update(models.Project)
            .where(
                models.Project.id == project_id,
                models.Project.initiative_id == initiative_id,
                models.Project.version == expected_version,
            )
            .values(
                name=name,
                repository=repository,
                status=status,
                version=expected_version + 1,
                updated_at=now,
            )
            .returning(models.Project)
        )
        model = result.one_or_none()
        if model is not None:
            return _project(model)
        if await self.get(initiative_id, project_id) is None:
            return None
        raise StaleVersionError("project", expected_version)


class SqlAlchemyBudgetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, budget: Budget) -> Budget:
        self._session.add(
            models.Budget(
                id=budget.id,
                project_id=budget.project_id,
                monthly_limit=budget.monthly_limit,
                currency=budget.currency,
                enforcement_mode=budget.enforcement_mode.value,
                version=budget.version,
                created_at=budget.created_at,
                updated_at=budget.updated_at,
            )
        )
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise DuplicateResourceError("project budget") from exc
        return budget

    async def get(self, project_id: uuid.UUID, budget_id: uuid.UUID) -> Budget | None:
        result = await self._session.scalars(
            select(models.Budget).where(
                models.Budget.id == budget_id,
                models.Budget.project_id == project_id,
            )
        )
        model = result.one_or_none()
        return None if model is None else _budget(model)

    async def list(self, project_id: uuid.UUID) -> Sequence[Budget]:
        result = await self._session.scalars(
            select(models.Budget)
            .where(models.Budget.project_id == project_id)
            .order_by(models.Budget.created_at, models.Budget.id)
        )
        return [_budget(model) for model in result]

    async def update(
        self,
        project_id: uuid.UUID,
        budget_id: uuid.UUID,
        expected_version: int,
        *,
        monthly_limit: Decimal,
        currency: str,
        enforcement_mode: str,
    ) -> Budget | None:
        now = datetime.now(UTC)
        result = await self._session.scalars(
            update(models.Budget)
            .where(
                models.Budget.id == budget_id,
                models.Budget.project_id == project_id,
                models.Budget.version == expected_version,
            )
            .values(
                monthly_limit=monthly_limit,
                currency=currency,
                enforcement_mode=enforcement_mode,
                version=expected_version + 1,
                updated_at=now,
            )
            .returning(models.Budget)
        )
        model = result.one_or_none()
        if model is not None:
            return _budget(model)
        if await self.get(project_id, budget_id) is None:
            return None
        raise StaleVersionError("budget", expected_version)


class SqlAlchemyOutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, message: OutboxMessage) -> OutboxMessage:
        self._session.add(
            models.OutboxEvent(
                id=message.id,
                occurred_at=message.occurred_at,
                topic=message.topic,
                aggregate_id=message.aggregate_id,
                payload=message.payload,
            )
        )
        await self._session.flush()
        return message
