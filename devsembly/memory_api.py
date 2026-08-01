from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from devsembly.auth import AuthorizedPrincipal, authorize_request
from devsembly.domain import MemoryStatus
from devsembly.memory_schemas import (
    ContextBuildRequest,
    ContextPackageRead,
    MemoryProposalCreate,
    MemoryRead,
    MemoryResolve,
)
from devsembly.memory_service import MemoryContextService
from devsembly.unit_of_work import SqlAlchemyUnitOfWork

router = APIRouter(
    prefix=(
        "/api/v1/organizations/{organization_id}/initiatives/{initiative_id}"
        "/projects/{project_id}/memory"
    ),
    tags=["Memory and context"],
    dependencies=[Depends(authorize_request)],
)


def get_memory_context_service() -> MemoryContextService:
    return MemoryContextService(lambda: SqlAlchemyUnitOfWork())


Service = Annotated[MemoryContextService, Depends(get_memory_context_service)]


@router.post("/proposals", response_model=MemoryRead, status_code=status.HTTP_201_CREATED)
async def propose_memory(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    payload: MemoryProposalCreate,
    service: Service,
    principal: AuthorizedPrincipal,
) -> MemoryRead:
    memory = await service.propose(
        organization_id,
        initiative_id,
        project_id,
        **payload.model_dump(),
        proposed_by=str(principal.principal_id),
    )
    return MemoryRead.model_validate(memory)


@router.get("/records", response_model=list[MemoryRead])
async def list_memories(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    service: Service,
) -> list[MemoryRead]:
    records = await service.list_memories(organization_id, initiative_id, project_id)
    return [MemoryRead.model_validate(record) for record in records]


async def _resolve(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    memory_id: uuid.UUID,
    payload: MemoryResolve,
    service: MemoryContextService,
    principal: AuthorizedPrincipal,
    target: MemoryStatus,
) -> MemoryRead:
    memory = await service.resolve(
        organization_id,
        initiative_id,
        project_id,
        memory_id,
        payload.expected_version,
        status=target,
        decided_by=str(principal.principal_id),
        reason=payload.reason,
    )
    return MemoryRead.model_validate(memory)


@router.post("/proposals/{memory_id}/approve", response_model=MemoryRead)
async def approve_memory(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    memory_id: uuid.UUID,
    payload: MemoryResolve,
    service: Service,
    principal: AuthorizedPrincipal,
) -> MemoryRead:
    return await _resolve(
        organization_id,
        initiative_id,
        project_id,
        memory_id,
        payload,
        service,
        principal,
        MemoryStatus.APPROVED,
    )


@router.post("/proposals/{memory_id}/reject", response_model=MemoryRead)
async def reject_memory(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    memory_id: uuid.UUID,
    payload: MemoryResolve,
    service: Service,
    principal: AuthorizedPrincipal,
) -> MemoryRead:
    return await _resolve(
        organization_id,
        initiative_id,
        project_id,
        memory_id,
        payload,
        service,
        principal,
        MemoryStatus.REJECTED,
    )


@router.post("/context", response_model=ContextPackageRead, status_code=status.HTTP_201_CREATED)
async def build_context(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    payload: ContextBuildRequest,
    service: Service,
    principal: AuthorizedPrincipal,
) -> ContextPackageRead:
    package = await service.build_context(
        organization_id,
        initiative_id,
        project_id,
        task=payload.task,
        token_budget=payload.token_budget,
        created_by=str(principal.principal_id),
    )
    return ContextPackageRead.model_validate(package)


@router.get("/context/{package_id}", response_model=ContextPackageRead)
async def get_context(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    package_id: uuid.UUID,
    service: Service,
) -> ContextPackageRead:
    package = await service.get_context(organization_id, initiative_id, project_id, package_id)
    return ContextPackageRead.model_validate(package)
