from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError

from devsembly.auth import AuthorizedPrincipal, authorize_request, internal_control_authorized
from devsembly.github_sync import (
    GitHubSynchronizationService,
    InvalidGitHubEvent,
    InvalidGitHubSignature,
    normalize_event,
    normalize_snapshot_entity,
    verify_signature,
)
from devsembly.temporal_workflows import GitHubSnapshotWorkflow

router = APIRouter(prefix="/api/v1/internal/projects/{project_id}/github", tags=["GitHub Sync"])
conflict_router = APIRouter(
    prefix=(
        "/api/v1/organizations/{organization_id}/initiatives/{initiative_id}"
        "/projects/{project_id}/project-intelligence/github-conflicts"
    ),
    tags=["GitHub Sync"],
    dependencies=[Depends(authorize_request)],
)


class SnapshotEntity(BaseModel):
    kind: str = Field(min_length=1, max_length=80)
    payload: dict[str, object]


class SnapshotReconciliationRequest(BaseModel):
    repository_id: str = Field(min_length=1, max_length=80)
    entities: list[SnapshotEntity] = Field(max_length=500)


class SnapshotScheduleRequest(BaseModel):
    repository_id: str = Field(min_length=1, max_length=80)
    repository: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", max_length=200)
    interval_seconds: int = Field(default=1800, ge=300, le=86400)


class ConflictResolutionRequest(BaseModel):
    resolution: Literal["keep_current", "accept_incoming"]
    reason: str = Field(min_length=1, max_length=2000)


class ConflictRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    entity_id: str
    current_sha256: str
    incoming_sha256: str
    current_authority: str
    incoming_authority: str
    reason: str
    status: str
    created_at: datetime
    resolved_at: datetime | None
    resolution: str | None
    resolution_reason: str | None
    resolved_by: uuid.UUID | None


@conflict_router.get("", response_model=list[ConflictRead])
async def list_github_conflicts(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    conflict_status: Literal["open", "resolved"] = "open",
) -> list[ConflictRead]:
    conflicts = await GitHubSynchronizationService().list_conflicts(
        organization_id, initiative_id, project_id, status=conflict_status
    )
    return [ConflictRead.model_validate(item, from_attributes=True) for item in conflicts]


@conflict_router.post("/{conflict_id}/resolve", response_model=ConflictRead)
async def resolve_github_conflict(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    conflict_id: uuid.UUID,
    request: ConflictResolutionRequest,
    principal: AuthorizedPrincipal,
) -> ConflictRead:
    try:
        result = await GitHubSynchronizationService().resolve_conflict(
            organization_id,
            initiative_id,
            project_id,
            conflict_id,
            resolution=request.resolution,
            reason=request.reason,
            principal_id=principal.principal_id,
        )
    except InvalidGitHubEvent as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ConflictRead.model_validate(result, from_attributes=True)


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
async def ingest_github_event(
    project_id: uuid.UUID,
    request: Request,
    delivery_id: Annotated[str, Header(alias="X-GitHub-Delivery", min_length=1, max_length=100)],
    event_name: Annotated[str, Header(alias="X-GitHub-Event", min_length=1, max_length=80)],
    signature: Annotated[str | None, Header(alias="X-Hub-Signature-256")] = None,
) -> dict[str, object]:
    body = await request.body()
    try:
        verify_signature(body, signature, os.getenv("DEVSEMBLY_GITHUB_WEBHOOK_SECRET", ""))
        event = normalize_event(body, delivery_id, event_name)
        result = await GitHubSynchronizationService().ingest(project_id, event)
    except InvalidGitHubSignature as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except InvalidGitHubEvent as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    return {
        "delivery_id": result.delivery_id,
        "entity_id": result.entity_id,
        "status": result.status,
        "duplicate": result.duplicate,
        "out_of_order": result.out_of_order,
        "conflict_id": result.conflict_id,
        "reconciliation_required": result.reconciliation_required,
    }


@router.post(
    "/snapshot-reconciliations",
    dependencies=[Depends(internal_control_authorized)],
)
async def reconcile_github_snapshot(
    project_id: uuid.UUID,
    request: SnapshotReconciliationRequest,
) -> dict[str, object]:
    try:
        events = [
            normalize_snapshot_entity(request.repository_id, item.kind, item.payload)
            for item in request.entities
        ]
        result = await GitHubSynchronizationService().reconcile_snapshot(
            project_id, request.repository_id, events
        )
    except InvalidGitHubEvent as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    return {
        "repository_id": result.repository_id,
        "processed": result.processed,
        "duplicates": result.duplicates,
        "conflicts": result.conflicts,
        "out_of_order": result.out_of_order,
        "stale_sources": result.stale_sources,
    }


@router.post(
    "/snapshot-schedule",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(internal_control_authorized)],
)
async def schedule_github_snapshot(
    project_id: uuid.UUID,
    request: SnapshotScheduleRequest,
) -> dict[str, object]:
    workflow_id = f"genesis-github-snapshot-{project_id}-{request.repository_id}"
    client = await Client.connect(os.getenv("DEVSEMBLY_TEMPORAL_ADDRESS", "localhost:7233"))
    created = True
    try:
        await client.start_workflow(
            GitHubSnapshotWorkflow.run,
            {
                "project_id": str(project_id),
                "repository_id": request.repository_id,
                "repository": request.repository,
                "interval_seconds": request.interval_seconds,
            },
            id=workflow_id,
            task_queue=os.getenv("DEVSEMBLY_TEMPORAL_TASK_QUEUE", "devsembly-factory"),
            id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
        )
    except WorkflowAlreadyStartedError:
        created = False
    return {"workflow_id": workflow_id, "created": created, "status": "scheduled"}
