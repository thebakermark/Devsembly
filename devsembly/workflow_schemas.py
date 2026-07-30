from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from devsembly.domain import (
    WorkflowAttemptStatus,
    WorkflowRunStatus,
    WorkflowStepStatus,
)
from devsembly.genesis_schemas import ExpectedVersion


def _strip(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


WorkflowKind = Annotated[
    str,
    BeforeValidator(_strip),
    Field(min_length=1, max_length=120),
]
IdempotencyKey = Annotated[
    str,
    BeforeValidator(_strip),
    Field(min_length=1, max_length=200),
]
WorkflowStepKey = Annotated[
    str,
    BeforeValidator(_strip),
    Field(min_length=1, max_length=120),
]
WorkflowStepName = Annotated[
    str,
    BeforeValidator(_strip),
    Field(min_length=1, max_length=200),
]
TemporalWorkflowId = Annotated[
    str | None,
    BeforeValidator(_strip),
    Field(min_length=1, max_length=255),
]


class WorkflowRunAdvanceStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStepCreate(BaseModel):
    key: WorkflowStepKey
    name: WorkflowStepName


class WorkflowRunCreate(BaseModel):
    workflow_kind: WorkflowKind
    idempotency_key: IdempotencyKey
    input_payload: dict[str, object] = Field(default_factory=dict)
    steps: Annotated[list[WorkflowStepCreate], Field(min_length=1, max_length=100)]

    @model_validator(mode="after")
    def keys_are_unique(self) -> WorkflowRunCreate:
        keys = [step.key for step in self.steps]
        if len(keys) != len(set(keys)):
            raise ValueError("workflow step keys must be unique")
        return self


class WorkflowRunStatusUpdate(BaseModel):
    expected_version: ExpectedVersion
    status: WorkflowRunAdvanceStatus
    temporal_workflow_id: TemporalWorkflowId = None


class WorkflowRunCancellationRequest(BaseModel):
    expected_version: ExpectedVersion


class WorkflowRunRetryRequest(BaseModel):
    expected_version: ExpectedVersion
    idempotency_key: IdempotencyKey


class WorkflowStepAttemptRecord(BaseModel):
    expected_step_version: ExpectedVersion
    status: WorkflowAttemptStatus
    result_payload: dict[str, object] | None = None
    error_payload: dict[str, object] | None = None
    started_at: datetime | None = None

    @field_validator("started_at")
    @classmethod
    def started_at_has_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("started_at must include a timezone offset")
        return value

    @model_validator(mode="after")
    def payload_matches_status(self) -> WorkflowStepAttemptRecord:
        if self.status is WorkflowAttemptStatus.SUCCEEDED and (
            self.result_payload is None or self.error_payload is not None
        ):
            raise ValueError(
                "a succeeded attempt requires result_payload and forbids error_payload"
            )
        if self.status is WorkflowAttemptStatus.FAILED and self.error_payload is None:
            raise ValueError("a failed attempt requires error_payload")
        return self


class WorkflowRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    workflow_kind: str
    idempotency_key: str
    input_payload: dict[str, object]
    status: WorkflowRunStatus
    temporal_workflow_id: str | None
    retry_of_run_id: uuid.UUID | None
    cost_estimate: Decimal | None
    version: int
    cancellation_requested_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class WorkflowStepAttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workflow_step_id: uuid.UUID
    attempt_number: int
    status: WorkflowAttemptStatus
    result_payload: dict[str, object] | None
    error_payload: dict[str, object] | None
    started_at: datetime
    completed_at: datetime
    created_at: datetime


class WorkflowStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workflow_run_id: uuid.UUID
    key: str
    name: str
    position: int
    status: WorkflowStepStatus
    version: int
    created_at: datetime
    updated_at: datetime


class WorkflowStepDetailRead(BaseModel):
    step: WorkflowStepRead
    attempts: list[WorkflowStepAttemptRead]


class WorkflowRunDetailRead(BaseModel):
    run: WorkflowRunRead
    steps: list[WorkflowStepDetailRead]
