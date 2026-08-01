from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from devsembly.domain import (
    MemoryKind,
    MemorySensitivity,
    MemoryStatus,
    ProjectStateAssertionStatus,
)

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class MemoryProposalCreate(BaseModel):
    kind: MemoryKind
    title: NonEmptyText = Field(max_length=500)
    content: NonEmptyText = Field(max_length=50_000)
    sensitivity: MemorySensitivity = MemorySensitivity.INTERNAL
    source_revision_id: uuid.UUID | None = None
    source_uri: str | None = Field(default=None, max_length=1000)
    assertion_status: ProjectStateAssertionStatus = ProjectStateAssertionStatus.INFERRED
    confidence: Decimal = Field(ge=0, le=1, max_digits=5, decimal_places=4)
    retention_until: datetime | None = None


class MemoryResolve(BaseModel):
    expected_version: int = Field(ge=1)
    reason: NonEmptyText = Field(max_length=2000)


class MemoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    kind: MemoryKind
    title: str
    content: str
    content_sha256: str
    status: MemoryStatus
    sensitivity: MemorySensitivity
    source_revision_id: uuid.UUID | None
    source_uri: str | None
    assertion_status: ProjectStateAssertionStatus
    confidence: Decimal
    retention_until: datetime | None
    superseded_by: uuid.UUID | None
    invalidated_at: datetime | None
    proposed_by: str
    decided_by: str | None
    decision_reason: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class ContextBuildRequest(BaseModel):
    task: NonEmptyText = Field(max_length=4000)
    token_budget: int = Field(ge=16, le=200_000)


class ContextPackageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    source_revision_id: uuid.UUID
    task: str
    token_budget: int
    tokens_used: int
    items: tuple[dict[str, object], ...]
    omissions: tuple[dict[str, object], ...]
    manifest_sha256: str
    invalidated_at: datetime | None
    created_by: str
    created_at: datetime
