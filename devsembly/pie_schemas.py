from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from devsembly.domain import ProjectGraphKind, ProjectStateAssertionStatus, ProjectWorkItemKind

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


class ProjectionRebuild(BaseModel):
    version: int = Field(ge=1)


class ProviderAliasRead(BaseModel):
    provider: str
    account: str
    kind: str
    external_id: str
    uri: str | None


class ProjectionProvenanceRead(BaseModel):
    provider: str
    kind: str
    external_id: str | None
    uri: str | None
    occurred_at: datetime | None
    observed_at: datetime


class ProjectWorkItemRead(BaseModel):
    id: str
    kind: ProjectWorkItemKind
    title: str
    status: str
    parent_id: str | None
    source_revision_id: uuid.UUID
    provenance: ProjectionProvenanceRead
    assertion: ProjectStateAssertionRead
    aliases: list[ProviderAliasRead]


class ProjectGraphNodeRead(BaseModel):
    id: str
    kind: str
    title: str
    status: str
    source_revision_id: uuid.UUID
    provenance: ProjectionProvenanceRead
    assertion: ProjectStateAssertionRead
    aliases: list[ProviderAliasRead]


class ProjectGraphEdgeRead(BaseModel):
    id: str
    from_id: str
    to_id: str
    relationship: str
    source_revision_id: uuid.UUID
    provenance: ProjectionProvenanceRead
    assertion: ProjectStateAssertionRead


class ProjectGraphRead(BaseModel):
    kind: ProjectGraphKind
    source_revision_id: uuid.UUID
    source_version: int
    nodes: list[ProjectGraphNodeRead]
    edges: list[ProjectGraphEdgeRead]


class AssuranceItemRead(BaseModel):
    id: str
    title: str
    status: str
    owner_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    acceptance_criterion_ids: list[str] = Field(default_factory=list)
    stale_at: datetime | None = None
    superseded_by: str | None = None
    likelihood: Decimal | None = None
    impact_score: Decimal | None = None
    mitigation: str | None = None
    trigger: str | None = None
    review_at: datetime | None = None
    principal: Decimal | None = None
    interest: Decimal | None = None
    impact: str | None = None
    retirement_criteria: str | None = None
    affected_capability_ids: list[str] = Field(default_factory=list)
    affected_dependency_ids: list[str] = Field(default_factory=list)
    source_revision_id: uuid.UUID
    provenance: ProjectionProvenanceRead
    assertion: ProjectStateAssertionRead


class ExecutiveAssuranceRead(BaseModel):
    validation_status: str
    verified_claims: int
    unverified_claims: int
    stale_claims: int
    open_risks: int
    risk_exposure: Decimal
    open_debt_items: int
    debt_principal: Decimal
    debt_interest: Decimal


class ProjectIntelligenceProjectionRead(BaseModel):
    project_id: uuid.UUID
    source_revision_id: uuid.UUID
    source_version: int
    rebuilt_at: datetime
    work_items: list[ProjectWorkItemRead]
    graphs: list[ProjectGraphRead]
    validation_results: list[AssuranceItemRead]
    risks: list[AssuranceItemRead]
    technical_debt: list[AssuranceItemRead]
    executive_assurance: ExecutiveAssuranceRead
