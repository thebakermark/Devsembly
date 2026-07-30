from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from devsembly.cost_schemas import (
    CostEvaluationCreate,
    CostEvaluationRead,
    CostOptionCreate,
    DecisionCreate,
    DecisionRead,
    DecisionResolveRequest,
)
from devsembly.cost_service import CostGovernanceService
from devsembly.domain import (
    CostLineItem,
    CostOptionDefinition,
    DecisionStatus,
)
from devsembly.unit_of_work import SqlAlchemyUnitOfWork

router = APIRouter(prefix="/api/v1/organizations", tags=["Genesis cost governance"])

PROJECT_PATH = "/{organization_id}/initiatives/{initiative_id}/projects/{project_id}"
COST_EVALUATIONS_PATH = f"{PROJECT_PATH}/cost-evaluations"
DECISIONS_PATH = f"{PROJECT_PATH}/decisions"


def get_cost_governance_service() -> CostGovernanceService:
    return CostGovernanceService(lambda: SqlAlchemyUnitOfWork())


Service = Annotated[CostGovernanceService, Depends(get_cost_governance_service)]


def _option_definition(option: CostOptionCreate) -> CostOptionDefinition:
    return CostOptionDefinition(
        key=option.key,
        name=option.name,
        satisfies_acceptance_criteria=option.satisfies_acceptance_criteria,
        line_items=tuple(
            CostLineItem(
                category=item.category,
                description=item.description,
                cadence=item.cadence,
                quantity=item.quantity,
                unit_cost=item.unit_cost,
            )
            for item in option.line_items
        ),
    )


@router.post(
    COST_EVALUATIONS_PATH,
    response_model=CostEvaluationRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_cost_evaluation(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    payload: CostEvaluationCreate,
    response: Response,
    service: Service,
) -> CostEvaluationRead:
    evaluation, created = await service.evaluate_costs(
        organization_id,
        initiative_id,
        project_id,
        idempotency_key=payload.idempotency_key,
        workflow_run_id=payload.workflow_run_id,
        selected_option=_option_definition(payload.selected_option),
        alternatives=tuple(_option_definition(item) for item in payload.alternatives),
    )
    if not created:
        response.status_code = status.HTTP_200_OK
    return CostEvaluationRead.model_validate(evaluation)


@router.get(COST_EVALUATIONS_PATH, response_model=list[CostEvaluationRead])
async def list_cost_evaluations(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    service: Service,
) -> list[CostEvaluationRead]:
    evaluations = await service.list_cost_evaluations(organization_id, initiative_id, project_id)
    return [CostEvaluationRead.model_validate(item) for item in evaluations]


@router.get(
    f"{COST_EVALUATIONS_PATH}/{{evaluation_id}}",
    response_model=CostEvaluationRead,
)
async def get_cost_evaluation(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    evaluation_id: uuid.UUID,
    service: Service,
) -> CostEvaluationRead:
    evaluation = await service.get_cost_evaluation(
        organization_id,
        initiative_id,
        project_id,
        evaluation_id,
    )
    return CostEvaluationRead.model_validate(evaluation)


@router.post(
    DECISIONS_PATH,
    response_model=DecisionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_decision(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    payload: DecisionCreate,
    service: Service,
) -> DecisionRead:
    decision = await service.create_decision(
        organization_id,
        initiative_id,
        project_id,
        cost_evaluation_id=payload.cost_evaluation_id,
        title=payload.title,
        context=payload.context,
        selected_option=payload.selected_option,
        alternatives=[item.model_dump(mode="json") for item in payload.alternatives],
        currency=payload.currency,
        estimated_one_time_cost=payload.estimated_one_time_cost,
        estimated_monthly_cost=payload.estimated_monthly_cost,
        risk=payload.risk,
        confidence=payload.confidence,
        rationale=payload.rationale,
    )
    return DecisionRead.model_validate(decision)


@router.get(DECISIONS_PATH, response_model=list[DecisionRead])
async def list_decisions(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    service: Service,
) -> list[DecisionRead]:
    decisions = await service.list_decisions(organization_id, initiative_id, project_id)
    return [DecisionRead.model_validate(item) for item in decisions]


@router.get(
    f"{DECISIONS_PATH}/{{decision_id}}",
    response_model=DecisionRead,
)
async def get_decision(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    decision_id: uuid.UUID,
    service: Service,
) -> DecisionRead:
    decision = await service.get_decision(
        organization_id,
        initiative_id,
        project_id,
        decision_id,
    )
    return DecisionRead.model_validate(decision)


@router.post(
    f"{DECISIONS_PATH}/{{decision_id}}/resolve",
    response_model=DecisionRead,
)
async def resolve_decision(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    decision_id: uuid.UUID,
    payload: DecisionResolveRequest,
    service: Service,
) -> DecisionRead:
    decision = await service.resolve_decision(
        organization_id,
        initiative_id,
        project_id,
        decision_id,
        payload.expected_version,
        status=DecisionStatus(payload.status.value),
        decided_by=payload.decided_by,
        decision_note=payload.decision_note,
        outcome=payload.outcome,
    )
    return DecisionRead.model_validate(decision)
