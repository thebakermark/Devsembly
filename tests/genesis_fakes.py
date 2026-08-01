from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime
from decimal import Decimal
from types import TracebackType
from typing import Self

from devsembly.domain import (
    Budget,
    ContextPackage,
    CostEvaluation,
    Decision,
    Evidence,
    Initiative,
    Organization,
    OutboxMessage,
    Project,
    ProjectIntelligenceProjection,
    ProjectMemory,
    ProjectStateRevision,
    WorkflowRun,
    WorkflowStep,
    WorkflowStepAttempt,
)
from devsembly.errors import DuplicateResourceError, InvalidTransitionError, StaleVersionError


@dataclass
class MemoryStore:
    organizations: dict[uuid.UUID, Organization] = field(default_factory=dict)
    initiatives: dict[uuid.UUID, Initiative] = field(default_factory=dict)
    projects: dict[uuid.UUID, Project] = field(default_factory=dict)
    project_state_revisions: dict[uuid.UUID, ProjectStateRevision] = field(default_factory=dict)
    project_intelligence_projections: dict[uuid.UUID, ProjectIntelligenceProjection] = field(
        default_factory=dict
    )
    project_memories: dict[uuid.UUID, ProjectMemory] = field(default_factory=dict)
    context_packages: dict[uuid.UUID, ContextPackage] = field(default_factory=dict)
    budgets: dict[uuid.UUID, Budget] = field(default_factory=dict)
    cost_evaluations: dict[uuid.UUID, CostEvaluation] = field(default_factory=dict)
    decisions: dict[uuid.UUID, Decision] = field(default_factory=dict)
    workflow_runs: dict[uuid.UUID, WorkflowRun] = field(default_factory=dict)
    workflow_steps: dict[uuid.UUID, WorkflowStep] = field(default_factory=dict)
    workflow_step_attempts: dict[uuid.UUID, WorkflowStepAttempt] = field(default_factory=dict)
    evidence: dict[uuid.UUID, Evidence] = field(default_factory=dict)
    outbox: list[OutboxMessage] = field(default_factory=list)
    audit_events: list[dict[str, object]] = field(default_factory=list)
    commits: int = 0
    rollbacks: int = 0


class MemoryOrganizationRepository:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    async def add(self, organization: Organization) -> Organization:
        self.store.organizations[organization.id] = organization
        return organization

    async def get(self, organization_id: uuid.UUID) -> Organization | None:
        return self.store.organizations.get(organization_id)

    async def list(self) -> list[Organization]:
        return list(self.store.organizations.values())

    async def update(
        self, organization_id: uuid.UUID, expected_version: int, name: str
    ) -> Organization | None:
        current = await self.get(organization_id)
        if current is None:
            return None
        if current.version != expected_version:
            raise StaleVersionError("organization", expected_version)
        updated = replace(current, name=name, version=current.version + 1)
        self.store.organizations[organization_id] = updated
        return updated


class MemoryInitiativeRepository:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    async def add(self, initiative: Initiative) -> Initiative:
        self.store.initiatives[initiative.id] = initiative
        return initiative

    async def get(self, organization_id: uuid.UUID, initiative_id: uuid.UUID) -> Initiative | None:
        initiative = self.store.initiatives.get(initiative_id)
        if initiative is None or initiative.organization_id != organization_id:
            return None
        return initiative

    async def list(self, organization_id: uuid.UUID) -> list[Initiative]:
        return [
            initiative
            for initiative in self.store.initiatives.values()
            if initiative.organization_id == organization_id
        ]

    async def update(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        expected_version: int,
        *,
        name: str,
        objective: str,
        status: str,
    ) -> Initiative | None:
        current = await self.get(organization_id, initiative_id)
        if current is None:
            return None
        if current.version != expected_version:
            raise StaleVersionError("initiative", expected_version)
        updated = replace(
            current,
            name=name,
            objective=objective,
            status=type(current.status)(status),
            version=current.version + 1,
        )
        self.store.initiatives[initiative_id] = updated
        return updated


class MemoryProjectRepository:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    async def add(self, project: Project) -> Project:
        self.store.projects[project.id] = project
        return project

    async def get(self, initiative_id: uuid.UUID, project_id: uuid.UUID) -> Project | None:
        project = self.store.projects.get(project_id)
        if project is None or project.initiative_id != initiative_id:
            return None
        return project

    async def list(self, initiative_id: uuid.UUID) -> list[Project]:
        return [
            project
            for project in self.store.projects.values()
            if project.initiative_id == initiative_id
        ]

    async def update(
        self,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
        expected_version: int,
        *,
        name: str,
        repository: str | None,
        status: str,
    ) -> Project | None:
        current = await self.get(initiative_id, project_id)
        if current is None:
            return None
        if current.version != expected_version:
            raise StaleVersionError("project", expected_version)
        updated = replace(
            current,
            name=name,
            repository=repository,
            status=type(current.status)(status),
            version=current.version + 1,
        )
        self.store.projects[project_id] = updated
        return updated


class MemoryProjectStateRevisionRepository:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    async def add(self, revision: ProjectStateRevision) -> ProjectStateRevision:
        if any(
            item.project_id == revision.project_id
            and (
                item.version == revision.version or item.idempotency_key == revision.idempotency_key
            )
            for item in self.store.project_state_revisions.values()
        ):
            raise DuplicateResourceError("project state revision")
        self.store.project_state_revisions[revision.id] = revision
        return revision

    async def latest(self, project_id: uuid.UUID) -> ProjectStateRevision | None:
        matches = [
            item
            for item in self.store.project_state_revisions.values()
            if item.project_id == project_id
        ]
        return None if not matches else max(matches, key=lambda item: item.version)

    async def get_version(self, project_id: uuid.UUID, version: int) -> ProjectStateRevision | None:
        return next(
            (
                item
                for item in self.store.project_state_revisions.values()
                if item.project_id == project_id and item.version == version
            ),
            None,
        )

    async def get_by_idempotency_key(
        self, project_id: uuid.UUID, idempotency_key: str
    ) -> ProjectStateRevision | None:
        return next(
            (
                item
                for item in self.store.project_state_revisions.values()
                if item.project_id == project_id and item.idempotency_key == idempotency_key
            ),
            None,
        )

    async def list(self, project_id: uuid.UUID) -> list[ProjectStateRevision]:
        return sorted(
            (
                item
                for item in self.store.project_state_revisions.values()
                if item.project_id == project_id
            ),
            key=lambda item: item.version,
        )


class MemoryProjectIntelligenceProjectionRepository:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    async def replace(self, projection: ProjectIntelligenceProjection) -> None:
        self.store.project_intelligence_projections[projection.checkpoint.project_id] = projection

    async def get(self, project_id: uuid.UUID) -> ProjectIntelligenceProjection | None:
        return self.store.project_intelligence_projections.get(project_id)


class MemoryProjectMemoryRepository:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    async def add(self, memory: ProjectMemory) -> ProjectMemory:
        if any(
            item.project_id == memory.project_id and item.content_sha256 == memory.content_sha256
            for item in self.store.project_memories.values()
        ):
            raise DuplicateResourceError("project memory")
        self.store.project_memories[memory.id] = memory
        return memory

    async def get(self, project_id: uuid.UUID, memory_id: uuid.UUID) -> ProjectMemory | None:
        memory = self.store.project_memories.get(memory_id)
        return memory if memory is not None and memory.project_id == project_id else None

    async def list(self, project_id: uuid.UUID) -> list[ProjectMemory]:
        return sorted(
            (
                item
                for item in self.store.project_memories.values()
                if item.project_id == project_id
            ),
            key=lambda item: (item.created_at, item.id),
        )

    async def resolve(
        self,
        project_id: uuid.UUID,
        memory_id: uuid.UUID,
        expected_version: int,
        *,
        status: str,
        decided_by: str,
        decision_reason: str,
        decided_at: datetime,
    ) -> ProjectMemory | None:
        current = await self.get(project_id, memory_id)
        if current is None:
            return None
        if current.version != expected_version:
            raise StaleVersionError("project memory", expected_version)
        if current.status.value != "proposed":
            raise InvalidTransitionError("project memory", current.status.value, status)
        from devsembly.domain import MemoryStatus

        resolved = replace(
            current,
            status=MemoryStatus(status),
            decided_by=decided_by,
            decision_reason=decision_reason,
            version=current.version + 1,
            updated_at=decided_at,
        )
        self.store.project_memories[memory_id] = resolved
        return resolved


class MemoryContextPackageRepository:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    async def add(self, package: ContextPackage) -> ContextPackage:
        self.store.context_packages[package.id] = package
        return package

    async def get(self, project_id: uuid.UUID, package_id: uuid.UUID) -> ContextPackage | None:
        package = self.store.context_packages.get(package_id)
        return package if package is not None and package.project_id == project_id else None

    async def invalidate_for_source_change(
        self, project_id: uuid.UUID, source_revision_id: uuid.UUID, invalidated_at: datetime
    ) -> int:
        count = 0
        for package_id, package in list(self.store.context_packages.items()):
            if (
                package.project_id == project_id
                and package.source_revision_id != source_revision_id
                and package.invalidated_at is None
            ):
                self.store.context_packages[package_id] = replace(
                    package, invalidated_at=invalidated_at
                )
                count += 1
        return count


class MemoryBudgetRepository:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    async def add(self, budget: Budget) -> Budget:
        if any(item.project_id == budget.project_id for item in self.store.budgets.values()):
            raise DuplicateResourceError("project budget")
        self.store.budgets[budget.id] = budget
        return budget

    async def get(self, project_id: uuid.UUID, budget_id: uuid.UUID) -> Budget | None:
        budget = self.store.budgets.get(budget_id)
        if budget is None or budget.project_id != project_id:
            return None
        return budget

    async def list(self, project_id: uuid.UUID) -> list[Budget]:
        return [budget for budget in self.store.budgets.values() if budget.project_id == project_id]

    async def update(
        self,
        project_id: uuid.UUID,
        budget_id: uuid.UUID,
        expected_version: int,
        *,
        monthly_limit: Decimal,
        currency: str,
        enforcement_mode: str,
    ) -> Budget | None:
        current = await self.get(project_id, budget_id)
        if current is None:
            return None
        if current.version != expected_version:
            raise StaleVersionError("budget", expected_version)
        updated = replace(
            current,
            monthly_limit=monthly_limit,
            currency=currency,
            enforcement_mode=type(current.enforcement_mode)(enforcement_mode),
            version=current.version + 1,
        )
        self.store.budgets[budget_id] = updated
        return updated


class MemoryCostEvaluationRepository:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    async def add(self, evaluation: CostEvaluation) -> CostEvaluation:
        if any(
            item.project_id == evaluation.project_id
            and item.idempotency_key == evaluation.idempotency_key
            for item in self.store.cost_evaluations.values()
        ):
            raise DuplicateResourceError("cost evaluation")
        self.store.cost_evaluations[evaluation.id] = evaluation
        return evaluation

    async def get(self, project_id: uuid.UUID, evaluation_id: uuid.UUID) -> CostEvaluation | None:
        evaluation = self.store.cost_evaluations.get(evaluation_id)
        if evaluation is None or evaluation.project_id != project_id:
            return None
        return evaluation

    async def get_by_idempotency_key(
        self, project_id: uuid.UUID, idempotency_key: str
    ) -> CostEvaluation | None:
        return next(
            (
                item
                for item in self.store.cost_evaluations.values()
                if item.project_id == project_id and item.idempotency_key == idempotency_key
            ),
            None,
        )

    async def list(self, project_id: uuid.UUID) -> list[CostEvaluation]:
        return [
            item for item in self.store.cost_evaluations.values() if item.project_id == project_id
        ]


class MemoryDecisionRepository:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    async def add(self, decision: Decision) -> Decision:
        self.store.decisions[decision.id] = decision
        return decision

    async def get(self, project_id: uuid.UUID, decision_id: uuid.UUID) -> Decision | None:
        decision = self.store.decisions.get(decision_id)
        if decision is None or decision.project_id != project_id:
            return None
        return decision

    async def list(self, project_id: uuid.UUID) -> list[Decision]:
        return [item for item in self.store.decisions.values() if item.project_id == project_id]

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
    ) -> Decision | None:
        current = await self.get(project_id, decision_id)
        if current is None:
            return None
        if current.version != expected_version:
            raise StaleVersionError("decision", expected_version)
        if current.status.value != "proposed":
            raise InvalidTransitionError("decision", current.status.value, status)
        updated = replace(
            current,
            status=type(current.status)(status),
            decided_by=decided_by,
            decision_note=decision_note,
            outcome=outcome,
            authorization_budget_version=authorization_budget_version,
            authorization_monthly_limit=authorization_monthly_limit,
            version=expected_version + 1,
            decided_at=decided_at,
            updated_at=decided_at,
        )
        self.store.decisions[decision_id] = updated
        return updated


class MemoryWorkflowRunRepository:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    async def add(self, workflow_run: WorkflowRun) -> WorkflowRun:
        if any(
            item.project_id == workflow_run.project_id
            and item.idempotency_key == workflow_run.idempotency_key
            for item in self.store.workflow_runs.values()
        ):
            raise DuplicateResourceError("workflow run")
        self.store.workflow_runs[workflow_run.id] = workflow_run
        return workflow_run

    async def get(self, project_id: uuid.UUID, workflow_run_id: uuid.UUID) -> WorkflowRun | None:
        workflow_run = self.store.workflow_runs.get(workflow_run_id)
        if workflow_run is None or workflow_run.project_id != project_id:
            return None
        return workflow_run

    async def get_by_idempotency_key(
        self, project_id: uuid.UUID, idempotency_key: str
    ) -> WorkflowRun | None:
        return next(
            (
                item
                for item in self.store.workflow_runs.values()
                if item.project_id == project_id and item.idempotency_key == idempotency_key
            ),
            None,
        )

    async def list(self, project_id: uuid.UUID) -> list[WorkflowRun]:
        return [item for item in self.store.workflow_runs.values() if item.project_id == project_id]

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
    ) -> WorkflowRun | None:
        current = await self.get(project_id, workflow_run_id)
        if current is None:
            return None
        if current.version != expected_version:
            raise StaleVersionError("workflow run", expected_version)
        if temporal_workflow_id is not None and any(
            item.id != workflow_run_id and item.temporal_workflow_id == temporal_workflow_id
            for item in self.store.workflow_runs.values()
        ):
            raise DuplicateResourceError("Temporal workflow correlation")
        updated = replace(
            current,
            status=type(current.status)(status),
            temporal_workflow_id=temporal_workflow_id,
            cancellation_requested_at=cancellation_requested_at,
            started_at=started_at,
            completed_at=completed_at,
            version=current.version + 1,
        )
        self.store.workflow_runs[workflow_run_id] = updated
        return updated


class MemoryWorkflowStepRepository:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    async def add(self, step: WorkflowStep) -> WorkflowStep:
        if any(
            item.workflow_run_id == step.workflow_run_id
            and (item.key == step.key or item.position == step.position)
            for item in self.store.workflow_steps.values()
        ):
            raise DuplicateResourceError("workflow step")
        self.store.workflow_steps[step.id] = step
        return step

    async def get(
        self, workflow_run_id: uuid.UUID, workflow_step_id: uuid.UUID
    ) -> WorkflowStep | None:
        step = self.store.workflow_steps.get(workflow_step_id)
        if step is None or step.workflow_run_id != workflow_run_id:
            return None
        return step

    async def list(self, workflow_run_id: uuid.UUID) -> list[WorkflowStep]:
        return sorted(
            (
                item
                for item in self.store.workflow_steps.values()
                if item.workflow_run_id == workflow_run_id
            ),
            key=lambda item: (item.position, item.id),
        )

    async def update_status(
        self,
        workflow_run_id: uuid.UUID,
        workflow_step_id: uuid.UUID,
        expected_version: int,
        *,
        status: str,
    ) -> WorkflowStep | None:
        current = await self.get(workflow_run_id, workflow_step_id)
        if current is None:
            return None
        if current.version != expected_version:
            raise StaleVersionError("workflow step", expected_version)
        updated = replace(
            current,
            status=type(current.status)(status),
            version=current.version + 1,
        )
        self.store.workflow_steps[workflow_step_id] = updated
        return updated


class MemoryWorkflowStepAttemptRepository:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    async def add(self, attempt: WorkflowStepAttempt) -> WorkflowStepAttempt:
        if any(
            item.workflow_step_id == attempt.workflow_step_id
            and item.attempt_number == attempt.attempt_number
            for item in self.store.workflow_step_attempts.values()
        ):
            raise DuplicateResourceError("workflow step attempt")
        self.store.workflow_step_attempts[attempt.id] = attempt
        return attempt

    async def list(self, workflow_step_id: uuid.UUID) -> list[WorkflowStepAttempt]:
        return sorted(
            (
                item
                for item in self.store.workflow_step_attempts.values()
                if item.workflow_step_id == workflow_step_id
            ),
            key=lambda item: (item.attempt_number, item.id),
        )


class MemoryOutboxRepository:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    async def add(self, message: OutboxMessage) -> OutboxMessage:
        self.store.outbox.append(message)
        self.store.audit_events.append(
            {
                "actor_type": message.actor_type,
                "actor_id": message.actor_id,
                "action": message.topic,
                "object_id": message.aggregate_id,
                "correlation_id": str(message.id),
                "payload": {"event_id": str(message.id), **message.payload},
            }
        )
        return message


class MemoryEvidenceRepository:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    async def add(self, evidence: Evidence) -> Evidence:
        if any(
            item.project_id == evidence.project_id and item.object_key == evidence.object_key
            for item in self.store.evidence.values()
        ):
            raise DuplicateResourceError("evidence")
        self.store.evidence[evidence.id] = evidence
        return evidence

    async def get(self, project_id: uuid.UUID, evidence_id: uuid.UUID) -> Evidence | None:
        evidence = self.store.evidence.get(evidence_id)
        if evidence is None or evidence.project_id != project_id:
            return None
        return evidence

    async def list(self, project_id: uuid.UUID) -> list[Evidence]:
        return sorted(
            (item for item in self.store.evidence.values() if item.project_id == project_id),
            key=lambda item: (item.created_at, item.id),
        )


class MemoryUnitOfWork:
    def __init__(self, store: MemoryStore) -> None:
        self.store = store
        self.organizations = MemoryOrganizationRepository(store)
        self.initiatives = MemoryInitiativeRepository(store)
        self.projects = MemoryProjectRepository(store)
        self.project_state_revisions = MemoryProjectStateRevisionRepository(store)
        self.project_intelligence_projection = MemoryProjectIntelligenceProjectionRepository(store)
        self.project_memories = MemoryProjectMemoryRepository(store)
        self.context_packages = MemoryContextPackageRepository(store)
        self.budgets = MemoryBudgetRepository(store)
        self.cost_evaluations = MemoryCostEvaluationRepository(store)
        self.decisions = MemoryDecisionRepository(store)
        self.workflow_runs = MemoryWorkflowRunRepository(store)
        self.workflow_steps = MemoryWorkflowStepRepository(store)
        self.workflow_step_attempts = MemoryWorkflowStepAttemptRepository(store)
        self.evidence = MemoryEvidenceRepository(store)
        self.outbox = MemoryOutboxRepository(store)
        self.committed = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None or not self.committed:
            await self.rollback()

    async def commit(self) -> None:
        self.committed = True
        self.store.commits += 1

    async def rollback(self) -> None:
        self.store.rollbacks += 1


class MemoryUnitOfWorkFactory:
    def __init__(self) -> None:
        self.store = MemoryStore()

    def __call__(self) -> MemoryUnitOfWork:
        return MemoryUnitOfWork(self.store)
