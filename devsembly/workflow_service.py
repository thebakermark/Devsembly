from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from devsembly.domain import (
    OutboxMessage,
    Project,
    WorkflowAttemptStatus,
    WorkflowRun,
    WorkflowRunDetail,
    WorkflowRunStatus,
    WorkflowStep,
    WorkflowStepAttempt,
    WorkflowStepDefinition,
    WorkflowStepDetail,
    WorkflowStepStatus,
)
from devsembly.errors import (
    IdempotencyConflictError,
    InvalidTransitionError,
    ResourceNotFoundError,
    StaleVersionError,
)
from devsembly.unit_of_work import UnitOfWork

UnitOfWorkFactory = Callable[[], UnitOfWork]
Clock = Callable[[], datetime]

RUN_TRANSITIONS: dict[WorkflowRunStatus, frozenset[WorkflowRunStatus]] = {
    WorkflowRunStatus.ACCEPTED: frozenset(
        {WorkflowRunStatus.QUEUED, WorkflowRunStatus.CANCELLATION_REQUESTED}
    ),
    WorkflowRunStatus.QUEUED: frozenset(
        {
            WorkflowRunStatus.RUNNING,
            WorkflowRunStatus.FAILED,
            WorkflowRunStatus.CANCELLATION_REQUESTED,
        }
    ),
    WorkflowRunStatus.RUNNING: frozenset(
        {
            WorkflowRunStatus.SUCCEEDED,
            WorkflowRunStatus.FAILED,
            WorkflowRunStatus.CANCELLATION_REQUESTED,
        }
    ),
    WorkflowRunStatus.CANCELLATION_REQUESTED: frozenset(
        {WorkflowRunStatus.CANCELLED, WorkflowRunStatus.FAILED}
    ),
    WorkflowRunStatus.SUCCEEDED: frozenset(),
    WorkflowRunStatus.FAILED: frozenset(),
    WorkflowRunStatus.CANCELLED: frozenset(),
}


def _utc_now() -> datetime:
    return datetime.now(UTC)


class WorkflowService:
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

    async def create_workflow_run(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
        *,
        workflow_kind: str,
        idempotency_key: str,
        input_payload: dict[str, object],
        steps: Sequence[WorkflowStepDefinition],
    ) -> tuple[WorkflowRunDetail, bool]:
        async with self._unit_of_work() as unit:
            await self._require_project(unit, organization_id, initiative_id, project_id)
            existing = await unit.workflow_runs.get_by_idempotency_key(project_id, idempotency_key)
            if existing is not None:
                detail = await self._detail(unit, existing)
                if self._matches_request(
                    detail,
                    workflow_kind=workflow_kind,
                    input_payload=input_payload,
                    steps=steps,
                    retry_of_run_id=None,
                ):
                    return detail, False
                raise IdempotencyConflictError(idempotency_key)

            now = self._clock()
            workflow_run = WorkflowRun(
                id=uuid.uuid4(),
                project_id=project_id,
                workflow_kind=workflow_kind,
                idempotency_key=idempotency_key,
                input_payload=dict(input_payload),
                status=WorkflowRunStatus.ACCEPTED,
                temporal_workflow_id=None,
                retry_of_run_id=None,
                cost_estimate=None,
                version=1,
                cancellation_requested_at=None,
                started_at=None,
                completed_at=None,
                created_at=now,
                updated_at=now,
            )
            workflow_steps = tuple(
                WorkflowStep(
                    id=uuid.uuid4(),
                    workflow_run_id=workflow_run.id,
                    key=definition.key,
                    name=definition.name,
                    position=position,
                    status=WorkflowStepStatus.PENDING,
                    version=1,
                    created_at=now,
                    updated_at=now,
                )
                for position, definition in enumerate(steps)
            )

            await unit.workflow_runs.add(workflow_run)
            for workflow_step in workflow_steps:
                await unit.workflow_steps.add(workflow_step)
            await unit.outbox.add(
                self._message(
                    "genesis.workflow_run.created",
                    workflow_run.id,
                    {
                        "organization_id": str(organization_id),
                        "initiative_id": str(initiative_id),
                        "project_id": str(project_id),
                        "workflow_run_id": str(workflow_run.id),
                        "workflow_kind": workflow_kind,
                        "version": 1,
                    },
                )
            )
            await unit.commit()
            return self._empty_attempt_detail(workflow_run, workflow_steps), True

    async def get_workflow_run(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
        workflow_run_id: uuid.UUID,
    ) -> WorkflowRunDetail:
        async with self._unit_of_work() as unit:
            await self._require_project(unit, organization_id, initiative_id, project_id)
            workflow_run = await self._require_workflow_run(unit, project_id, workflow_run_id)
            return await self._detail(unit, workflow_run)

    async def list_workflow_runs(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> Sequence[WorkflowRun]:
        async with self._unit_of_work() as unit:
            await self._require_project(unit, organization_id, initiative_id, project_id)
            return await unit.workflow_runs.list(project_id)

    async def update_workflow_run_status(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
        workflow_run_id: uuid.UUID,
        expected_version: int,
        *,
        target_status: WorkflowRunStatus,
        temporal_workflow_id: str | None,
    ) -> WorkflowRunDetail:
        async with self._unit_of_work() as unit:
            await self._require_project(unit, organization_id, initiative_id, project_id)
            current = await self._require_workflow_run(unit, project_id, workflow_run_id)
            self._require_expected_version(current, expected_version)
            self._require_run_transition(current.status, target_status)
            if target_status is WorkflowRunStatus.SUCCEEDED:
                steps = await unit.workflow_steps.list(current.id)
                if any(
                    step.status not in {WorkflowStepStatus.SUCCEEDED, WorkflowStepStatus.SKIPPED}
                    for step in steps
                ):
                    raise InvalidTransitionError(
                        "workflow run steps",
                        ",".join(step.status.value for step in steps),
                        target_status.value,
                    )

            resolved_temporal_id = self._resolve_temporal_workflow_id(
                current, target_status, temporal_workflow_id
            )
            now = self._clock()
            updated = await unit.workflow_runs.update_status(
                project_id,
                workflow_run_id,
                expected_version,
                status=target_status.value,
                temporal_workflow_id=resolved_temporal_id,
                cancellation_requested_at=current.cancellation_requested_at,
                started_at=(
                    now
                    if target_status is WorkflowRunStatus.RUNNING and current.started_at is None
                    else current.started_at
                ),
                completed_at=(
                    now
                    if target_status
                    in {
                        WorkflowRunStatus.SUCCEEDED,
                        WorkflowRunStatus.FAILED,
                        WorkflowRunStatus.CANCELLED,
                    }
                    else current.completed_at
                ),
            )
            if updated is None:
                raise ResourceNotFoundError("workflow run")
            await unit.outbox.add(
                self._message(
                    "genesis.workflow_run.status_changed",
                    updated.id,
                    self._run_event_payload(
                        organization_id, initiative_id, updated, previous_status=current.status
                    ),
                )
            )
            detail = await self._detail(unit, updated)
            await unit.commit()
            return detail

    async def request_workflow_run_cancellation(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
        workflow_run_id: uuid.UUID,
        expected_version: int,
    ) -> WorkflowRunDetail:
        async with self._unit_of_work() as unit:
            await self._require_project(unit, organization_id, initiative_id, project_id)
            current = await self._require_workflow_run(unit, project_id, workflow_run_id)
            self._require_expected_version(current, expected_version)
            target_status = WorkflowRunStatus.CANCELLATION_REQUESTED
            self._require_run_transition(current.status, target_status)

            now = self._clock()
            updated = await unit.workflow_runs.update_status(
                project_id,
                workflow_run_id,
                expected_version,
                status=target_status.value,
                temporal_workflow_id=current.temporal_workflow_id,
                cancellation_requested_at=now,
                started_at=current.started_at,
                completed_at=current.completed_at,
            )
            if updated is None:
                raise ResourceNotFoundError("workflow run")
            await unit.outbox.add(
                self._message(
                    "genesis.workflow_run.cancellation_requested",
                    updated.id,
                    self._run_event_payload(
                        organization_id, initiative_id, updated, previous_status=current.status
                    ),
                )
            )
            detail = await self._detail(unit, updated)
            await unit.commit()
            return detail

    async def retry_workflow_run(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
        workflow_run_id: uuid.UUID,
        expected_version: int,
        *,
        idempotency_key: str,
    ) -> tuple[WorkflowRunDetail, bool]:
        async with self._unit_of_work() as unit:
            await self._require_project(unit, organization_id, initiative_id, project_id)
            source = await self._require_workflow_run(unit, project_id, workflow_run_id)
            self._require_expected_version(source, expected_version)
            if source.status not in {
                WorkflowRunStatus.FAILED,
                WorkflowRunStatus.CANCELLED,
            }:
                raise InvalidTransitionError("workflow run", source.status.value, "retry")
            source_detail = await self._detail(unit, source)
            source_definitions = tuple(
                WorkflowStepDefinition(key=item.step.key, name=item.step.name)
                for item in source_detail.steps
            )

            existing = await unit.workflow_runs.get_by_idempotency_key(project_id, idempotency_key)
            if existing is not None:
                detail = await self._detail(unit, existing)
                if self._matches_request(
                    detail,
                    workflow_kind=source.workflow_kind,
                    input_payload=source.input_payload,
                    steps=source_definitions,
                    retry_of_run_id=source.id,
                ):
                    return detail, False
                raise IdempotencyConflictError(idempotency_key)

            now = self._clock()
            retry_run = WorkflowRun(
                id=uuid.uuid4(),
                project_id=project_id,
                workflow_kind=source.workflow_kind,
                idempotency_key=idempotency_key,
                input_payload=dict(source.input_payload),
                status=WorkflowRunStatus.ACCEPTED,
                temporal_workflow_id=None,
                retry_of_run_id=source.id,
                cost_estimate=source.cost_estimate,
                version=1,
                cancellation_requested_at=None,
                started_at=None,
                completed_at=None,
                created_at=now,
                updated_at=now,
            )
            retry_steps = tuple(
                WorkflowStep(
                    id=uuid.uuid4(),
                    workflow_run_id=retry_run.id,
                    key=definition.key,
                    name=definition.name,
                    position=position,
                    status=WorkflowStepStatus.PENDING,
                    version=1,
                    created_at=now,
                    updated_at=now,
                )
                for position, definition in enumerate(source_definitions)
            )
            await unit.workflow_runs.add(retry_run)
            for step in retry_steps:
                await unit.workflow_steps.add(step)
            await unit.outbox.add(
                self._message(
                    "genesis.workflow_run.retry_created",
                    retry_run.id,
                    {
                        "organization_id": str(organization_id),
                        "initiative_id": str(initiative_id),
                        "project_id": str(project_id),
                        "workflow_run_id": str(retry_run.id),
                        "retry_of_run_id": str(source.id),
                        "version": 1,
                    },
                )
            )
            await unit.commit()
            return self._empty_attempt_detail(retry_run, retry_steps), True

    async def record_workflow_step_attempt(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
        workflow_run_id: uuid.UUID,
        workflow_step_id: uuid.UUID,
        expected_step_version: int,
        *,
        status: WorkflowAttemptStatus,
        result_payload: dict[str, object] | None,
        error_payload: dict[str, object] | None,
        started_at: datetime | None,
    ) -> WorkflowStepDetail:
        async with self._unit_of_work() as unit:
            await self._require_project(unit, organization_id, initiative_id, project_id)
            workflow_run = await self._require_workflow_run(unit, project_id, workflow_run_id)
            if workflow_run.status is not WorkflowRunStatus.RUNNING:
                raise InvalidTransitionError(
                    "workflow run", workflow_run.status.value, "record_step_attempt"
                )
            current_step = await unit.workflow_steps.get(workflow_run_id, workflow_step_id)
            if current_step is None:
                raise ResourceNotFoundError("workflow step")
            if current_step.version != expected_step_version:
                raise StaleVersionError("workflow step", expected_step_version)
            if current_step.status not in {
                WorkflowStepStatus.PENDING,
                WorkflowStepStatus.RUNNING,
                WorkflowStepStatus.FAILED,
            }:
                raise InvalidTransitionError(
                    "workflow step", current_step.status.value, status.value
                )

            attempts = await unit.workflow_step_attempts.list(workflow_step_id)
            completed_at = self._clock()
            resolved_started_at = started_at or completed_at
            if resolved_started_at > completed_at:
                raise InvalidTransitionError("workflow step attempt", "not_started", "completed")
            attempt = WorkflowStepAttempt(
                id=uuid.uuid4(),
                workflow_step_id=workflow_step_id,
                attempt_number=len(attempts) + 1,
                status=status,
                result_payload=None if result_payload is None else dict(result_payload),
                error_payload=None if error_payload is None else dict(error_payload),
                started_at=resolved_started_at,
                completed_at=completed_at,
                created_at=completed_at,
            )
            target_step_status = WorkflowStepStatus(status.value)
            await unit.workflow_step_attempts.add(attempt)
            updated_step = await unit.workflow_steps.update_status(
                workflow_run_id,
                workflow_step_id,
                expected_step_version,
                status=target_step_status.value,
            )
            if updated_step is None:
                raise ResourceNotFoundError("workflow step")
            await unit.outbox.add(
                self._message(
                    "genesis.workflow_step.attempt_recorded",
                    updated_step.id,
                    {
                        "organization_id": str(organization_id),
                        "initiative_id": str(initiative_id),
                        "project_id": str(project_id),
                        "workflow_run_id": str(workflow_run_id),
                        "workflow_step_id": str(updated_step.id),
                        "attempt_id": str(attempt.id),
                        "attempt_number": attempt.attempt_number,
                        "status": attempt.status.value,
                        "step_version": updated_step.version,
                    },
                )
            )
            await unit.commit()
            return WorkflowStepDetail(step=updated_step, attempts=(*attempts, attempt))

    @staticmethod
    def _require_expected_version(workflow_run: WorkflowRun, expected_version: int) -> None:
        if workflow_run.version != expected_version:
            raise StaleVersionError("workflow run", expected_version)

    @staticmethod
    def _require_run_transition(
        current_status: WorkflowRunStatus, target_status: WorkflowRunStatus
    ) -> None:
        if target_status not in RUN_TRANSITIONS[current_status]:
            raise InvalidTransitionError("workflow run", current_status.value, target_status.value)

    @staticmethod
    def _resolve_temporal_workflow_id(
        workflow_run: WorkflowRun,
        target_status: WorkflowRunStatus,
        supplied_temporal_workflow_id: str | None,
    ) -> str | None:
        current_id = workflow_run.temporal_workflow_id
        if (
            current_id is not None
            and supplied_temporal_workflow_id is not None
            and current_id != supplied_temporal_workflow_id
        ):
            raise InvalidTransitionError(
                "workflow run correlation",
                current_id,
                supplied_temporal_workflow_id,
            )
        if (
            current_id is None
            and supplied_temporal_workflow_id is not None
            and target_status is not WorkflowRunStatus.QUEUED
        ):
            raise InvalidTransitionError(
                "workflow run correlation",
                "unassigned",
                target_status.value,
            )
        resolved = supplied_temporal_workflow_id or current_id
        if target_status is WorkflowRunStatus.QUEUED and resolved is None:
            raise InvalidTransitionError(
                "workflow run", workflow_run.status.value, "queued_without_provider_id"
            )
        return resolved

    @staticmethod
    async def _require_project(
        unit: UnitOfWork,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> Project:
        initiative = await unit.initiatives.get(organization_id, initiative_id)
        if initiative is None:
            raise ResourceNotFoundError("initiative")
        project = await unit.projects.get(initiative_id, project_id)
        if project is None:
            raise ResourceNotFoundError("project")
        return project

    @staticmethod
    async def _require_workflow_run(
        unit: UnitOfWork, project_id: uuid.UUID, workflow_run_id: uuid.UUID
    ) -> WorkflowRun:
        workflow_run = await unit.workflow_runs.get(project_id, workflow_run_id)
        if workflow_run is None:
            raise ResourceNotFoundError("workflow run")
        return workflow_run

    @staticmethod
    async def _detail(unit: UnitOfWork, workflow_run: WorkflowRun) -> WorkflowRunDetail:
        steps = await unit.workflow_steps.list(workflow_run.id)
        details = []
        for step in steps:
            attempts = await unit.workflow_step_attempts.list(step.id)
            details.append(WorkflowStepDetail(step=step, attempts=tuple(attempts)))
        return WorkflowRunDetail(run=workflow_run, steps=tuple(details))

    @staticmethod
    def _empty_attempt_detail(
        workflow_run: WorkflowRun, steps: Sequence[WorkflowStep]
    ) -> WorkflowRunDetail:
        return WorkflowRunDetail(
            run=workflow_run,
            steps=tuple(WorkflowStepDetail(step=step, attempts=()) for step in steps),
        )

    @staticmethod
    def _matches_request(
        detail: WorkflowRunDetail,
        *,
        workflow_kind: str,
        input_payload: dict[str, object],
        steps: Sequence[WorkflowStepDefinition],
        retry_of_run_id: uuid.UUID | None,
    ) -> bool:
        return (
            detail.run.workflow_kind == workflow_kind
            and detail.run.input_payload == input_payload
            and detail.run.retry_of_run_id == retry_of_run_id
            and [(item.step.key, item.step.name) for item in detail.steps]
            == [(item.key, item.name) for item in steps]
        )

    @staticmethod
    def _run_event_payload(
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        workflow_run: WorkflowRun,
        *,
        previous_status: WorkflowRunStatus,
    ) -> dict[str, object]:
        return {
            "organization_id": str(organization_id),
            "initiative_id": str(initiative_id),
            "project_id": str(workflow_run.project_id),
            "workflow_run_id": str(workflow_run.id),
            "previous_status": previous_status.value,
            "status": workflow_run.status.value,
            "version": workflow_run.version,
        }
