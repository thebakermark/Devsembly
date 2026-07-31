from __future__ import annotations

import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError

from devsembly.auth import internal_control_authorized
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
