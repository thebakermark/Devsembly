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
    model_validator,
)

from devsembly.domain import (
    BudgetEnforcementMode,
    CostCadence,
    CostEvaluationOutcome,
    DecisionRisk,
    DecisionStatus,
)
from devsembly.genesis_schemas import ExpectedVersion
from devsembly.workflow_schemas import IdempotencyKey


def _strip(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


ShortText = Annotated[
    str,
    BeforeValidator(_strip),
    Field(min_length=1, max_length=200),
]
LongText = Annotated[
    str,
    BeforeValidator(_strip),
    Field(min_length=1, max_length=4000),
]
Currency = Annotated[
    str,
    BeforeValidator(_strip),
    Field(pattern=r"^[A-Z]{3}$"),
]
Money = Annotated[
    Decimal,
    Field(ge=Decimal(0), max_digits=14, decimal_places=4),
]
Quantity = Annotated[
    Decimal,
    Field(gt=Decimal(0), max_digits=12, decimal_places=4),
]
Confidence = Annotated[
    Decimal,
    Field(ge=Decimal(0), le=Decimal(1), max_digits=5, decimal_places=4),
]


class DecisionResolution(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class CostLineItemCreate(BaseModel):
    category: ShortText
    description: ShortText
    cadence: CostCadence
    quantity: Quantity = Decimal(1)
    unit_cost: Money


class CostOptionCreate(BaseModel):
    key: ShortText
    name: ShortText
    satisfies_acceptance_criteria: bool
    line_items: Annotated[list[CostLineItemCreate], Field(min_length=1, max_length=100)]


class CostEvaluationCreate(BaseModel):
    idempotency_key: IdempotencyKey
    workflow_run_id: uuid.UUID | None = None
    selected_option: CostOptionCreate
    alternatives: Annotated[list[CostOptionCreate], Field(max_length=20)] = Field(
        default_factory=list
    )

    @model_validator(mode="after")
    def option_keys_are_unique(self) -> CostEvaluationCreate:
        keys = [self.selected_option.key, *(item.key for item in self.alternatives)]
        if len(keys) != len(set(keys)):
            raise ValueError("cost option keys must be unique")
        return self


class CostLineItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: str
    description: str
    cadence: CostCadence
    quantity: Decimal
    unit_cost: Decimal


class CostOptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    name: str
    satisfies_acceptance_criteria: bool
    line_items: list[CostLineItemRead]
    one_time_cost: Decimal
    monthly_cost: Decimal


class CostRecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    option_key: str
    monthly_savings: Decimal
    one_time_savings: Decimal
    fits_monthly_budget: bool
    rationale: str
    algorithm_version: str


class CostEvaluationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    budget_id: uuid.UUID
    workflow_run_id: uuid.UUID | None
    idempotency_key: str
    currency: str
    budget_monthly_limit: Decimal
    budget_version: int
    enforcement_mode: BudgetEnforcementMode
    selected_option: CostOptionRead
    alternatives: list[CostOptionRead]
    outcome: CostEvaluationOutcome
    monthly_overage: Decimal
    recommendation: CostRecommendationRead | None
    algorithm_version: str
    created_at: datetime


class DecisionAlternativeCreate(BaseModel):
    key: ShortText
    description: LongText


class DecisionCreate(BaseModel):
    cost_evaluation_id: uuid.UUID | None = None
    title: Annotated[
        str,
        BeforeValidator(_strip),
        Field(min_length=1, max_length=250),
    ]
    context: LongText
    selected_option: LongText | None = None
    alternatives: Annotated[list[DecisionAlternativeCreate], Field(max_length=20)] = Field(
        default_factory=list
    )
    currency: Currency | None = None
    estimated_one_time_cost: Money | None = None
    estimated_monthly_cost: Money | None = None
    risk: DecisionRisk
    confidence: Confidence
    rationale: LongText

    @model_validator(mode="after")
    def direct_costs_are_complete(self) -> DecisionCreate:
        direct_values = (
            self.currency,
            self.estimated_one_time_cost,
            self.estimated_monthly_cost,
        )
        if self.cost_evaluation_id is None and any(value is None for value in direct_values):
            raise ValueError("currency and estimated costs are required without a cost evaluation")
        if self.cost_evaluation_id is None and self.selected_option is None:
            raise ValueError("selected_option is required without a cost evaluation")
        if self.cost_evaluation_id is not None and any(
            value is not None for value in direct_values
        ):
            raise ValueError("costs and currency are derived from the cost evaluation")
        if self.cost_evaluation_id is not None and self.selected_option is not None:
            raise ValueError("selected_option is derived from the cost evaluation")
        if self.cost_evaluation_id is not None and self.alternatives:
            raise ValueError("alternatives are derived from the cost evaluation")
        return self


class DecisionResolveRequest(BaseModel):
    expected_version: ExpectedVersion
    status: DecisionResolution
    decided_by: Annotated[
        str,
        BeforeValidator(_strip),
        Field(min_length=1, max_length=255),
    ]
    decision_note: LongText
    outcome: LongText


class DecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    cost_evaluation_id: uuid.UUID | None
    title: str
    context: str
    selected_option: str
    alternatives: list[dict[str, object]]
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
