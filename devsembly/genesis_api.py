from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from devsembly.auth import (
    AuthorizedPrincipal,
    IdentityManagerDependency,
    authorize_request,
)
from devsembly.genesis_schemas import (
    BudgetCreate,
    BudgetRead,
    BudgetUpdate,
    InitiativeCreate,
    InitiativeRead,
    InitiativeUpdate,
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
)
from devsembly.genesis_service import GenesisService
from devsembly.unit_of_work import SqlAlchemyUnitOfWork

router = APIRouter(
    prefix="/api/v1/organizations",
    tags=["Genesis"],
    dependencies=[Depends(authorize_request)],
)


def get_genesis_service() -> GenesisService:
    return GenesisService(lambda: SqlAlchemyUnitOfWork())


Service = Annotated[GenesisService, Depends(get_genesis_service)]


@router.post("", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreate,
    service: Service,
    principal: AuthorizedPrincipal,
    identities: IdentityManagerDependency,
) -> OrganizationRead:
    organization = await service.create_organization(payload.name)
    await identities.bootstrap_organization_owner(organization.id, principal)
    return OrganizationRead.model_validate(organization)


@router.get("", response_model=list[OrganizationRead])
async def list_organizations(
    service: Service,
    principal: AuthorizedPrincipal,
    identities: IdentityManagerDependency,
) -> list[OrganizationRead]:
    organizations = await service.list_organizations()
    allowed = await identities.authorized_organization_ids(principal)
    return [OrganizationRead.model_validate(item) for item in organizations if item.id in allowed]


@router.get("/{organization_id}", response_model=OrganizationRead)
async def get_organization(organization_id: uuid.UUID, service: Service) -> OrganizationRead:
    organization = await service.get_organization(organization_id)
    return OrganizationRead.model_validate(organization)


@router.put("/{organization_id}", response_model=OrganizationRead)
async def update_organization(
    organization_id: uuid.UUID,
    payload: OrganizationUpdate,
    service: Service,
) -> OrganizationRead:
    organization = await service.update_organization(
        organization_id, payload.expected_version, payload.name
    )
    return OrganizationRead.model_validate(organization)


@router.post(
    "/{organization_id}/initiatives",
    response_model=InitiativeRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_initiative(
    organization_id: uuid.UUID,
    payload: InitiativeCreate,
    service: Service,
) -> InitiativeRead:
    initiative = await service.create_initiative(
        organization_id,
        name=payload.name,
        objective=payload.objective,
        status=payload.status,
    )
    return InitiativeRead.model_validate(initiative)


@router.get("/{organization_id}/initiatives", response_model=list[InitiativeRead])
async def list_initiatives(organization_id: uuid.UUID, service: Service) -> list[InitiativeRead]:
    initiatives = await service.list_initiatives(organization_id)
    return [InitiativeRead.model_validate(item) for item in initiatives]


@router.get(
    "/{organization_id}/initiatives/{initiative_id}",
    response_model=InitiativeRead,
)
async def get_initiative(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    service: Service,
) -> InitiativeRead:
    initiative = await service.get_initiative(organization_id, initiative_id)
    return InitiativeRead.model_validate(initiative)


@router.put(
    "/{organization_id}/initiatives/{initiative_id}",
    response_model=InitiativeRead,
)
async def update_initiative(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    payload: InitiativeUpdate,
    service: Service,
) -> InitiativeRead:
    initiative = await service.update_initiative(
        organization_id,
        initiative_id,
        payload.expected_version,
        name=payload.name,
        objective=payload.objective,
        status=payload.status,
    )
    return InitiativeRead.model_validate(initiative)


@router.post(
    "/{organization_id}/initiatives/{initiative_id}/projects",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    payload: ProjectCreate,
    service: Service,
) -> ProjectRead:
    project = await service.create_project(
        organization_id,
        initiative_id,
        name=payload.name,
        repository=payload.repository,
        status=payload.status,
    )
    return ProjectRead.model_validate(project)


@router.get(
    "/{organization_id}/initiatives/{initiative_id}/projects",
    response_model=list[ProjectRead],
)
async def list_projects(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    service: Service,
) -> list[ProjectRead]:
    projects = await service.list_projects(organization_id, initiative_id)
    return [ProjectRead.model_validate(item) for item in projects]


@router.get(
    "/{organization_id}/initiatives/{initiative_id}/projects/{project_id}",
    response_model=ProjectRead,
)
async def get_project(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    service: Service,
) -> ProjectRead:
    project = await service.get_project(organization_id, initiative_id, project_id)
    return ProjectRead.model_validate(project)


@router.put(
    "/{organization_id}/initiatives/{initiative_id}/projects/{project_id}",
    response_model=ProjectRead,
)
async def update_project(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    service: Service,
) -> ProjectRead:
    project = await service.update_project(
        organization_id,
        initiative_id,
        project_id,
        payload.expected_version,
        name=payload.name,
        repository=payload.repository,
        status=payload.status,
    )
    return ProjectRead.model_validate(project)


@router.post(
    "/{organization_id}/initiatives/{initiative_id}/projects/{project_id}/budgets",
    response_model=BudgetRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_budget(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    payload: BudgetCreate,
    service: Service,
) -> BudgetRead:
    budget = await service.create_budget(
        organization_id,
        initiative_id,
        project_id,
        monthly_limit=payload.monthly_limit,
        currency=payload.currency,
        enforcement_mode=payload.enforcement_mode,
    )
    return BudgetRead.model_validate(budget)


@router.get(
    "/{organization_id}/initiatives/{initiative_id}/projects/{project_id}/budgets",
    response_model=list[BudgetRead],
)
async def list_budgets(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    service: Service,
) -> list[BudgetRead]:
    budgets = await service.list_budgets(organization_id, initiative_id, project_id)
    return [BudgetRead.model_validate(item) for item in budgets]


@router.get(
    ("/{organization_id}/initiatives/{initiative_id}/projects/{project_id}/budgets/{budget_id}"),
    response_model=BudgetRead,
)
async def get_budget(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    budget_id: uuid.UUID,
    service: Service,
) -> BudgetRead:
    budget = await service.get_budget(organization_id, initiative_id, project_id, budget_id)
    return BudgetRead.model_validate(budget)


@router.put(
    ("/{organization_id}/initiatives/{initiative_id}/projects/{project_id}/budgets/{budget_id}"),
    response_model=BudgetRead,
)
async def update_budget(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    budget_id: uuid.UUID,
    payload: BudgetUpdate,
    service: Service,
) -> BudgetRead:
    budget = await service.update_budget(
        organization_id,
        initiative_id,
        project_id,
        budget_id,
        payload.expected_version,
        monthly_limit=payload.monthly_limit,
        currency=payload.currency,
        enforcement_mode=payload.enforcement_mode,
    )
    return BudgetRead.model_validate(budget)
