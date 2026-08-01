from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from devsembly.audit import current_audit_actor
from devsembly.domain import (
    Budget,
    BudgetEnforcementMode,
    CostCadence,
    CostEvaluation,
    CostEvaluationOutcome,
    CostOption,
    CostOptionDefinition,
    CostRecommendation,
    Decision,
    DecisionRisk,
    DecisionStatus,
    Initiative,
    OutboxMessage,
    Project,
)
from devsembly.errors import (
    CostGovernanceError,
    IdempotencyConflictError,
    InvalidTransitionError,
    ResourceNotFoundError,
    StaleVersionError,
)
from devsembly.unit_of_work import UnitOfWork

UnitOfWorkFactory = Callable[[], UnitOfWork]
Clock = Callable[[], datetime]

MONEY_QUANTUM = Decimal("0.0001")
MAX_MONEY = Decimal("9999999999.9999")
COST_ALGORITHM_VERSION = "genesis-cost-v1"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


class CostGovernanceService:
    def __init__(self, unit_of_work: UnitOfWorkFactory, clock: Clock = _utc_now) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    def _message(
        self, topic: str, aggregate_id: uuid.UUID, payload: dict[str, object]
    ) -> OutboxMessage:
        actor_type, actor_id = current_audit_actor()
        return OutboxMessage(
            id=uuid.uuid4(),
            occurred_at=self._clock(),
            topic=topic,
            aggregate_id=str(aggregate_id),
            payload=payload,
            actor_type=actor_type,
            actor_id=actor_id,
        )

    @staticmethod
    def _option(definition: CostOptionDefinition) -> CostOption:
        one_time = Decimal(0)
        monthly = Decimal(0)
        for item in definition.line_items:
            extended = item.quantity * item.unit_cost
            if item.cadence is CostCadence.ONE_TIME:
                one_time += extended
            else:
                monthly += extended
        one_time = one_time.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
        monthly = monthly.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
        if one_time > MAX_MONEY or monthly > MAX_MONEY:
            raise CostGovernanceError(f"option {definition.key!r} exceeds the supported cost range")
        return CostOption(
            key=definition.key,
            name=definition.name,
            satisfies_acceptance_criteria=definition.satisfies_acceptance_criteria,
            line_items=definition.line_items,
            one_time_cost=one_time,
            monthly_cost=monthly,
        )

    @staticmethod
    def _definition_payload(definition: CostOptionDefinition) -> dict[str, object]:
        return {
            "key": definition.key,
            "name": definition.name,
            "satisfies_acceptance_criteria": definition.satisfies_acceptance_criteria,
            "line_items": [
                {
                    "category": item.category,
                    "description": item.description,
                    "cadence": item.cadence.value,
                    "quantity": _decimal_text(item.quantity),
                    "unit_cost": _decimal_text(item.unit_cost),
                }
                for item in definition.line_items
            ],
        }

    @classmethod
    def _fingerprint(
        cls,
        workflow_run_id: uuid.UUID | None,
        selected_option: CostOptionDefinition,
        alternatives: Sequence[CostOptionDefinition],
    ) -> str:
        payload = {
            "workflow_run_id": None if workflow_run_id is None else str(workflow_run_id),
            "selected_option": cls._definition_payload(selected_option),
            "alternatives": [cls._definition_payload(item) for item in alternatives],
        }
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode()
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _outcome(budget: Budget, selected: CostOption) -> CostEvaluationOutcome:
        if selected.monthly_cost <= budget.monthly_limit:
            return CostEvaluationOutcome.WITHIN_BUDGET
        if budget.enforcement_mode is BudgetEnforcementMode.OBSERVE:
            return CostEvaluationOutcome.OBSERVED_OVERAGE
        if budget.enforcement_mode is BudgetEnforcementMode.WARN:
            return CostEvaluationOutcome.APPROVAL_REQUIRED
        return CostEvaluationOutcome.BLOCKED

    @staticmethod
    def _recommendation(
        budget: Budget,
        selected: CostOption,
        alternatives: Sequence[CostOption],
    ) -> CostRecommendation | None:
        candidates = [
            option
            for option in alternatives
            if option.satisfies_acceptance_criteria
            and option.monthly_cost < selected.monthly_cost
            and option.monthly_cost <= budget.monthly_limit
        ]
        if not candidates:
            return None
        recommended = min(
            candidates,
            key=lambda option: (option.monthly_cost, option.one_time_cost, option.key),
        )
        monthly_savings = (selected.monthly_cost - recommended.monthly_cost).quantize(MONEY_QUANTUM)
        one_time_savings = max(
            Decimal(0),
            selected.one_time_cost - recommended.one_time_cost,
        ).quantize(MONEY_QUANTUM)
        rationale = (
            f"{recommended.name} is the lowest-monthly-cost supplied option that "
            f"satisfies the acceptance criteria and fits the {budget.currency} "
            f"{budget.monthly_limit:.2f} monthly limit; it saves "
            f"{budget.currency} {monthly_savings:.4f} per month."
        )
        return CostRecommendation(
            option_key=recommended.key,
            monthly_savings=monthly_savings,
            one_time_savings=one_time_savings,
            fits_monthly_budget=True,
            rationale=rationale,
            algorithm_version=COST_ALGORITHM_VERSION,
        )

    async def evaluate_costs(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
        *,
        idempotency_key: str,
        workflow_run_id: uuid.UUID | None,
        selected_option: CostOptionDefinition,
        alternatives: Sequence[CostOptionDefinition],
    ) -> tuple[CostEvaluation, bool]:
        fingerprint = self._fingerprint(workflow_run_id, selected_option, alternatives)
        async with self._unit_of_work() as unit:
            await self._require_project(unit, organization_id, initiative_id, project_id)
            existing = await unit.cost_evaluations.get_by_idempotency_key(
                project_id, idempotency_key
            )
            if existing is not None:
                if existing.request_fingerprint == fingerprint:
                    return existing, False
                raise IdempotencyConflictError(idempotency_key)

            if workflow_run_id is not None:
                workflow_run = await unit.workflow_runs.get(project_id, workflow_run_id)
                if workflow_run is None:
                    raise ResourceNotFoundError("workflow run")
            budget = await self._require_budget(unit, project_id)
            selected = self._option(selected_option)
            resolved_alternatives = tuple(self._option(item) for item in alternatives)
            outcome = self._outcome(budget, selected)
            overage = max(
                Decimal(0),
                selected.monthly_cost - budget.monthly_limit,
            ).quantize(MONEY_QUANTUM)
            recommendation = self._recommendation(
                budget,
                selected,
                resolved_alternatives,
            )
            evaluation = CostEvaluation(
                id=uuid.uuid4(),
                project_id=project_id,
                budget_id=budget.id,
                workflow_run_id=workflow_run_id,
                idempotency_key=idempotency_key,
                request_fingerprint=fingerprint,
                currency=budget.currency,
                budget_monthly_limit=budget.monthly_limit.quantize(MONEY_QUANTUM),
                budget_version=budget.version,
                enforcement_mode=budget.enforcement_mode,
                selected_option=selected,
                alternatives=resolved_alternatives,
                outcome=outcome,
                monthly_overage=overage,
                recommendation=recommendation,
                algorithm_version=COST_ALGORITHM_VERSION,
                created_at=self._clock(),
            )
            await unit.cost_evaluations.add(evaluation)
            await unit.outbox.add(
                self._message(
                    "genesis.cost_evaluation.created",
                    evaluation.id,
                    {
                        "organization_id": str(organization_id),
                        "initiative_id": str(initiative_id),
                        "project_id": str(project_id),
                        "budget_id": str(budget.id),
                        "budget_version": budget.version,
                        "cost_evaluation_id": str(evaluation.id),
                        "outcome": outcome.value,
                        "recommended_option_key": (
                            None if recommendation is None else recommendation.option_key
                        ),
                    },
                )
            )
            await unit.commit()
            return evaluation, True

    async def get_cost_evaluation(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
        evaluation_id: uuid.UUID,
    ) -> CostEvaluation:
        async with self._unit_of_work() as unit:
            await self._require_project(unit, organization_id, initiative_id, project_id)
            evaluation = await unit.cost_evaluations.get(project_id, evaluation_id)
            if evaluation is None:
                raise ResourceNotFoundError("cost evaluation")
            return evaluation

    async def list_cost_evaluations(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> Sequence[CostEvaluation]:
        async with self._unit_of_work() as unit:
            await self._require_project(unit, organization_id, initiative_id, project_id)
            return await unit.cost_evaluations.list(project_id)

    async def create_decision(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
        *,
        cost_evaluation_id: uuid.UUID | None,
        title: str,
        context: str,
        selected_option: str | None,
        alternatives: Sequence[dict[str, object]],
        currency: str | None,
        estimated_one_time_cost: Decimal | None,
        estimated_monthly_cost: Decimal | None,
        risk: DecisionRisk,
        confidence: Decimal,
        rationale: str,
    ) -> Decision:
        async with self._unit_of_work() as unit:
            await self._require_project(unit, organization_id, initiative_id, project_id)
            resolved_alternatives: tuple[dict[str, object], ...]
            if cost_evaluation_id is not None:
                evaluation = await unit.cost_evaluations.get(project_id, cost_evaluation_id)
                if evaluation is None:
                    raise ResourceNotFoundError("cost evaluation")
                resolved_selected_option = evaluation.selected_option.key
                resolved_alternatives = tuple(
                    {
                        "key": item.key,
                        "description": (
                            f"{item.name}: {evaluation.currency} "
                            f"{item.one_time_cost:.4f} one-time, "
                            f"{evaluation.currency} {item.monthly_cost:.4f} monthly"
                        ),
                    }
                    for item in evaluation.alternatives
                )
                resolved_currency = evaluation.currency
                resolved_one_time_cost = evaluation.selected_option.one_time_cost
                resolved_monthly_cost = evaluation.selected_option.monthly_cost
            else:
                if (
                    selected_option is None
                    or currency is None
                    or estimated_one_time_cost is None
                    or estimated_monthly_cost is None
                ):
                    raise CostGovernanceError(
                        "direct decisions require an option, currency, and cost estimates"
                    )
                resolved_selected_option = selected_option
                resolved_alternatives = tuple(alternatives)
                resolved_currency = currency
                resolved_one_time_cost = estimated_one_time_cost.quantize(MONEY_QUANTUM)
                resolved_monthly_cost = estimated_monthly_cost.quantize(MONEY_QUANTUM)

            now = self._clock()
            decision = Decision(
                id=uuid.uuid4(),
                project_id=project_id,
                cost_evaluation_id=cost_evaluation_id,
                title=title,
                context=context,
                selected_option=resolved_selected_option,
                alternatives=resolved_alternatives,
                currency=resolved_currency,
                estimated_one_time_cost=resolved_one_time_cost,
                estimated_monthly_cost=resolved_monthly_cost,
                risk=risk,
                confidence=confidence,
                rationale=rationale,
                status=DecisionStatus.PROPOSED,
                decided_by=None,
                decision_note=None,
                outcome=None,
                authorization_budget_version=None,
                authorization_monthly_limit=None,
                version=1,
                decided_at=None,
                created_at=now,
                updated_at=now,
            )
            await unit.decisions.add(decision)
            await unit.outbox.add(
                self._message(
                    "genesis.decision.proposed",
                    decision.id,
                    {
                        "organization_id": str(organization_id),
                        "initiative_id": str(initiative_id),
                        "project_id": str(project_id),
                        "decision_id": str(decision.id),
                        "cost_evaluation_id": (
                            None if cost_evaluation_id is None else str(cost_evaluation_id)
                        ),
                        "version": 1,
                    },
                )
            )
            await unit.commit()
            return decision

    async def get_decision(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
        decision_id: uuid.UUID,
    ) -> Decision:
        async with self._unit_of_work() as unit:
            await self._require_project(unit, organization_id, initiative_id, project_id)
            decision = await unit.decisions.get(project_id, decision_id)
            if decision is None:
                raise ResourceNotFoundError("decision")
            return decision

    async def list_decisions(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> Sequence[Decision]:
        async with self._unit_of_work() as unit:
            await self._require_project(unit, organization_id, initiative_id, project_id)
            return await unit.decisions.list(project_id)

    async def resolve_decision(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
        decision_id: uuid.UUID,
        expected_version: int,
        *,
        status: DecisionStatus,
        decided_by: str,
        decision_note: str,
        outcome: str,
    ) -> Decision:
        if status not in {DecisionStatus.APPROVED, DecisionStatus.REJECTED}:
            raise CostGovernanceError("a decision can only be approved or rejected")
        async with self._unit_of_work() as unit:
            await self._require_project(unit, organization_id, initiative_id, project_id)
            current = await unit.decisions.get(project_id, decision_id)
            if current is None:
                raise ResourceNotFoundError("decision")
            if current.version != expected_version:
                raise StaleVersionError("decision", expected_version)
            if current.status is not DecisionStatus.PROPOSED:
                raise InvalidTransitionError(
                    "decision",
                    current.status.value,
                    status.value,
                )

            authorization_budget_version: int | None = None
            authorization_monthly_limit: Decimal | None = None
            if status is DecisionStatus.APPROVED:
                budgets = await unit.budgets.list(project_id)
                current_budget = budgets[0] if budgets else None
                if current.cost_evaluation_id is not None:
                    evaluation = await unit.cost_evaluations.get(
                        project_id, current.cost_evaluation_id
                    )
                    if evaluation is None:
                        raise ResourceNotFoundError("cost evaluation")
                    if not evaluation.selected_option.satisfies_acceptance_criteria:
                        raise InvalidTransitionError(
                            "cost evaluation acceptance",
                            "not_satisfied",
                            DecisionStatus.APPROVED.value,
                        )
                    if current_budget is None:
                        raise ResourceNotFoundError("project budget")
                    if evaluation.outcome is CostEvaluationOutcome.BLOCKED and not (
                        current_budget.id == evaluation.budget_id
                        and current_budget.currency == evaluation.currency
                        and current_budget.version > evaluation.budget_version
                        and current.estimated_monthly_cost <= current_budget.monthly_limit
                    ):
                        raise InvalidTransitionError(
                            "cost evaluation",
                            evaluation.outcome.value,
                            DecisionStatus.APPROVED.value,
                        )
                if current_budget is not None and current_budget.currency != current.currency:
                    raise CostGovernanceError(
                        "decision currency does not match the active project budget"
                    )
                if (
                    current_budget is not None
                    and current_budget.enforcement_mode is BudgetEnforcementMode.BLOCK
                    and current.estimated_monthly_cost > current_budget.monthly_limit
                ):
                    raise InvalidTransitionError(
                        "project budget",
                        CostEvaluationOutcome.BLOCKED.value,
                        DecisionStatus.APPROVED.value,
                    )
                if current_budget is not None:
                    authorization_budget_version = current_budget.version
                    authorization_monthly_limit = current_budget.monthly_limit.quantize(
                        MONEY_QUANTUM
                    )

            now = self._clock()
            resolved = await unit.decisions.resolve(
                project_id,
                decision_id,
                expected_version,
                status=status.value,
                decided_by=decided_by,
                decision_note=decision_note,
                outcome=outcome,
                authorization_budget_version=authorization_budget_version,
                authorization_monthly_limit=authorization_monthly_limit,
                decided_at=now,
            )
            if resolved is None:
                raise ResourceNotFoundError("decision")
            await unit.outbox.add(
                self._message(
                    f"genesis.decision.{status.value}",
                    resolved.id,
                    {
                        "organization_id": str(organization_id),
                        "initiative_id": str(initiative_id),
                        "project_id": str(project_id),
                        "decision_id": str(resolved.id),
                        "status": status.value,
                        "declared_decider_id": decided_by,
                        "version": resolved.version,
                    },
                )
            )
            await unit.commit()
            return resolved

    @staticmethod
    async def _require_initiative(
        unit: UnitOfWork,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
    ) -> Initiative:
        initiative = await unit.initiatives.get(organization_id, initiative_id)
        if initiative is None:
            raise ResourceNotFoundError("initiative")
        return initiative

    @classmethod
    async def _require_project(
        cls,
        unit: UnitOfWork,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> Project:
        await cls._require_initiative(unit, organization_id, initiative_id)
        project = await unit.projects.get(initiative_id, project_id)
        if project is None:
            raise ResourceNotFoundError("project")
        return project

    @staticmethod
    async def _require_budget(unit: UnitOfWork, project_id: uuid.UUID) -> Budget:
        budgets = await unit.budgets.list(project_id)
        if not budgets:
            raise ResourceNotFoundError("project budget")
        return budgets[0]
