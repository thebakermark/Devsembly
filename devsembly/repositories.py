from __future__ import annotations

import uuid
from collections.abc import Sequence
from decimal import Decimal
from typing import Protocol

from devsembly.domain import Budget, Initiative, Organization, OutboxMessage, Project


class OrganizationRepository(Protocol):
    async def add(self, organization: Organization) -> Organization: ...

    async def get(self, organization_id: uuid.UUID) -> Organization | None: ...

    async def list(self) -> Sequence[Organization]: ...

    async def update(
        self, organization_id: uuid.UUID, expected_version: int, name: str
    ) -> Organization | None: ...


class InitiativeRepository(Protocol):
    async def add(self, initiative: Initiative) -> Initiative: ...

    async def get(
        self, organization_id: uuid.UUID, initiative_id: uuid.UUID
    ) -> Initiative | None: ...

    async def list(self, organization_id: uuid.UUID) -> Sequence[Initiative]: ...

    async def update(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        expected_version: int,
        *,
        name: str,
        objective: str,
        status: str,
    ) -> Initiative | None: ...


class ProjectRepository(Protocol):
    async def add(self, project: Project) -> Project: ...

    async def get(self, initiative_id: uuid.UUID, project_id: uuid.UUID) -> Project | None: ...

    async def list(self, initiative_id: uuid.UUID) -> Sequence[Project]: ...

    async def update(
        self,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
        expected_version: int,
        *,
        name: str,
        repository: str | None,
        status: str,
    ) -> Project | None: ...


class BudgetRepository(Protocol):
    async def add(self, budget: Budget) -> Budget: ...

    async def get(self, project_id: uuid.UUID, budget_id: uuid.UUID) -> Budget | None: ...

    async def list(self, project_id: uuid.UUID) -> Sequence[Budget]: ...

    async def update(
        self,
        project_id: uuid.UUID,
        budget_id: uuid.UUID,
        expected_version: int,
        *,
        monthly_limit: Decimal,
        currency: str,
        enforcement_mode: str,
    ) -> Budget | None: ...


class OutboxRepository(Protocol):
    async def add(self, message: OutboxMessage) -> OutboxMessage: ...
