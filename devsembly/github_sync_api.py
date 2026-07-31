from __future__ import annotations

import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request, status

from devsembly.github_sync import (
    GitHubSynchronizationService,
    InvalidGitHubEvent,
    InvalidGitHubSignature,
    normalize_event,
    verify_signature,
)

router = APIRouter(prefix="/api/v1/internal/projects/{project_id}/github", tags=["GitHub Sync"])


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
