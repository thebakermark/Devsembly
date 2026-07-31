from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from devsembly.auth import authorize_request
from devsembly.domain import ProjectStateRevision
from devsembly.pie_schemas import (
    ProjectStateAssertionRead,
    ProjectStateReconcile,
    ProjectStateRevisionRead,
    ProjectStateSourceRead,
)
from devsembly.pie_service import ProjectIntelligenceService
from devsembly.unit_of_work import SqlAlchemyUnitOfWork

router = APIRouter(
    prefix=(
        "/api/v1/organizations/{organization_id}/initiatives/{initiative_id}"
        "/projects/{project_id}/project-intelligence"
    ),
    tags=["Project Intelligence"],
    dependencies=[Depends(authorize_request)],
)


def get_project_intelligence_service() -> ProjectIntelligenceService:
    return ProjectIntelligenceService(lambda: SqlAlchemyUnitOfWork())


Service = Annotated[ProjectIntelligenceService, Depends(get_project_intelligence_service)]


def _read(revision: ProjectStateRevision) -> ProjectStateRevisionRead:
    return ProjectStateRevisionRead(
        id=revision.id,
        project_id=revision.project_id,
        version=revision.version,
        parent_revision_id=revision.parent_revision_id,
        schema_version=revision.schema_version,
        state=revision.state,
        state_sha256=revision.state_sha256,
        source=ProjectStateSourceRead(
            provider=revision.source_provider,
            kind=revision.source_kind,
            event_id=revision.source_event_id,
            uri=revision.source_uri,
            occurred_at=revision.source_occurred_at,
            observed_at=revision.observed_at,
        ),
        assertion=ProjectStateAssertionRead(
            status=revision.assertion_status,
            confidence=revision.confidence,
            explanation=revision.confidence_explanation,
        ),
        created_at=revision.created_at,
    )


@router.get("/state", response_model=ProjectStateRevisionRead)
async def latest_project_state(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    service: Service,
) -> ProjectStateRevisionRead:
    return _read(await service.latest(organization_id, initiative_id, project_id))


@router.get("/revisions", response_model=list[ProjectStateRevisionRead])
async def list_project_state_revisions(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    service: Service,
) -> list[ProjectStateRevisionRead]:
    revisions = await service.list_revisions(organization_id, initiative_id, project_id)
    return [_read(revision) for revision in revisions]


@router.get("/revisions/{version}", response_model=ProjectStateRevisionRead)
async def get_project_state_revision(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    version: int,
    service: Service,
) -> ProjectStateRevisionRead:
    return _read(await service.get_version(organization_id, initiative_id, project_id, version))


@router.post(
    "/revisions",
    response_model=ProjectStateRevisionRead,
    status_code=status.HTTP_201_CREATED,
)
async def reconcile_project_state(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    payload: ProjectStateReconcile,
    service: Service,
) -> ProjectStateRevisionRead:
    revision = await service.reconcile(
        organization_id,
        initiative_id,
        project_id,
        expected_version=payload.expected_version,
        idempotency_key=payload.idempotency_key,
        schema_version=payload.schema_version,
        state=payload.state,
        source_provider=payload.source.provider,
        source_kind=payload.source.kind,
        source_event_id=payload.source.event_id,
        source_uri=payload.source.uri,
        source_occurred_at=payload.source.occurred_at,
        assertion_status=payload.assertion.status,
        confidence=payload.assertion.confidence,
        confidence_explanation=payload.assertion.explanation,
    )
    return _read(revision)
