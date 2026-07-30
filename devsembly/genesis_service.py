from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from decimal import Decimal

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
from devsembly.errors import DuplicateResourceError, ResourceNotFoundError
from devsembly.unit_of_work import UnitOfWork

UnitOfWorkFactory = Callable[[], UnitOfWork]
Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


class GenesisService:
    def __init__(self, unit_of_work: UnitOfWorkFactory, clock: Clock = _utc_now) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    def _message(
        self, topic: str, aggregate_id: uuid.UUID, payload: dict[str, object]
    ) -> OutboxMessage:
        return OutboxMessage(
            id=uuid.uuid4(),
            occurred_at=self._clock(),
            topic=topic,
            aggregate_id=str(aggregate_id),
            payload=payload,
        )

    async def create_organization(self, name: str) -> Organization:
        now = self._clock()
        organization = Organization(
            id=uuid.uuid4(),
            name=name,
            version=1,
            created_at=now,
            updated_at=now,
        )
        async with self._unit_of_work() as unit:
            await unit.organizations.add(organization)
            await unit.outbox.add(
                self._message(
                    "genesis.organization.created",
                    organization.id,
                    {"organization_id": str(organization.id), "version": 1},
                )
            )
            await unit.commit()
        return organization

    async def get_organization(self, organization_id: uuid.UUID) -> Organization:
        async with self._unit_of_work() as unit:
            organization = await unit.organizations.get(organization_id)
            if organization is None:
                raise ResourceNotFoundError("organization")
            return organization

    async def list_organizations(self) -> Sequence[Organization]:
        async with self._unit_of_work() as unit:
            return await unit.organizations.list()

    async def update_organization(
        self, organization_id: uuid.UUID, expected_version: int, name: str
    ) -> Organization:
        async with self._unit_of_work() as unit:
            organization = await unit.organizations.update(organization_id, expected_version, name)
            if organization is None:
                raise ResourceNotFoundError("organization")
            await unit.outbox.add(
                self._message(
                    "genesis.organization.updated",
                    organization.id,
                    {
                        "organization_id": str(organization.id),
                        "version": organization.version,
                    },
                )
            )
            await unit.commit()
            return organization

    async def create_initiative(
        self,
        organization_id: uuid.UUID,
        *,
        name: str,
        objective: str,
        status: InitiativeStatus,
    ) -> Initiative:
        now = self._clock()
        initiative = Initiative(
            id=uuid.uuid4(),
            organization_id=organization_id,
            name=name,
            objective=objective,
            status=status,
            version=1,
            created_at=now,
            updated_at=now,
        )
        async with self._unit_of_work() as unit:
            await self._require_organization(unit, organization_id)
            await unit.initiatives.add(initiative)
            await unit.outbox.add(
                self._message(
                    "genesis.initiative.created",
                    initiative.id,
                    {
                        "organization_id": str(organization_id),
                        "initiative_id": str(initiative.id),
                        "version": 1,
                    },
                )
            )
            await unit.commit()
        return initiative

    async def get_initiative(
        self, organization_id: uuid.UUID, initiative_id: uuid.UUID
    ) -> Initiative:
        async with self._unit_of_work() as unit:
            return await self._require_initiative(unit, organization_id, initiative_id)

    async def list_initiatives(self, organization_id: uuid.UUID) -> Sequence[Initiative]:
        async with self._unit_of_work() as unit:
            await self._require_organization(unit, organization_id)
            return await unit.initiatives.list(organization_id)

    async def update_initiative(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        expected_version: int,
        *,
        name: str,
        objective: str,
        status: InitiativeStatus,
    ) -> Initiative:
        async with self._unit_of_work() as unit:
            await self._require_organization(unit, organization_id)
            initiative = await unit.initiatives.update(
                organization_id,
                initiative_id,
                expected_version,
                name=name,
                objective=objective,
                status=status.value,
            )
            if initiative is None:
                raise ResourceNotFoundError("initiative")
            await unit.outbox.add(
                self._message(
                    "genesis.initiative.updated",
                    initiative.id,
                    {
                        "organization_id": str(organization_id),
                        "initiative_id": str(initiative.id),
                        "version": initiative.version,
                    },
                )
            )
            await unit.commit()
            return initiative

    async def create_project(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        *,
        name: str,
        repository: str | None,
        status: ProjectStatus,
    ) -> Project:
        now = self._clock()
        project = Project(
            id=uuid.uuid4(),
            initiative_id=initiative_id,
            name=name,
            repository=repository,
            status=status,
            version=1,
            created_at=now,
            updated_at=now,
        )
        async with self._unit_of_work() as unit:
            await self._require_initiative(unit, organization_id, initiative_id)
            await unit.projects.add(project)
            await unit.outbox.add(
                self._message(
                    "genesis.project.created",
                    project.id,
                    {
                        "organization_id": str(organization_id),
                        "initiative_id": str(initiative_id),
                        "project_id": str(project.id),
                        "version": 1,
                    },
                )
            )
            await unit.commit()
        return project

    async def get_project(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> Project:
        async with self._unit_of_work() as unit:
            return await self._require_project(unit, organization_id, initiative_id, project_id)

    async def list_projects(
        self, organization_id: uuid.UUID, initiative_id: uuid.UUID
    ) -> Sequence[Project]:
        async with self._unit_of_work() as unit:
            await self._require_initiative(unit, organization_id, initiative_id)
            return await unit.projects.list(initiative_id)

    async def update_project(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
        expected_version: int,
        *,
        name: str,
        repository: str | None,
        status: ProjectStatus,
    ) -> Project:
        async with self._unit_of_work() as unit:
            await self._require_initiative(unit, organization_id, initiative_id)
            project = await unit.projects.update(
                initiative_id,
                project_id,
                expected_version,
                name=name,
                repository=repository,
                status=status.value,
            )
            if project is None:
                raise ResourceNotFoundError("project")
            await unit.outbox.add(
                self._message(
                    "genesis.project.updated",
                    project.id,
                    {
                        "organization_id": str(organization_id),
                        "initiative_id": str(initiative_id),
                        "project_id": str(project.id),
                        "version": project.version,
                    },
                )
            )
            await unit.commit()
            return project

    async def create_budget(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
        *,
        monthly_limit: Decimal,
        currency: str,
        enforcement_mode: BudgetEnforcementMode,
    ) -> Budget:
        now = self._clock()
        budget = Budget(
            id=uuid.uuid4(),
            project_id=project_id,
            monthly_limit=monthly_limit,
            currency=currency,
            enforcement_mode=enforcement_mode,
            version=1,
            created_at=now,
            updated_at=now,
        )
        async with self._unit_of_work() as unit:
            await self._require_project(unit, organization_id, initiative_id, project_id)
            if await unit.budgets.list(project_id):
                raise DuplicateResourceError("project budget")
            await unit.budgets.add(budget)
            await unit.outbox.add(
                self._message(
                    "genesis.budget.created",
                    budget.id,
                    {
                        "organization_id": str(organization_id),
                        "initiative_id": str(initiative_id),
                        "project_id": str(project_id),
                        "budget_id": str(budget.id),
                        "version": 1,
                    },
                )
            )
            await unit.commit()
        return budget

    async def get_budget(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
        budget_id: uuid.UUID,
    ) -> Budget:
        async with self._unit_of_work() as unit:
            await self._require_project(unit, organization_id, initiative_id, project_id)
            budget = await unit.budgets.get(project_id, budget_id)
            if budget is None:
                raise ResourceNotFoundError("budget")
            return budget

    async def list_budgets(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> Sequence[Budget]:
        async with self._unit_of_work() as unit:
            await self._require_project(unit, organization_id, initiative_id, project_id)
            return await unit.budgets.list(project_id)

    async def update_budget(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
        budget_id: uuid.UUID,
        expected_version: int,
        *,
        monthly_limit: Decimal,
        currency: str,
        enforcement_mode: BudgetEnforcementMode,
    ) -> Budget:
        async with self._unit_of_work() as unit:
            await self._require_project(unit, organization_id, initiative_id, project_id)
            budget = await unit.budgets.update(
                project_id,
                budget_id,
                expected_version,
                monthly_limit=monthly_limit,
                currency=currency,
                enforcement_mode=enforcement_mode.value,
            )
            if budget is None:
                raise ResourceNotFoundError("budget")
            await unit.outbox.add(
                self._message(
                    "genesis.budget.updated",
                    budget.id,
                    {
                        "organization_id": str(organization_id),
                        "initiative_id": str(initiative_id),
                        "project_id": str(project_id),
                        "budget_id": str(budget.id),
                        "version": budget.version,
                    },
                )
            )
            await unit.commit()
            return budget

    @staticmethod
    async def _require_organization(unit: UnitOfWork, organization_id: uuid.UUID) -> Organization:
        organization = await unit.organizations.get(organization_id)
        if organization is None:
            raise ResourceNotFoundError("organization")
        return organization

    @staticmethod
    async def _require_initiative(
        unit: UnitOfWork, organization_id: uuid.UUID, initiative_id: uuid.UUID
    ) -> Initiative:
        initiative = await unit.initiatives.get(organization_id, initiative_id)
        if initiative is None:
            raise ResourceNotFoundError("initiative")
        return initiative

    @classmethod
    async def _require_project(
        cls,
        unit: UnitOfWork,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> Project:
        await cls._require_initiative(unit, organization_id, initiative_id)
        project = await unit.projects.get(initiative_id, project_id)
        if project is None:
            raise ResourceNotFoundError("project")
        return project
