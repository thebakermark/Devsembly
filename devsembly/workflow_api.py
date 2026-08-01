from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from devsembly.auth import authorize_request, internal_control_authorized
from devsembly.domain import (
    WorkflowRunDetail,
    WorkflowRunStatus,
    WorkflowStepDefinition,
    WorkflowStepDetail,
)
from devsembly.unit_of_work import SqlAlchemyUnitOfWork
from devsembly.workflow_schemas import (
    WorkflowRunCancellationRequest,
    WorkflowRunCreate,
    WorkflowRunDetailRead,
    WorkflowRunRead,
    WorkflowRunRetryRequest,
    WorkflowRunStatusUpdate,
    WorkflowStepAttemptRead,
    WorkflowStepAttemptRecord,
    WorkflowStepDetailRead,
    WorkflowStepRead,
)
from devsembly.workflow_service import WorkflowService

router = APIRouter(
    prefix="/api/v1/organizations",
    tags=["Genesis workflow runs"],
    dependencies=[Depends(authorize_request)],
)
internal_router = APIRouter(
    prefix="/api/v1/internal/organizations",
    tags=["Genesis workflow control"],
    dependencies=[Depends(internal_control_authorized)],
)

PROJECT_RUNS_PATH = (
    "/{organization_id}/initiatives/{initiative_id}/projects/{project_id}/workflow-runs"
)


def get_workflow_service() -> WorkflowService:
    return WorkflowService(lambda: SqlAlchemyUnitOfWork())


Service = Annotated[WorkflowService, Depends(get_workflow_service)]


def _step_detail_read(detail: WorkflowStepDetail) -> WorkflowStepDetailRead:
    return WorkflowStepDetailRead(
        step=WorkflowStepRead.model_validate(detail.step),
        attempts=[WorkflowStepAttemptRead.model_validate(attempt) for attempt in detail.attempts],
    )


def _run_detail_read(detail: WorkflowRunDetail) -> WorkflowRunDetailRead:
    return WorkflowRunDetailRead(
        run=WorkflowRunRead.model_validate(detail.run),
        steps=[_step_detail_read(step) for step in detail.steps],
    )


@router.post(
    PROJECT_RUNS_PATH,
    response_model=WorkflowRunDetailRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_workflow_run(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    payload: WorkflowRunCreate,
    response: Response,
    service: Service,
) -> WorkflowRunDetailRead:
    detail, created = await service.create_workflow_run(
        organization_id,
        initiative_id,
        project_id,
        workflow_kind=payload.workflow_kind,
        idempotency_key=payload.idempotency_key,
        input_payload=payload.input_payload,
        steps=[WorkflowStepDefinition(key=step.key, name=step.name) for step in payload.steps],
    )
    if not created:
        response.status_code = status.HTTP_200_OK
    return _run_detail_read(detail)


@router.get(PROJECT_RUNS_PATH, response_model=list[WorkflowRunRead])
async def list_workflow_runs(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    service: Service,
) -> list[WorkflowRunRead]:
    workflow_runs = await service.list_workflow_runs(organization_id, initiative_id, project_id)
    return [WorkflowRunRead.model_validate(workflow_run) for workflow_run in workflow_runs]


@router.get(
    f"{PROJECT_RUNS_PATH}/{{workflow_run_id}}",
    response_model=WorkflowRunDetailRead,
)
async def get_workflow_run(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    workflow_run_id: uuid.UUID,
    service: Service,
) -> WorkflowRunDetailRead:
    detail = await service.get_workflow_run(
        organization_id,
        initiative_id,
        project_id,
        workflow_run_id,
    )
    return _run_detail_read(detail)


@router.put(
    f"{PROJECT_RUNS_PATH}/{{workflow_run_id}}/status",
    response_model=WorkflowRunDetailRead,
)
async def update_workflow_run_status(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    workflow_run_id: uuid.UUID,
    payload: WorkflowRunStatusUpdate,
    service: Service,
) -> WorkflowRunDetailRead:
    detail = await service.update_workflow_run_status(
        organization_id,
        initiative_id,
        project_id,
        workflow_run_id,
        payload.expected_version,
        target_status=WorkflowRunStatus(payload.status.value),
        temporal_workflow_id=payload.temporal_workflow_id,
    )
    return _run_detail_read(detail)


@router.post(
    f"{PROJECT_RUNS_PATH}/{{workflow_run_id}}/cancel",
    response_model=WorkflowRunDetailRead,
)
async def request_workflow_run_cancellation(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    workflow_run_id: uuid.UUID,
    payload: WorkflowRunCancellationRequest,
    service: Service,
) -> WorkflowRunDetailRead:
    detail = await service.request_workflow_run_cancellation(
        organization_id,
        initiative_id,
        project_id,
        workflow_run_id,
        payload.expected_version,
    )
    return _run_detail_read(detail)


@router.post(
    f"{PROJECT_RUNS_PATH}/{{workflow_run_id}}/retry",
    response_model=WorkflowRunDetailRead,
    status_code=status.HTTP_201_CREATED,
)
async def retry_workflow_run(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    workflow_run_id: uuid.UUID,
    payload: WorkflowRunRetryRequest,
    response: Response,
    service: Service,
) -> WorkflowRunDetailRead:
    detail, created = await service.retry_workflow_run(
        organization_id,
        initiative_id,
        project_id,
        workflow_run_id,
        payload.expected_version,
        idempotency_key=payload.idempotency_key,
    )
    if not created:
        response.status_code = status.HTTP_200_OK
    return _run_detail_read(detail)


@internal_router.post(
    f"{PROJECT_RUNS_PATH}/{{workflow_run_id}}/steps/{{workflow_step_id}}/attempts",
    response_model=WorkflowStepDetailRead,
    status_code=status.HTTP_201_CREATED,
)
async def record_workflow_step_attempt(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    workflow_run_id: uuid.UUID,
    workflow_step_id: uuid.UUID,
    payload: WorkflowStepAttemptRecord,
    service: Service,
) -> WorkflowStepDetailRead:
    detail = await service.record_workflow_step_attempt(
        organization_id,
        initiative_id,
        project_id,
        workflow_run_id,
        workflow_step_id,
        payload.expected_step_version,
        status=payload.status,
        result_payload=payload.result_payload,
        error_payload=payload.error_payload,
        started_at=payload.started_at,
    )
    return _step_detail_read(detail)
