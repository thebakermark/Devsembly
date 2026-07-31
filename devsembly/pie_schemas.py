from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from devsembly.domain import ProjectStateAssertionStatus

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ProjectStateSource(BaseModel):
    provider: NonEmptyText = Field(max_length=80)
    kind: NonEmptyText = Field(max_length=80)
    event_id: str | None = Field(default=None, max_length=255)
    uri: str | None = Field(default=None, max_length=1000)
    occurred_at: datetime | None = None

    @field_validator("event_id", "uri")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ProjectStateAssertion(BaseModel):
    status: ProjectStateAssertionStatus
    confidence: Decimal = Field(ge=Decimal(0), le=Decimal(1), max_digits=5, decimal_places=4)
    explanation: NonEmptyText = Field(max_length=2000)


class ProjectStateReconcile(BaseModel):
    expected_version: int = Field(ge=0)
    idempotency_key: NonEmptyText = Field(max_length=200)
    schema_version: NonEmptyText = Field(max_length=40)
    state: dict[str, object]
    source: ProjectStateSource
    assertion: ProjectStateAssertion

    @field_validator("state")
    @classmethod
    def require_state(cls, value: dict[str, object]) -> dict[str, object]:
        if not value:
            raise ValueError("state must contain at least one field")
        return value


class ProjectStateSourceRead(BaseModel):
    provider: str
    kind: str
    event_id: str | None
    uri: str | None
    occurred_at: datetime | None
    observed_at: datetime


class ProjectStateAssertionRead(BaseModel):
    status: ProjectStateAssertionStatus
    confidence: Decimal
    explanation: str


class ProjectStateRevisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    version: int
    parent_revision_id: uuid.UUID | None
    schema_version: str
    state: dict[str, object]
    state_sha256: str
    source: ProjectStateSourceRead
    assertion: ProjectStateAssertionRead
    created_at: datetime
