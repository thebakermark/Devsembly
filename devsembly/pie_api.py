from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from devsembly.auth import authorize_request
from devsembly.domain import (
    ProjectGraphEdge,
    ProjectGraphKind,
    ProjectGraphNode,
    ProjectIntelligenceProjection,
    ProjectProviderAlias,
    ProjectStateRevision,
    ProjectWorkItem,
)
from devsembly.pie_schemas import (
    ProjectGraphEdgeRead,
    ProjectGraphNodeRead,
    ProjectGraphRead,
    ProjectIntelligenceProjectionRead,
    ProjectionProvenanceRead,
    ProjectionRebuild,
    ProjectStateAssertionRead,
    ProjectStateReconcile,
    ProjectStateRevisionRead,
    ProjectStateSourceRead,
    ProjectWorkItemRead,
    ProviderAliasRead,
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


def _alias_read(alias: ProjectProviderAlias) -> ProviderAliasRead:
    return ProviderAliasRead(
        provider=alias.provider,
        account=alias.account,
        kind=alias.external_kind,
        external_id=alias.external_id,
        uri=alias.uri,
    )


def _aliases_for(
    projection: ProjectIntelligenceProjection, canonical_id: str
) -> list[ProviderAliasRead]:
    return [
        _alias_read(alias) for alias in projection.aliases if alias.canonical_id == canonical_id
    ]


def _provenance_read(
    item: ProjectWorkItem | ProjectGraphNode | ProjectGraphEdge,
) -> ProjectionProvenanceRead:
    return ProjectionProvenanceRead(
        provider=item.source_provider,
        kind=item.source_kind,
        external_id=item.source_external_id,
        uri=item.source_uri,
        occurred_at=item.source_occurred_at,
        observed_at=item.source_observed_at,
    )


def _assertion_read(
    item: ProjectWorkItem | ProjectGraphNode | ProjectGraphEdge,
) -> ProjectStateAssertionRead:
    return ProjectStateAssertionRead(
        status=item.assertion_status,
        confidence=item.confidence,
        explanation=item.confidence_explanation,
    )


def _work_item_read(
    projection: ProjectIntelligenceProjection, item: ProjectWorkItem
) -> ProjectWorkItemRead:
    return ProjectWorkItemRead(
        id=item.stable_id,
        kind=item.kind,
        title=item.title,
        status=item.status,
        parent_id=item.parent_stable_id,
        source_revision_id=item.source_revision_id,
        provenance=_provenance_read(item),
        assertion=_assertion_read(item),
        aliases=_aliases_for(projection, item.stable_id),
    )


def _graph_read(
    projection: ProjectIntelligenceProjection, graph_kind: ProjectGraphKind
) -> ProjectGraphRead:
    nodes = [item for item in projection.graph_nodes if item.graph_kind == graph_kind]
    edges = [item for item in projection.graph_edges if item.graph_kind == graph_kind]
    return ProjectGraphRead(
        kind=graph_kind,
        source_revision_id=projection.checkpoint.source_revision_id,
        source_version=projection.checkpoint.source_version,
        nodes=[
            ProjectGraphNodeRead(
                id=item.stable_id,
                kind=item.entity_kind,
                title=item.title,
                status=item.status,
                source_revision_id=item.source_revision_id,
                provenance=_provenance_read(item),
                assertion=_assertion_read(item),
                aliases=_aliases_for(projection, item.stable_id),
            )
            for item in nodes
        ],
        edges=[
            ProjectGraphEdgeRead(
                id=item.stable_id,
                from_id=item.from_stable_id,
                to_id=item.to_stable_id,
                relationship=item.relationship,
                source_revision_id=item.source_revision_id,
                provenance=_provenance_read(item),
                assertion=_assertion_read(item),
            )
            for item in edges
        ],
    )


def _projection_read(
    projection: ProjectIntelligenceProjection,
) -> ProjectIntelligenceProjectionRead:
    return ProjectIntelligenceProjectionRead(
        project_id=projection.checkpoint.project_id,
        source_revision_id=projection.checkpoint.source_revision_id,
        source_version=projection.checkpoint.source_version,
        rebuilt_at=projection.checkpoint.rebuilt_at,
        work_items=[_work_item_read(projection, item) for item in projection.work_items],
        graphs=[
            _graph_read(projection, ProjectGraphKind.CAPABILITY),
            _graph_read(projection, ProjectGraphKind.DEPENDENCY),
        ],
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


@router.get("/projection", response_model=ProjectIntelligenceProjectionRead)
async def get_project_intelligence_projection(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    service: Service,
) -> ProjectIntelligenceProjectionRead:
    return _projection_read(await service.projection(organization_id, initiative_id, project_id))


@router.get("/work-items", response_model=list[ProjectWorkItemRead])
async def list_project_work_items(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    service: Service,
) -> list[ProjectWorkItemRead]:
    projection = await service.projection(organization_id, initiative_id, project_id)
    return [_work_item_read(projection, item) for item in projection.work_items]


@router.get("/graphs/{graph_kind}", response_model=ProjectGraphRead)
async def get_project_graph(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    graph_kind: ProjectGraphKind,
    service: Service,
) -> ProjectGraphRead:
    projection = await service.projection(organization_id, initiative_id, project_id)
    return _graph_read(projection, graph_kind)


@router.post("/projection/rebuild", response_model=ProjectIntelligenceProjectionRead)
async def rebuild_project_intelligence_projection(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    payload: ProjectionRebuild,
    service: Service,
) -> ProjectIntelligenceProjectionRead:
    projection = await service.rebuild_projection(
        organization_id, initiative_id, project_id, payload.version
    )
    return _projection_read(projection)


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
