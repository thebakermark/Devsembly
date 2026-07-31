from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from devsembly.domain import (
    Budget,
    CostEvaluation,
    Decision,
    Evidence,
    Initiative,
    Organization,
    OutboxMessage,
    Project,
    ProjectStateRevision,
    WorkflowRun,
    WorkflowStep,
    WorkflowStepAttempt,
)


class OrganizationRepository(Protocol):
    async def add(self, organization: Organization) -> Organization: ...

    async def get(self, organization_id: uuid.UUID) -> Organization | None: ...

    async def list(self) -> Sequence[Organization]: ...

    async def update(
        self, organization_id: uuid.UUID, expected_version: int, name: str
    ) -> Organization | None: ...


class InitiativeRepository(Protocol):
    async def add(self, initiative: Initiative) -> Initiative: ...

    async def get(
        self, organization_id: uuid.UUID, initiative_id: uuid.UUID
    ) -> Initiative | None: ...

    async def list(self, organization_id: uuid.UUID) -> Sequence[Initiative]: ...

    async def update(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        expected_version: int,
        *,
        name: str,
        objective: str,
        status: str,
    ) -> Initiative | None: ...


class ProjectRepository(Protocol):
    async def add(self, project: Project) -> Project: ...

    async def get(self, initiative_id: uuid.UUID, project_id: uuid.UUID) -> Project | None: ...

    async def list(self, initiative_id: uuid.UUID) -> Sequence[Project]: ...

    async def update(
        self,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
        expected_version: int,
        *,
        name: str,
        repository: str | None,
        status: str,
    ) -> Project | None: ...


class ProjectStateRevisionRepository(Protocol):
    async def add(self, revision: ProjectStateRevision) -> ProjectStateRevision: ...

    async def latest(self, project_id: uuid.UUID) -> ProjectStateRevision | None: ...

    async def get_version(
        self, project_id: uuid.UUID, version: int
    ) -> ProjectStateRevision | None: ...

    async def get_by_idempotency_key(
        self, project_id: uuid.UUID, idempotency_key: str
    ) -> ProjectStateRevision | None: ...

    async def list(self, project_id: uuid.UUID) -> Sequence[ProjectStateRevision]: ...


class BudgetRepository(Protocol):
    async def add(self, budget: Budget) -> Budget: ...

    async def get(self, project_id: uuid.UUID, budget_id: uuid.UUID) -> Budget | None: ...

    async def list(self, project_id: uuid.UUID) -> Sequence[Budget]: ...

    async def update(
        self,
        project_id: uuid.UUID,
        budget_id: uuid.UUID,
        expected_version: int,
        *,
        monthly_limit: Decimal,
        currency: str,
        enforcement_mode: str,
    ) -> Budget | None: ...


class CostEvaluationRepository(Protocol):
    async def add(self, evaluation: CostEvaluation) -> CostEvaluation: ...

    async def get(
        self, project_id: uuid.UUID, evaluation_id: uuid.UUID
    ) -> CostEvaluation | None: ...

    async def get_by_idempotency_key(
        self, project_id: uuid.UUID, idempotency_key: str
    ) -> CostEvaluation | None: ...

    async def list(self, project_id: uuid.UUID) -> Sequence[CostEvaluation]: ...


class DecisionRepository(Protocol):
    async def add(self, decision: Decision) -> Decision: ...

    async def get(self, project_id: uuid.UUID, decision_id: uuid.UUID) -> Decision | None: ...

    async def list(self, project_id: uuid.UUID) -> Sequence[Decision]: ...

    async def resolve(
        self,
        project_id: uuid.UUID,
        decision_id: uuid.UUID,
        expected_version: int,
        *,
        status: str,
        decided_by: str,
        decision_note: str,
        outcome: str,
        authorization_budget_version: int | None,
        authorization_monthly_limit: Decimal | None,
        decided_at: datetime,
    ) -> Decision | None: ...


class WorkflowRunRepository(Protocol):
    async def add(self, workflow_run: WorkflowRun) -> WorkflowRun: ...

    async def get(
        self, project_id: uuid.UUID, workflow_run_id: uuid.UUID
    ) -> WorkflowRun | None: ...

    async def get_by_idempotency_key(
        self, project_id: uuid.UUID, idempotency_key: str
    ) -> WorkflowRun | None: ...

    async def list(self, project_id: uuid.UUID) -> Sequence[WorkflowRun]: ...

    async def update_status(
        self,
        project_id: uuid.UUID,
        workflow_run_id: uuid.UUID,
        expected_version: int,
        *,
        status: str,
        temporal_workflow_id: str | None,
        cancellation_requested_at: datetime | None,
        started_at: datetime | None,
        completed_at: datetime | None,
    ) -> WorkflowRun | None: ...


class WorkflowStepRepository(Protocol):
    async def add(self, step: WorkflowStep) -> WorkflowStep: ...

    async def get(
        self, workflow_run_id: uuid.UUID, workflow_step_id: uuid.UUID
    ) -> WorkflowStep | None: ...

    async def list(self, workflow_run_id: uuid.UUID) -> Sequence[WorkflowStep]: ...

    async def update_status(
        self,
        workflow_run_id: uuid.UUID,
        workflow_step_id: uuid.UUID,
        expected_version: int,
        *,
        status: str,
    ) -> WorkflowStep | None: ...


class WorkflowStepAttemptRepository(Protocol):
    async def add(self, attempt: WorkflowStepAttempt) -> WorkflowStepAttempt: ...

    async def list(self, workflow_step_id: uuid.UUID) -> Sequence[WorkflowStepAttempt]: ...


class OutboxRepository(Protocol):
    async def add(self, message: OutboxMessage) -> OutboxMessage: ...


class EvidenceRepository(Protocol):
    async def add(self, evidence: Evidence) -> Evidence: ...
    async def get(self, project_id: uuid.UUID, evidence_id: uuid.UUID) -> Evidence | None: ...
    async def list(self, project_id: uuid.UUID) -> Sequence[Evidence]: ...
