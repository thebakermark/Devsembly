from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class InitiativeStatus(StrEnum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ProjectStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class BudgetEnforcementMode(StrEnum):
    OBSERVE = "observe"
    WARN = "warn"
    BLOCK = "block"


class CostCadence(StrEnum):
    ONE_TIME = "one_time"
    MONTHLY = "monthly"


class CostEvaluationOutcome(StrEnum):
    WITHIN_BUDGET = "within_budget"
    OBSERVED_OVERAGE = "observed_overage"
    APPROVAL_REQUIRED = "approval_required"
    BLOCKED = "blocked"


class DecisionStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"


class DecisionRisk(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class WorkflowRunStatus(StrEnum):
    ACCEPTED = "accepted"
    QUEUED = "queued"
    RUNNING = "running"
    CANCELLATION_REQUESTED = "cancellation_requested"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class WorkflowAttemptStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EvidenceKind(StrEnum):
    VALIDATION = "validation"
    SOURCE_CONTROL = "source_control"
    WORKFLOW = "workflow"
    OTHER = "other"


class EvidenceRetentionClass(StrEnum):
    TRANSIENT = "transient"
    STANDARD = "standard"
    COMPLIANCE = "compliance"
    PERMANENT = "permanent"


class ProjectStateAssertionStatus(StrEnum):
    VERIFIED = "verified"
    INFERRED = "inferred"
    DISPUTED = "disputed"


class ProjectWorkItemKind(StrEnum):
    ROADMAP = "roadmap"
    MILESTONE = "milestone"
    EPIC = "epic"
    FEATURE = "feature"
    TASK = "task"
    SPRINT = "sprint"


class ProjectGraphKind(StrEnum):
    CAPABILITY = "capability"
    DEPENDENCY = "dependency"


@dataclass(frozen=True, slots=True)
class Organization:
    id: uuid.UUID
    name: str
    version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Initiative:
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    objective: str
    status: InitiativeStatus
    version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Project:
    id: uuid.UUID
    initiative_id: uuid.UUID
    name: str
    repository: str | None
    status: ProjectStatus
    version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class Budget:
    id: uuid.UUID
    project_id: uuid.UUID
    monthly_limit: Decimal
    currency: str
    enforcement_mode: BudgetEnforcementMode
    version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class CostLineItem:
    category: str
    description: str
    cadence: CostCadence
    quantity: Decimal
    unit_cost: Decimal


@dataclass(frozen=True, slots=True)
class CostOptionDefinition:
    key: str
    name: str
    satisfies_acceptance_criteria: bool
    line_items: tuple[CostLineItem, ...]


@dataclass(frozen=True, slots=True)
class CostOption:
    key: str
    name: str
    satisfies_acceptance_criteria: bool
    line_items: tuple[CostLineItem, ...]
    one_time_cost: Decimal
    monthly_cost: Decimal


@dataclass(frozen=True, slots=True)
class CostRecommendation:
    option_key: str
    monthly_savings: Decimal
    one_time_savings: Decimal
    fits_monthly_budget: bool
    rationale: str
    algorithm_version: str


@dataclass(frozen=True, slots=True)
class CostEvaluation:
    id: uuid.UUID
    project_id: uuid.UUID
    budget_id: uuid.UUID
    workflow_run_id: uuid.UUID | None
    idempotency_key: str
    request_fingerprint: str
    currency: str
    budget_monthly_limit: Decimal
    budget_version: int
    enforcement_mode: BudgetEnforcementMode
    selected_option: CostOption
    alternatives: tuple[CostOption, ...]
    outcome: CostEvaluationOutcome
    monthly_overage: Decimal
    recommendation: CostRecommendation | None
    algorithm_version: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Decision:
    id: uuid.UUID
    project_id: uuid.UUID
    cost_evaluation_id: uuid.UUID | None
    title: str
    context: str
    selected_option: str
    alternatives: tuple[dict[str, object], ...]
    currency: str
    estimated_one_time_cost: Decimal
    estimated_monthly_cost: Decimal
    risk: DecisionRisk
    confidence: Decimal
    rationale: str
    status: DecisionStatus
    decided_by: str | None
    decision_note: str | None
    outcome: str | None
    authorization_budget_version: int | None
    authorization_monthly_limit: Decimal | None
    version: int
    decided_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class WorkflowRun:
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


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    id: uuid.UUID
    workflow_run_id: uuid.UUID
    key: str
    name: str
    position: int
    status: WorkflowStepStatus
    version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class WorkflowStepAttempt:
    id: uuid.UUID
    workflow_step_id: uuid.UUID
    attempt_number: int
    status: WorkflowAttemptStatus
    result_payload: dict[str, object] | None
    error_payload: dict[str, object] | None
    started_at: datetime
    completed_at: datetime
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Evidence:
    id: uuid.UUID
    project_id: uuid.UUID
    workflow_run_id: uuid.UUID | None
    workflow_step_attempt_id: uuid.UUID | None
    kind: EvidenceKind
    name: str
    content_type: str
    object_key: str
    sha256: str
    size_bytes: int
    retention_class: EvidenceRetentionClass
    retain_until: datetime | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ProjectStateRevision:
    id: uuid.UUID
    project_id: uuid.UUID
    version: int
    parent_revision_id: uuid.UUID | None
    schema_version: str
    state: dict[str, object]
    state_sha256: str
    idempotency_key: str
    request_fingerprint: str
    source_provider: str
    source_kind: str
    source_event_id: str | None
    source_uri: str | None
    source_occurred_at: datetime | None
    observed_at: datetime
    assertion_status: ProjectStateAssertionStatus
    confidence: Decimal
    confidence_explanation: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ProjectProjectionCheckpoint:
    project_id: uuid.UUID
    source_revision_id: uuid.UUID
    source_version: int
    rebuilt_at: datetime


@dataclass(frozen=True, slots=True)
class ProjectWorkItem:
    id: uuid.UUID
    project_id: uuid.UUID
    stable_id: str
    kind: ProjectWorkItemKind
    title: str
    status: str
    parent_stable_id: str | None
    source_revision_id: uuid.UUID
    source_provider: str
    source_kind: str
    source_external_id: str | None
    source_uri: str | None
    source_occurred_at: datetime | None
    source_observed_at: datetime
    assertion_status: ProjectStateAssertionStatus
    confidence: Decimal
    confidence_explanation: str


@dataclass(frozen=True, slots=True)
class ProjectProviderAlias:
    id: uuid.UUID
    project_id: uuid.UUID
    canonical_id: str
    provider: str
    account: str
    external_kind: str
    external_id: str
    uri: str | None
    source_revision_id: uuid.UUID


@dataclass(frozen=True, slots=True)
class ProjectGraphNode:
    id: uuid.UUID
    project_id: uuid.UUID
    stable_id: str
    graph_kind: ProjectGraphKind
    entity_kind: str
    title: str
    status: str
    source_revision_id: uuid.UUID
    source_provider: str
    source_kind: str
    source_external_id: str | None
    source_uri: str | None
    source_occurred_at: datetime | None
    source_observed_at: datetime
    assertion_status: ProjectStateAssertionStatus
    confidence: Decimal
    confidence_explanation: str


@dataclass(frozen=True, slots=True)
class ProjectGraphEdge:
    id: uuid.UUID
    project_id: uuid.UUID
    stable_id: str
    graph_kind: ProjectGraphKind
    from_stable_id: str
    to_stable_id: str
    relationship: str
    source_revision_id: uuid.UUID
    source_provider: str
    source_kind: str
    source_external_id: str | None
    source_uri: str | None
    source_occurred_at: datetime | None
    source_observed_at: datetime
    assertion_status: ProjectStateAssertionStatus
    confidence: Decimal
    confidence_explanation: str


@dataclass(frozen=True, slots=True)
class ProjectValidationResult:
    id: uuid.UUID
    project_id: uuid.UUID
    stable_id: str
    title: str
    status: str
    evidence_ids: tuple[str, ...]
    acceptance_criterion_ids: tuple[str, ...]
    stale_at: datetime | None
    superseded_by: str | None
    affected_capability_ids: tuple[str, ...]
    source_revision_id: uuid.UUID
    source_provider: str
    source_kind: str
    source_external_id: str | None
    source_uri: str | None
    source_occurred_at: datetime | None
    source_observed_at: datetime
    assertion_status: ProjectStateAssertionStatus
    confidence: Decimal
    confidence_explanation: str


@dataclass(frozen=True, slots=True)
class ProjectRisk:
    id: uuid.UUID
    project_id: uuid.UUID
    stable_id: str
    title: str
    status: str
    owner_id: str
    likelihood: Decimal
    impact: Decimal
    mitigation: str
    trigger: str
    review_at: datetime | None
    affected_capability_ids: tuple[str, ...]
    affected_dependency_ids: tuple[str, ...]
    source_revision_id: uuid.UUID
    source_provider: str
    source_kind: str
    source_external_id: str | None
    source_uri: str | None
    source_occurred_at: datetime | None
    source_observed_at: datetime
    assertion_status: ProjectStateAssertionStatus
    confidence: Decimal
    confidence_explanation: str


@dataclass(frozen=True, slots=True)
class ProjectTechnicalDebt:
    id: uuid.UUID
    project_id: uuid.UUID
    stable_id: str
    title: str
    status: str
    owner_id: str
    principal: Decimal
    interest: Decimal
    impact: str
    retirement_criteria: str
    affected_capability_ids: tuple[str, ...]
    affected_dependency_ids: tuple[str, ...]
    source_revision_id: uuid.UUID
    source_provider: str
    source_kind: str
    source_external_id: str | None
    source_uri: str | None
    source_occurred_at: datetime | None
    source_observed_at: datetime
    assertion_status: ProjectStateAssertionStatus
    confidence: Decimal
    confidence_explanation: str


@dataclass(frozen=True, slots=True)
class ProjectIntelligenceProjection:
    checkpoint: ProjectProjectionCheckpoint
    work_items: tuple[ProjectWorkItem, ...]
    aliases: tuple[ProjectProviderAlias, ...]
    graph_nodes: tuple[ProjectGraphNode, ...]
    graph_edges: tuple[ProjectGraphEdge, ...]
    validation_results: tuple[ProjectValidationResult, ...] = ()
    risks: tuple[ProjectRisk, ...] = ()
    technical_debt: tuple[ProjectTechnicalDebt, ...] = ()


@dataclass(frozen=True, slots=True)
class WorkflowStepDefinition:
    key: str
    name: str


@dataclass(frozen=True, slots=True)
class WorkflowStepDetail:
    step: WorkflowStep
    attempts: tuple[WorkflowStepAttempt, ...]


@dataclass(frozen=True, slots=True)
class WorkflowRunDetail:
    run: WorkflowRun
    steps: tuple[WorkflowStepDetail, ...]


@dataclass(frozen=True, slots=True)
class OutboxMessage:
    id: uuid.UUID
    occurred_at: datetime
    topic: str
    aggregate_id: str
    payload: dict[str, object]
    actor_type: str = "service"
    actor_id: str = "genesis-control-plane"
