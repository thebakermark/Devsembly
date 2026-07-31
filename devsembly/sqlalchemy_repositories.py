from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import cast

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from devsembly import models
from devsembly.domain import (
    Budget,
    BudgetEnforcementMode,
    CostCadence,
    CostEvaluation,
    CostEvaluationOutcome,
    CostLineItem,
    CostOption,
    CostRecommendation,
    Decision,
    DecisionRisk,
    DecisionStatus,
    Evidence,
    EvidenceKind,
    EvidenceRetentionClass,
    Initiative,
    InitiativeStatus,
    Organization,
    OutboxMessage,
    Project,
    ProjectGraphEdge,
    ProjectGraphKind,
    ProjectGraphNode,
    ProjectIntelligenceProjection,
    ProjectProjectionCheckpoint,
    ProjectProviderAlias,
    ProjectStateAssertionStatus,
    ProjectStateRevision,
    ProjectStatus,
    ProjectWorkItem,
    ProjectWorkItemKind,
    WorkflowAttemptStatus,
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowStep,
    WorkflowStepAttempt,
    WorkflowStepStatus,
)
from devsembly.errors import DuplicateResourceError, InvalidTransitionError, StaleVersionError
from devsembly.pie_projection import build_projection


def _organization(model: models.Organization) -> Organization:
    return Organization(
        id=model.id,
        name=model.name,
        version=model.version,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _initiative(model: models.Initiative) -> Initiative:
    return Initiative(
        id=model.id,
        organization_id=model.organization_id,
        name=model.name,
        objective=model.objective,
        status=InitiativeStatus(model.status),
        version=model.version,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _project(model: models.Project) -> Project:
    return Project(
        id=model.id,
        initiative_id=model.initiative_id,
        name=model.name,
        repository=model.repository,
        status=ProjectStatus(model.status),
        version=model.version,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _project_state_revision(model: models.ProjectStateRevision) -> ProjectStateRevision:
    return ProjectStateRevision(
        id=model.id,
        project_id=model.project_id,
        version=model.version,
        parent_revision_id=model.parent_revision_id,
        schema_version=model.schema_version,
        state=model.state,
        state_sha256=model.state_sha256,
        idempotency_key=model.idempotency_key,
        request_fingerprint=model.request_fingerprint,
        source_provider=model.source_provider,
        source_kind=model.source_kind,
        source_event_id=model.source_event_id,
        source_uri=model.source_uri,
        source_occurred_at=model.source_occurred_at,
        observed_at=model.observed_at,
        assertion_status=ProjectStateAssertionStatus(model.assertion_status),
        confidence=model.confidence,
        confidence_explanation=model.confidence_explanation,
        created_at=model.created_at,
    )


def _project_work_item(model: models.ProjectIntelligenceWorkItem) -> ProjectWorkItem:
    return ProjectWorkItem(
        id=model.id,
        project_id=model.project_id,
        stable_id=model.stable_id,
        kind=ProjectWorkItemKind(model.kind),
        title=model.title,
        status=model.status,
        parent_stable_id=model.parent_stable_id,
        source_revision_id=model.source_revision_id,
        source_provider=model.source_provider,
        source_kind=model.source_kind,
        source_external_id=model.source_external_id,
        source_uri=model.source_uri,
        source_occurred_at=model.source_occurred_at,
        source_observed_at=model.source_observed_at,
        assertion_status=ProjectStateAssertionStatus(model.assertion_status),
        confidence=model.confidence,
        confidence_explanation=model.confidence_explanation,
    )


def _project_graph_node(model: models.ProjectIntelligenceGraphNode) -> ProjectGraphNode:
    return ProjectGraphNode(
        id=model.id,
        project_id=model.project_id,
        stable_id=model.stable_id,
        graph_kind=ProjectGraphKind(model.graph_kind),
        entity_kind=model.entity_kind,
        title=model.title,
        status=model.status,
        source_revision_id=model.source_revision_id,
        source_provider=model.source_provider,
        source_kind=model.source_kind,
        source_external_id=model.source_external_id,
        source_uri=model.source_uri,
        source_occurred_at=model.source_occurred_at,
        source_observed_at=model.source_observed_at,
        assertion_status=ProjectStateAssertionStatus(model.assertion_status),
        confidence=model.confidence,
        confidence_explanation=model.confidence_explanation,
    )


def _project_graph_edge(model: models.ProjectIntelligenceGraphEdge) -> ProjectGraphEdge:
    return ProjectGraphEdge(
        id=model.id,
        project_id=model.project_id,
        stable_id=model.stable_id,
        graph_kind=ProjectGraphKind(model.graph_kind),
        from_stable_id=model.from_stable_id,
        to_stable_id=model.to_stable_id,
        relationship=model.relationship,
        source_revision_id=model.source_revision_id,
        source_provider=model.source_provider,
        source_kind=model.source_kind,
        source_external_id=model.source_external_id,
        source_uri=model.source_uri,
        source_occurred_at=model.source_occurred_at,
        source_observed_at=model.source_observed_at,
        assertion_status=ProjectStateAssertionStatus(model.assertion_status),
        confidence=model.confidence,
        confidence_explanation=model.confidence_explanation,
    )


def _budget(model: models.Budget) -> Budget:
    return Budget(
        id=model.id,
        project_id=model.project_id,
        monthly_limit=model.monthly_limit,
        currency=model.currency,
        enforcement_mode=BudgetEnforcementMode(model.enforcement_mode),
        version=model.version,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _line_item_payload(item: CostLineItem) -> dict[str, object]:
    return {
        "category": item.category,
        "description": item.description,
        "cadence": item.cadence.value,
        "quantity": str(item.quantity),
        "unit_cost": str(item.unit_cost),
    }


def _option_payload(option: CostOption) -> dict[str, object]:
    return {
        "key": option.key,
        "name": option.name,
        "satisfies_acceptance_criteria": option.satisfies_acceptance_criteria,
        "line_items": [_line_item_payload(item) for item in option.line_items],
        "one_time_cost": str(option.one_time_cost),
        "monthly_cost": str(option.monthly_cost),
    }


def _cost_option(payload: dict[str, object]) -> CostOption:
    items = cast(list[dict[str, object]], payload["line_items"])
    return CostOption(
        key=str(payload["key"]),
        name=str(payload["name"]),
        satisfies_acceptance_criteria=bool(payload["satisfies_acceptance_criteria"]),
        line_items=tuple(
            CostLineItem(
                category=str(item["category"]),
                description=str(item["description"]),
                cadence=CostCadence(str(item["cadence"])),
                quantity=Decimal(str(item["quantity"])),
                unit_cost=Decimal(str(item["unit_cost"])),
            )
            for item in items
        ),
        one_time_cost=Decimal(str(payload["one_time_cost"])),
        monthly_cost=Decimal(str(payload["monthly_cost"])),
    )


def _recommendation_payload(recommendation: CostRecommendation) -> dict[str, object]:
    return {
        "option_key": recommendation.option_key,
        "monthly_savings": str(recommendation.monthly_savings),
        "one_time_savings": str(recommendation.one_time_savings),
        "fits_monthly_budget": recommendation.fits_monthly_budget,
        "rationale": recommendation.rationale,
        "algorithm_version": recommendation.algorithm_version,
    }


def _cost_recommendation(payload: dict[str, object]) -> CostRecommendation:
    return CostRecommendation(
        option_key=str(payload["option_key"]),
        monthly_savings=Decimal(str(payload["monthly_savings"])),
        one_time_savings=Decimal(str(payload["one_time_savings"])),
        fits_monthly_budget=bool(payload["fits_monthly_budget"]),
        rationale=str(payload["rationale"]),
        algorithm_version=str(payload["algorithm_version"]),
    )


def _cost_evaluation(model: models.CostEvaluation) -> CostEvaluation:
    return CostEvaluation(
        id=model.id,
        project_id=model.project_id,
        budget_id=model.budget_id,
        workflow_run_id=model.workflow_run_id,
        idempotency_key=model.idempotency_key,
        request_fingerprint=model.request_fingerprint,
        currency=model.currency,
        budget_monthly_limit=model.budget_monthly_limit,
        budget_version=model.budget_version,
        enforcement_mode=BudgetEnforcementMode(model.enforcement_mode),
        selected_option=_cost_option(model.selected_option),
        alternatives=tuple(_cost_option(item) for item in model.alternatives),
        outcome=CostEvaluationOutcome(model.outcome),
        monthly_overage=model.monthly_overage,
        recommendation=(
            None if model.recommendation is None else _cost_recommendation(model.recommendation)
        ),
        algorithm_version=model.algorithm_version,
        created_at=model.created_at,
    )


def _decision(model: models.Decision) -> Decision:
    return Decision(
        id=model.id,
        project_id=model.project_id,
        cost_evaluation_id=model.cost_evaluation_id,
        title=model.title,
        context=model.context,
        selected_option=model.selected_option,
        alternatives=tuple(model.alternatives),
        currency=model.currency,
        estimated_one_time_cost=model.estimated_one_time_cost,
        estimated_monthly_cost=model.estimated_monthly_cost,
        risk=DecisionRisk(model.risk),
        confidence=model.confidence,
        rationale=model.rationale,
        status=DecisionStatus(model.status),
        decided_by=model.decided_by,
        decision_note=model.decision_note,
        outcome=model.outcome,
        authorization_budget_version=model.authorization_budget_version,
        authorization_monthly_limit=model.authorization_monthly_limit,
        version=model.version,
        decided_at=model.decided_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _workflow_run(model: models.WorkflowRun) -> WorkflowRun:
    return WorkflowRun(
        id=model.id,
        project_id=model.project_id,
        workflow_kind=model.workflow_kind,
        idempotency_key=model.idempotency_key,
        input_payload=model.input_payload,
        status=WorkflowRunStatus(model.status),
        temporal_workflow_id=model.temporal_workflow_id,
        retry_of_run_id=model.retry_of_run_id,
        cost_estimate=model.cost_estimate,
        version=model.version,
        cancellation_requested_at=model.cancellation_requested_at,
        started_at=model.started_at,
        completed_at=model.completed_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _workflow_step(model: models.WorkflowStep) -> WorkflowStep:
    return WorkflowStep(
        id=model.id,
        workflow_run_id=model.workflow_run_id,
        key=model.key,
        name=model.name,
        position=model.position,
        status=WorkflowStepStatus(model.status),
        version=model.version,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _workflow_step_attempt(model: models.WorkflowStepAttempt) -> WorkflowStepAttempt:
    return WorkflowStepAttempt(
        id=model.id,
        workflow_step_id=model.workflow_step_id,
        attempt_number=model.attempt_number,
        status=WorkflowAttemptStatus(model.status),
        result_payload=model.result_payload,
        error_payload=model.error_payload,
        started_at=model.started_at,
        completed_at=model.completed_at,
        created_at=model.created_at,
    )


def _evidence(model: models.Evidence) -> Evidence:
    return Evidence(
        id=model.id,
        project_id=model.project_id,
        workflow_run_id=model.workflow_run_id,
        workflow_step_attempt_id=model.workflow_step_attempt_id,
        kind=EvidenceKind(model.kind),
        name=model.name,
        content_type=model.content_type,
        object_key=model.object_key,
        sha256=model.sha256,
        size_bytes=model.size_bytes,
        retention_class=EvidenceRetentionClass(model.retention_class),
        retain_until=model.retain_until,
        created_at=model.created_at,
    )


class SqlAlchemyOrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, organization: Organization) -> Organization:
        self._session.add(
            models.Organization(
                id=organization.id,
                name=organization.name,
                version=organization.version,
                created_at=organization.created_at,
                updated_at=organization.updated_at,
            )
        )
        await self._session.flush()
        return organization

    async def get(self, organization_id: uuid.UUID) -> Organization | None:
        model = await self._session.get(models.Organization, organization_id)
        return None if model is None else _organization(model)

    async def list(self) -> Sequence[Organization]:
        result = await self._session.scalars(
            select(models.Organization).order_by(
                models.Organization.created_at, models.Organization.id
            )
        )
        return [_organization(model) for model in result]

    async def update(
        self, organization_id: uuid.UUID, expected_version: int, name: str
    ) -> Organization | None:
        now = datetime.now(UTC)
        result = await self._session.scalars(
            update(models.Organization)
            .where(
                models.Organization.id == organization_id,
                models.Organization.version == expected_version,
            )
            .values(name=name, version=expected_version + 1, updated_at=now)
            .returning(models.Organization)
        )
        model = result.one_or_none()
        if model is not None:
            return _organization(model)
        if await self.get(organization_id) is None:
            return None
        raise StaleVersionError("organization", expected_version)


class SqlAlchemyInitiativeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, initiative: Initiative) -> Initiative:
        self._session.add(
            models.Initiative(
                id=initiative.id,
                organization_id=initiative.organization_id,
                name=initiative.name,
                objective=initiative.objective,
                status=initiative.status.value,
                version=initiative.version,
                created_at=initiative.created_at,
                updated_at=initiative.updated_at,
            )
        )
        await self._session.flush()
        return initiative

    async def get(self, organization_id: uuid.UUID, initiative_id: uuid.UUID) -> Initiative | None:
        result = await self._session.scalars(
            select(models.Initiative).where(
                models.Initiative.id == initiative_id,
                models.Initiative.organization_id == organization_id,
            )
        )
        model = result.one_or_none()
        return None if model is None else _initiative(model)

    async def list(self, organization_id: uuid.UUID) -> Sequence[Initiative]:
        result = await self._session.scalars(
            select(models.Initiative)
            .where(models.Initiative.organization_id == organization_id)
            .order_by(models.Initiative.created_at, models.Initiative.id)
        )
        return [_initiative(model) for model in result]

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
        now = datetime.now(UTC)
        result = await self._session.scalars(
            update(models.Initiative)
            .where(
                models.Initiative.id == initiative_id,
                models.Initiative.organization_id == organization_id,
                models.Initiative.version == expected_version,
            )
            .values(
                name=name,
                objective=objective,
                status=status,
                version=expected_version + 1,
                updated_at=now,
            )
            .returning(models.Initiative)
        )
        model = result.one_or_none()
        if model is not None:
            return _initiative(model)
        if await self.get(organization_id, initiative_id) is None:
            return None
        raise StaleVersionError("initiative", expected_version)


class SqlAlchemyProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, project: Project) -> Project:
        self._session.add(
            models.Project(
                id=project.id,
                initiative_id=project.initiative_id,
                name=project.name,
                repository=project.repository,
                status=project.status.value,
                version=project.version,
                created_at=project.created_at,
                updated_at=project.updated_at,
            )
        )
        await self._session.flush()
        return project

    async def get(self, initiative_id: uuid.UUID, project_id: uuid.UUID) -> Project | None:
        result = await self._session.scalars(
            select(models.Project).where(
                models.Project.id == project_id,
                models.Project.initiative_id == initiative_id,
            )
        )
        model = result.one_or_none()
        return None if model is None else _project(model)

    async def list(self, initiative_id: uuid.UUID) -> Sequence[Project]:
        result = await self._session.scalars(
            select(models.Project)
            .where(models.Project.initiative_id == initiative_id)
            .order_by(models.Project.created_at, models.Project.id)
        )
        return [_project(model) for model in result]

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
        now = datetime.now(UTC)
        result = await self._session.scalars(
            update(models.Project)
            .where(
                models.Project.id == project_id,
                models.Project.initiative_id == initiative_id,
                models.Project.version == expected_version,
            )
            .values(
                name=name,
                repository=repository,
                status=status,
                version=expected_version + 1,
                updated_at=now,
            )
            .returning(models.Project)
        )
        model = result.one_or_none()
        if model is not None:
            return _project(model)
        if await self.get(initiative_id, project_id) is None:
            return None
        raise StaleVersionError("project", expected_version)


class SqlAlchemyProjectStateRevisionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, revision: ProjectStateRevision) -> ProjectStateRevision:
        self._session.add(
            models.ProjectStateRevision(
                id=revision.id,
                project_id=revision.project_id,
                version=revision.version,
                parent_revision_id=revision.parent_revision_id,
                schema_version=revision.schema_version,
                state=revision.state,
                state_sha256=revision.state_sha256,
                idempotency_key=revision.idempotency_key,
                request_fingerprint=revision.request_fingerprint,
                source_provider=revision.source_provider,
                source_kind=revision.source_kind,
                source_event_id=revision.source_event_id,
                source_uri=revision.source_uri,
                source_occurred_at=revision.source_occurred_at,
                observed_at=revision.observed_at,
                assertion_status=revision.assertion_status.value,
                confidence=revision.confidence,
                confidence_explanation=revision.confidence_explanation,
                created_at=revision.created_at,
            )
        )
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise DuplicateResourceError("project state revision") from exc
        return revision

    async def latest(self, project_id: uuid.UUID) -> ProjectStateRevision | None:
        model = await self._session.scalar(
            select(models.ProjectStateRevision)
            .where(models.ProjectStateRevision.project_id == project_id)
            .order_by(models.ProjectStateRevision.version.desc())
            .limit(1)
        )
        return None if model is None else _project_state_revision(model)

    async def get_version(self, project_id: uuid.UUID, version: int) -> ProjectStateRevision | None:
        model = await self._session.scalar(
            select(models.ProjectStateRevision).where(
                models.ProjectStateRevision.project_id == project_id,
                models.ProjectStateRevision.version == version,
            )
        )
        return None if model is None else _project_state_revision(model)

    async def get_by_idempotency_key(
        self, project_id: uuid.UUID, idempotency_key: str
    ) -> ProjectStateRevision | None:
        model = await self._session.scalar(
            select(models.ProjectStateRevision).where(
                models.ProjectStateRevision.project_id == project_id,
                models.ProjectStateRevision.idempotency_key == idempotency_key,
            )
        )
        return None if model is None else _project_state_revision(model)

    async def list(self, project_id: uuid.UUID) -> Sequence[ProjectStateRevision]:
        result = await self._session.scalars(
            select(models.ProjectStateRevision)
            .where(models.ProjectStateRevision.project_id == project_id)
            .order_by(models.ProjectStateRevision.version)
        )
        return [_project_state_revision(model) for model in result]


class SqlAlchemyProjectIntelligenceProjectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace(self, projection: ProjectIntelligenceProjection) -> None:
        project_id = projection.checkpoint.project_id
        for model in (
            models.ProjectIntelligenceProviderAlias,
            models.ProjectIntelligenceGraphEdge,
            models.ProjectIntelligenceGraphNode,
            models.ProjectIntelligenceWorkItem,
            models.ProjectIntelligenceProjection,
        ):
            await self._session.execute(delete(model).where(model.project_id == project_id))
        await self._session.flush()
        self._session.add(
            models.ProjectIntelligenceProjection(
                project_id=project_id,
                source_revision_id=projection.checkpoint.source_revision_id,
                source_version=projection.checkpoint.source_version,
                rebuilt_at=projection.checkpoint.rebuilt_at,
                validation_results=[
                    {
                        "id": item.stable_id,
                        "status": item.status,
                        "evidence_ids": list(item.evidence_ids),
                        "acceptance_criterion_ids": list(item.acceptance_criterion_ids),
                        "affected_capability_ids": list(item.affected_capability_ids),
                    }
                    for item in projection.validation_results
                ],
                risks=[
                    {
                        "id": item.stable_id,
                        "status": item.status,
                        "owner_id": item.owner_id,
                        "likelihood": str(item.likelihood),
                        "impact": str(item.impact),
                        "affected_capability_ids": list(item.affected_capability_ids),
                        "affected_dependency_ids": list(item.affected_dependency_ids),
                    }
                    for item in projection.risks
                ],
                technical_debt=[
                    {
                        "id": item.stable_id,
                        "status": item.status,
                        "owner_id": item.owner_id,
                        "principal": str(item.principal),
                        "interest": str(item.interest),
                        "affected_capability_ids": list(item.affected_capability_ids),
                        "affected_dependency_ids": list(item.affected_dependency_ids),
                    }
                    for item in projection.technical_debt
                ],
            )
        )
        self._session.add_all(
            [
                models.ProjectIntelligenceWorkItem(
                    id=item.id,
                    project_id=item.project_id,
                    stable_id=item.stable_id,
                    kind=item.kind.value,
                    title=item.title,
                    status=item.status,
                    parent_stable_id=item.parent_stable_id,
                    source_revision_id=item.source_revision_id,
                    source_provider=item.source_provider,
                    source_kind=item.source_kind,
                    source_external_id=item.source_external_id,
                    source_uri=item.source_uri,
                    source_occurred_at=item.source_occurred_at,
                    source_observed_at=item.source_observed_at,
                    assertion_status=item.assertion_status.value,
                    confidence=item.confidence,
                    confidence_explanation=item.confidence_explanation,
                )
                for item in projection.work_items
            ]
        )
        self._session.add_all(
            [
                models.ProjectIntelligenceProviderAlias(
                    id=item.id,
                    project_id=item.project_id,
                    canonical_id=item.canonical_id,
                    provider=item.provider,
                    account=item.account,
                    external_kind=item.external_kind,
                    external_id=item.external_id,
                    uri=item.uri,
                    source_revision_id=item.source_revision_id,
                )
                for item in projection.aliases
            ]
        )
        self._session.add_all(
            [
                models.ProjectIntelligenceGraphNode(
                    id=item.id,
                    project_id=item.project_id,
                    stable_id=item.stable_id,
                    graph_kind=item.graph_kind.value,
                    entity_kind=item.entity_kind,
                    title=item.title,
                    status=item.status,
                    source_revision_id=item.source_revision_id,
                    source_provider=item.source_provider,
                    source_kind=item.source_kind,
                    source_external_id=item.source_external_id,
                    source_uri=item.source_uri,
                    source_occurred_at=item.source_occurred_at,
                    source_observed_at=item.source_observed_at,
                    assertion_status=item.assertion_status.value,
                    confidence=item.confidence,
                    confidence_explanation=item.confidence_explanation,
                )
                for item in projection.graph_nodes
            ]
        )
        self._session.add_all(
            [
                models.ProjectIntelligenceGraphEdge(
                    id=item.id,
                    project_id=item.project_id,
                    stable_id=item.stable_id,
                    graph_kind=item.graph_kind.value,
                    from_stable_id=item.from_stable_id,
                    to_stable_id=item.to_stable_id,
                    relationship=item.relationship,
                    source_revision_id=item.source_revision_id,
                    source_provider=item.source_provider,
                    source_kind=item.source_kind,
                    source_external_id=item.source_external_id,
                    source_uri=item.source_uri,
                    source_occurred_at=item.source_occurred_at,
                    source_observed_at=item.source_observed_at,
                    assertion_status=item.assertion_status.value,
                    confidence=item.confidence,
                    confidence_explanation=item.confidence_explanation,
                )
                for item in projection.graph_edges
            ]
        )
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise DuplicateResourceError("project intelligence projection") from exc

    async def get(self, project_id: uuid.UUID) -> ProjectIntelligenceProjection | None:
        checkpoint = await self._session.get(models.ProjectIntelligenceProjection, project_id)
        if checkpoint is None:
            return None
        work_items = await self._session.scalars(
            select(models.ProjectIntelligenceWorkItem)
            .where(models.ProjectIntelligenceWorkItem.project_id == project_id)
            .order_by(
                models.ProjectIntelligenceWorkItem.kind,
                models.ProjectIntelligenceWorkItem.stable_id,
            )
        )
        aliases = await self._session.scalars(
            select(models.ProjectIntelligenceProviderAlias)
            .where(models.ProjectIntelligenceProviderAlias.project_id == project_id)
            .order_by(
                models.ProjectIntelligenceProviderAlias.provider,
                models.ProjectIntelligenceProviderAlias.account,
                models.ProjectIntelligenceProviderAlias.external_kind,
                models.ProjectIntelligenceProviderAlias.external_id,
            )
        )
        nodes = await self._session.scalars(
            select(models.ProjectIntelligenceGraphNode)
            .where(models.ProjectIntelligenceGraphNode.project_id == project_id)
            .order_by(
                models.ProjectIntelligenceGraphNode.graph_kind,
                models.ProjectIntelligenceGraphNode.stable_id,
            )
        )
        edges = await self._session.scalars(
            select(models.ProjectIntelligenceGraphEdge)
            .where(models.ProjectIntelligenceGraphEdge.project_id == project_id)
            .order_by(
                models.ProjectIntelligenceGraphEdge.graph_kind,
                models.ProjectIntelligenceGraphEdge.stable_id,
            )
        )
        revision_model = await self._session.get(
            models.ProjectStateRevision, checkpoint.source_revision_id
        )
        if revision_model is None:
            raise RuntimeError("project intelligence projection source revision is missing")
        assurance = build_projection(_project_state_revision(revision_model), checkpoint.rebuilt_at)
        return ProjectIntelligenceProjection(
            checkpoint=ProjectProjectionCheckpoint(
                project_id=checkpoint.project_id,
                source_revision_id=checkpoint.source_revision_id,
                source_version=checkpoint.source_version,
                rebuilt_at=checkpoint.rebuilt_at,
            ),
            work_items=tuple(_project_work_item(item) for item in work_items),
            aliases=tuple(
                ProjectProviderAlias(
                    id=item.id,
                    project_id=item.project_id,
                    canonical_id=item.canonical_id,
                    provider=item.provider,
                    account=item.account,
                    external_kind=item.external_kind,
                    external_id=item.external_id,
                    uri=item.uri,
                    source_revision_id=item.source_revision_id,
                )
                for item in aliases
            ),
            graph_nodes=tuple(_project_graph_node(item) for item in nodes),
            graph_edges=tuple(_project_graph_edge(item) for item in edges),
            validation_results=assurance.validation_results,
            risks=assurance.risks,
            technical_debt=assurance.technical_debt,
        )


class SqlAlchemyBudgetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, budget: Budget) -> Budget:
        self._session.add(
            models.Budget(
                id=budget.id,
                project_id=budget.project_id,
                monthly_limit=budget.monthly_limit,
                currency=budget.currency,
                enforcement_mode=budget.enforcement_mode.value,
                version=budget.version,
                created_at=budget.created_at,
                updated_at=budget.updated_at,
            )
        )
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise DuplicateResourceError("project budget") from exc
        return budget

    async def get(self, project_id: uuid.UUID, budget_id: uuid.UUID) -> Budget | None:
        result = await self._session.scalars(
            select(models.Budget).where(
                models.Budget.id == budget_id,
                models.Budget.project_id == project_id,
            )
        )
        model = result.one_or_none()
        return None if model is None else _budget(model)

    async def list(self, project_id: uuid.UUID) -> Sequence[Budget]:
        result = await self._session.scalars(
            select(models.Budget)
            .where(models.Budget.project_id == project_id)
            .order_by(models.Budget.created_at, models.Budget.id)
        )
        return [_budget(model) for model in result]

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
        now = datetime.now(UTC)
        result = await self._session.scalars(
            update(models.Budget)
            .where(
                models.Budget.id == budget_id,
                models.Budget.project_id == project_id,
                models.Budget.version == expected_version,
            )
            .values(
                monthly_limit=monthly_limit,
                currency=currency,
                enforcement_mode=enforcement_mode,
                version=expected_version + 1,
                updated_at=now,
            )
            .returning(models.Budget)
        )
        model = result.one_or_none()
        if model is not None:
            return _budget(model)
        if await self.get(project_id, budget_id) is None:
            return None
        raise StaleVersionError("budget", expected_version)


class SqlAlchemyCostEvaluationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, evaluation: CostEvaluation) -> CostEvaluation:
        self._session.add(
            models.CostEvaluation(
                id=evaluation.id,
                project_id=evaluation.project_id,
                budget_id=evaluation.budget_id,
                workflow_run_id=evaluation.workflow_run_id,
                idempotency_key=evaluation.idempotency_key,
                request_fingerprint=evaluation.request_fingerprint,
                currency=evaluation.currency,
                budget_monthly_limit=evaluation.budget_monthly_limit,
                budget_version=evaluation.budget_version,
                enforcement_mode=evaluation.enforcement_mode.value,
                selected_option=_option_payload(evaluation.selected_option),
                alternatives=[_option_payload(item) for item in evaluation.alternatives],
                selected_one_time_cost=evaluation.selected_option.one_time_cost,
                selected_monthly_cost=evaluation.selected_option.monthly_cost,
                outcome=evaluation.outcome.value,
                monthly_overage=evaluation.monthly_overage,
                recommendation=(
                    None
                    if evaluation.recommendation is None
                    else _recommendation_payload(evaluation.recommendation)
                ),
                algorithm_version=evaluation.algorithm_version,
                created_at=evaluation.created_at,
            )
        )
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise DuplicateResourceError("cost evaluation") from exc
        return evaluation

    async def get(self, project_id: uuid.UUID, evaluation_id: uuid.UUID) -> CostEvaluation | None:
        result = await self._session.scalars(
            select(models.CostEvaluation).where(
                models.CostEvaluation.id == evaluation_id,
                models.CostEvaluation.project_id == project_id,
            )
        )
        model = result.one_or_none()
        return None if model is None else _cost_evaluation(model)

    async def get_by_idempotency_key(
        self, project_id: uuid.UUID, idempotency_key: str
    ) -> CostEvaluation | None:
        result = await self._session.scalars(
            select(models.CostEvaluation).where(
                models.CostEvaluation.project_id == project_id,
                models.CostEvaluation.idempotency_key == idempotency_key,
            )
        )
        model = result.one_or_none()
        return None if model is None else _cost_evaluation(model)

    async def list(self, project_id: uuid.UUID) -> Sequence[CostEvaluation]:
        result = await self._session.scalars(
            select(models.CostEvaluation)
            .where(models.CostEvaluation.project_id == project_id)
            .order_by(models.CostEvaluation.created_at, models.CostEvaluation.id)
        )
        return [_cost_evaluation(model) for model in result]


class SqlAlchemyDecisionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, decision: Decision) -> Decision:
        self._session.add(
            models.Decision(
                id=decision.id,
                project_id=decision.project_id,
                cost_evaluation_id=decision.cost_evaluation_id,
                title=decision.title,
                context=decision.context,
                selected_option=decision.selected_option,
                alternatives=list(decision.alternatives),
                currency=decision.currency,
                estimated_one_time_cost=decision.estimated_one_time_cost,
                estimated_monthly_cost=decision.estimated_monthly_cost,
                risk=decision.risk.value,
                confidence=decision.confidence,
                rationale=decision.rationale,
                status=decision.status.value,
                decided_by=decision.decided_by,
                decision_note=decision.decision_note,
                outcome=decision.outcome,
                authorization_budget_version=decision.authorization_budget_version,
                authorization_monthly_limit=decision.authorization_monthly_limit,
                version=decision.version,
                decided_at=decision.decided_at,
                created_at=decision.created_at,
                updated_at=decision.updated_at,
            )
        )
        await self._session.flush()
        return decision

    async def get(self, project_id: uuid.UUID, decision_id: uuid.UUID) -> Decision | None:
        result = await self._session.scalars(
            select(models.Decision).where(
                models.Decision.id == decision_id,
                models.Decision.project_id == project_id,
            )
        )
        model = result.one_or_none()
        return None if model is None else _decision(model)

    async def list(self, project_id: uuid.UUID) -> Sequence[Decision]:
        result = await self._session.scalars(
            select(models.Decision)
            .where(models.Decision.project_id == project_id)
            .order_by(models.Decision.created_at, models.Decision.id)
        )
        return [_decision(model) for model in result]

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
        result = await self._session.scalars(
            update(models.Decision)
            .where(
                models.Decision.id == decision_id,
                models.Decision.project_id == project_id,
                models.Decision.version == expected_version,
                models.Decision.status == DecisionStatus.PROPOSED.value,
            )
            .values(
                status=status,
                decided_by=decided_by,
                decision_note=decision_note,
                outcome=outcome,
                authorization_budget_version=authorization_budget_version,
                authorization_monthly_limit=authorization_monthly_limit,
                version=expected_version + 1,
                decided_at=decided_at,
                updated_at=decided_at,
            )
            .returning(models.Decision)
        )
        model = result.one_or_none()
        if model is not None:
            return _decision(model)
        current = await self.get(project_id, decision_id)
        if current is None:
            return None
        if current.version != expected_version:
            raise StaleVersionError("decision", expected_version)
        raise InvalidTransitionError("decision", current.status.value, status)


class SqlAlchemyWorkflowRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, workflow_run: WorkflowRun) -> WorkflowRun:
        try:
            async with self._session.begin_nested():
                self._session.add(
                    models.WorkflowRun(
                        id=workflow_run.id,
                        project_id=workflow_run.project_id,
                        workflow_kind=workflow_run.workflow_kind,
                        idempotency_key=workflow_run.idempotency_key,
                        input_payload=workflow_run.input_payload,
                        status=workflow_run.status.value,
                        temporal_workflow_id=workflow_run.temporal_workflow_id,
                        retry_of_run_id=workflow_run.retry_of_run_id,
                        cost_estimate=workflow_run.cost_estimate,
                        version=workflow_run.version,
                        cancellation_requested_at=workflow_run.cancellation_requested_at,
                        started_at=workflow_run.started_at,
                        completed_at=workflow_run.completed_at,
                        created_at=workflow_run.created_at,
                        updated_at=workflow_run.updated_at,
                    )
                )
                await self._session.flush()
        except IntegrityError as exc:
            existing = await self.get_by_idempotency_key(
                workflow_run.project_id, workflow_run.idempotency_key
            )
            if existing is not None:
                return existing
            raise DuplicateResourceError("workflow run") from exc
        return workflow_run

    async def get(self, project_id: uuid.UUID, workflow_run_id: uuid.UUID) -> WorkflowRun | None:
        result = await self._session.scalars(
            select(models.WorkflowRun).where(
                models.WorkflowRun.id == workflow_run_id,
                models.WorkflowRun.project_id == project_id,
            )
        )
        model = result.one_or_none()
        return None if model is None else _workflow_run(model)

    async def get_by_idempotency_key(
        self, project_id: uuid.UUID, idempotency_key: str
    ) -> WorkflowRun | None:
        result = await self._session.scalars(
            select(models.WorkflowRun).where(
                models.WorkflowRun.project_id == project_id,
                models.WorkflowRun.idempotency_key == idempotency_key,
            )
        )
        model = result.one_or_none()
        return None if model is None else _workflow_run(model)

    async def list(self, project_id: uuid.UUID) -> Sequence[WorkflowRun]:
        result = await self._session.scalars(
            select(models.WorkflowRun)
            .where(models.WorkflowRun.project_id == project_id)
            .order_by(models.WorkflowRun.created_at, models.WorkflowRun.id)
        )
        return [_workflow_run(model) for model in result]

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
        now = datetime.now(UTC)
        try:
            result = await self._session.scalars(
                update(models.WorkflowRun)
                .where(
                    models.WorkflowRun.id == workflow_run_id,
                    models.WorkflowRun.project_id == project_id,
                    models.WorkflowRun.version == expected_version,
                )
                .values(
                    status=status,
                    temporal_workflow_id=temporal_workflow_id,
                    cancellation_requested_at=cancellation_requested_at,
                    started_at=started_at,
                    completed_at=completed_at,
                    version=expected_version + 1,
                    updated_at=now,
                )
                .returning(models.WorkflowRun)
            )
        except IntegrityError as exc:
            raise DuplicateResourceError("Temporal workflow correlation") from exc
        model = result.one_or_none()
        if model is not None:
            return _workflow_run(model)
        if await self.get(project_id, workflow_run_id) is None:
            return None
        raise StaleVersionError("workflow run", expected_version)


class SqlAlchemyWorkflowStepRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, step: WorkflowStep) -> WorkflowStep:
        self._session.add(
            models.WorkflowStep(
                id=step.id,
                workflow_run_id=step.workflow_run_id,
                key=step.key,
                name=step.name,
                position=step.position,
                status=step.status.value,
                version=step.version,
                created_at=step.created_at,
                updated_at=step.updated_at,
            )
        )
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise DuplicateResourceError("workflow step") from exc
        return step

    async def get(
        self, workflow_run_id: uuid.UUID, workflow_step_id: uuid.UUID
    ) -> WorkflowStep | None:
        result = await self._session.scalars(
            select(models.WorkflowStep).where(
                models.WorkflowStep.id == workflow_step_id,
                models.WorkflowStep.workflow_run_id == workflow_run_id,
            )
        )
        model = result.one_or_none()
        return None if model is None else _workflow_step(model)

    async def list(self, workflow_run_id: uuid.UUID) -> Sequence[WorkflowStep]:
        result = await self._session.scalars(
            select(models.WorkflowStep)
            .where(models.WorkflowStep.workflow_run_id == workflow_run_id)
            .order_by(models.WorkflowStep.position, models.WorkflowStep.id)
        )
        return [_workflow_step(model) for model in result]

    async def update_status(
        self,
        workflow_run_id: uuid.UUID,
        workflow_step_id: uuid.UUID,
        expected_version: int,
        *,
        status: str,
    ) -> WorkflowStep | None:
        now = datetime.now(UTC)
        result = await self._session.scalars(
            update(models.WorkflowStep)
            .where(
                models.WorkflowStep.id == workflow_step_id,
                models.WorkflowStep.workflow_run_id == workflow_run_id,
                models.WorkflowStep.version == expected_version,
            )
            .values(status=status, version=expected_version + 1, updated_at=now)
            .returning(models.WorkflowStep)
        )
        model = result.one_or_none()
        if model is not None:
            return _workflow_step(model)
        if await self.get(workflow_run_id, workflow_step_id) is None:
            return None
        raise StaleVersionError("workflow step", expected_version)


class SqlAlchemyWorkflowStepAttemptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, attempt: WorkflowStepAttempt) -> WorkflowStepAttempt:
        self._session.add(
            models.WorkflowStepAttempt(
                id=attempt.id,
                workflow_step_id=attempt.workflow_step_id,
                attempt_number=attempt.attempt_number,
                status=attempt.status.value,
                result_payload=attempt.result_payload,
                error_payload=attempt.error_payload,
                started_at=attempt.started_at,
                completed_at=attempt.completed_at,
                created_at=attempt.created_at,
            )
        )
        try:
            await self._session.flush()
        except IntegrityError as exc:
            raise DuplicateResourceError("workflow step attempt") from exc
        return attempt

    async def list(self, workflow_step_id: uuid.UUID) -> Sequence[WorkflowStepAttempt]:
        result = await self._session.scalars(
            select(models.WorkflowStepAttempt)
            .where(models.WorkflowStepAttempt.workflow_step_id == workflow_step_id)
            .order_by(
                models.WorkflowStepAttempt.attempt_number,
                models.WorkflowStepAttempt.id,
            )
        )
        return [_workflow_step_attempt(model) for model in result]


class SqlAlchemyOutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, message: OutboxMessage) -> OutboxMessage:
        organization_id = message.payload.get("organization_id")
        project_id = message.payload.get("project_id")
        self._session.add(
            models.OutboxEvent(
                id=message.id,
                occurred_at=message.occurred_at,
                topic=message.topic,
                aggregate_id=message.aggregate_id,
                payload=message.payload,
                available_at=message.occurred_at,
            )
        )
        self._session.add(
            models.AuditEvent(
                occurred_at=message.occurred_at,
                actor_type=message.actor_type,
                actor_id=message.actor_id,
                action=message.topic,
                object_type=message.topic.removeprefix("genesis.").rsplit(".", 1)[0],
                object_id=message.aggregate_id,
                organization_id=(
                    uuid.UUID(organization_id) if isinstance(organization_id, str) else None
                ),
                project_id=uuid.UUID(project_id) if isinstance(project_id, str) else None,
                correlation_id=str(message.id),
                outcome="success",
                payload={"event_id": str(message.id), **message.payload},
            )
        )
        await self._session.flush()
        return message


class SqlAlchemyEvidenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, evidence: Evidence) -> Evidence:
        self._session.add(
            models.Evidence(
                id=evidence.id,
                project_id=evidence.project_id,
                workflow_run_id=evidence.workflow_run_id,
                workflow_step_attempt_id=evidence.workflow_step_attempt_id,
                kind=evidence.kind.value,
                name=evidence.name,
                content_type=evidence.content_type,
                object_key=evidence.object_key,
                sha256=evidence.sha256,
                size_bytes=evidence.size_bytes,
                retention_class=evidence.retention_class.value,
                retain_until=evidence.retain_until,
                created_at=evidence.created_at,
            )
        )
        await self._session.flush()
        return evidence

    async def get(self, project_id: uuid.UUID, evidence_id: uuid.UUID) -> Evidence | None:
        result = await self._session.scalar(
            select(models.Evidence).where(
                models.Evidence.id == evidence_id, models.Evidence.project_id == project_id
            )
        )
        return None if result is None else _evidence(result)

    async def list(self, project_id: uuid.UUID) -> Sequence[Evidence]:
        result = await self._session.scalars(
            select(models.Evidence)
            .where(models.Evidence.project_id == project_id)
            .order_by(models.Evidence.created_at, models.Evidence.id)
        )
        return [_evidence(item) for item in result]
