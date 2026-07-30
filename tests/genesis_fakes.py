from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from decimal import Decimal
from types import TracebackType
from typing import Self

from devsembly.domain import Budget, Initiative, Organization, OutboxMessage, Project
from devsembly.errors import DuplicateResourceError, StaleVersionError


@dataclass
class MemoryStore:
    organizations: dict[uuid.UUID, Organization] = field(default_factory=dict)
    initiatives: dict[uuid.UUID, Initiative] = field(default_factory=dict)
    projects: dict[uuid.UUID, Project] = field(default_factory=dict)
    budgets: dict[uuid.UUID, Budget] = field(default_factory=dict)
    outbox: list[OutboxMessage] = field(default_factory=list)
    commits: int = 0
    rollbacks: int = 0


class MemoryOrganizationRepository:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    async def add(self, organization: Organization) -> Organization:
        self.store.organizations[organization.id] = organization
        return organization

    async def get(self, organization_id: uuid.UUID) -> Organization | None:
        return self.store.organizations.get(organization_id)

    async def list(self) -> list[Organization]:
        return list(self.store.organizations.values())

    async def update(
        self, organization_id: uuid.UUID, expected_version: int, name: str
    ) -> Organization | None:
        current = await self.get(organization_id)
        if current is None:
            return None
        if current.version != expected_version:
            raise StaleVersionError("organization", expected_version)
        updated = replace(current, name=name, version=current.version + 1)
        self.store.organizations[organization_id] = updated
        return updated


class MemoryInitiativeRepository:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    async def add(self, initiative: Initiative) -> Initiative:
        self.store.initiatives[initiative.id] = initiative
        return initiative

    async def get(self, organization_id: uuid.UUID, initiative_id: uuid.UUID) -> Initiative | None:
        initiative = self.store.initiatives.get(initiative_id)
        if initiative is None or initiative.organization_id != organization_id:
            return None
        return initiative

    async def list(self, organization_id: uuid.UUID) -> list[Initiative]:
        return [
            initiative
            for initiative in self.store.initiatives.values()
            if initiative.organization_id == organization_id
        ]

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
        current = await self.get(organization_id, initiative_id)
        if current is None:
            return None
        if current.version != expected_version:
            raise StaleVersionError("initiative", expected_version)
        updated = replace(
            current,
            name=name,
            objective=objective,
            status=type(current.status)(status),
            version=current.version + 1,
        )
        self.store.initiatives[initiative_id] = updated
        return updated


class MemoryProjectRepository:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    async def add(self, project: Project) -> Project:
        self.store.projects[project.id] = project
        return project

    async def get(self, initiative_id: uuid.UUID, project_id: uuid.UUID) -> Project | None:
        project = self.store.projects.get(project_id)
        if project is None or project.initiative_id != initiative_id:
            return None
        return project

    async def list(self, initiative_id: uuid.UUID) -> list[Project]:
        return [
            project
            for project in self.store.projects.values()
            if project.initiative_id == initiative_id
        ]

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
        current = await self.get(initiative_id, project_id)
        if current is None:
            return None
        if current.version != expected_version:
            raise StaleVersionError("project", expected_version)
        updated = replace(
            current,
            name=name,
            repository=repository,
            status=type(current.status)(status),
            version=current.version + 1,
        )
        self.store.projects[project_id] = updated
        return updated


class MemoryBudgetRepository:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    async def add(self, budget: Budget) -> Budget:
        if any(item.project_id == budget.project_id for item in self.store.budgets.values()):
            raise DuplicateResourceError("project budget")
        self.store.budgets[budget.id] = budget
        return budget

    async def get(self, project_id: uuid.UUID, budget_id: uuid.UUID) -> Budget | None:
        budget = self.store.budgets.get(budget_id)
        if budget is None or budget.project_id != project_id:
            return None
        return budget

    async def list(self, project_id: uuid.UUID) -> list[Budget]:
        return [budget for budget in self.store.budgets.values() if budget.project_id == project_id]

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
        current = await self.get(project_id, budget_id)
        if current is None:
            return None
        if current.version != expected_version:
            raise StaleVersionError("budget", expected_version)
        updated = replace(
            current,
            monthly_limit=monthly_limit,
            currency=currency,
            enforcement_mode=type(current.enforcement_mode)(enforcement_mode),
            version=current.version + 1,
        )
        self.store.budgets[budget_id] = updated
        return updated


class MemoryOutboxRepository:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    async def add(self, message: OutboxMessage) -> OutboxMessage:
        self.store.outbox.append(message)
        return message


class MemoryUnitOfWork:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store
        self.organizations = MemoryOrganizationRepository(store)
        self.initiatives = MemoryInitiativeRepository(store)
        self.projects = MemoryProjectRepository(store)
        self.budgets = MemoryBudgetRepository(store)
        self.outbox = MemoryOutboxRepository(store)
        self.committed = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None or not self.committed:
            await self.rollback()

    async def commit(self) -> None:
        self.committed = True
        self.store.commits += 1

    async def rollback(self) -> None:
        self.store.rollbacks += 1


class MemoryUnitOfWorkFactory:
    def __init__(self) -> None:
        self.store = MemoryStore()

    def __call__(self) -> MemoryUnitOfWork:
        return MemoryUnitOfWork(self.store)
