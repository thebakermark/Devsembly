from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from devsembly.domain import BudgetEnforcementMode, InitiativeStatus, ProjectStatus


def _strip(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


def _strip_optional(value: object) -> object:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    return stripped or None


def _currency(value: object) -> object:
    return value.strip().upper() if isinstance(value, str) else value


Name = Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=200)]
Objective = Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=10_000)]
RepositoryReference = Annotated[str | None, BeforeValidator(_strip_optional), Field(max_length=300)]
Currency = Annotated[
    str, BeforeValidator(_currency), Field(min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
]
MonthlyLimit = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]
ExpectedVersion = Annotated[int, Field(ge=1)]


class OrganizationCreate(BaseModel):
    name: Name


class OrganizationUpdate(BaseModel):
    expected_version: ExpectedVersion
    name: Name


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    version: int
    created_at: datetime
    updated_at: datetime


class InitiativeCreate(BaseModel):
    name: Name
    objective: Objective
    status: InitiativeStatus = InitiativeStatus.PROPOSED


class InitiativeUpdate(BaseModel):
    expected_version: ExpectedVersion
    name: Name
    objective: Objective
    status: InitiativeStatus


class InitiativeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    objective: str
    status: InitiativeStatus
    version: int
    created_at: datetime
    updated_at: datetime


class ProjectCreate(BaseModel):
    name: Name
    repository: RepositoryReference = None
    status: ProjectStatus = ProjectStatus.PLANNED


class ProjectUpdate(BaseModel):
    expected_version: ExpectedVersion
    name: Name
    repository: RepositoryReference = None
    status: ProjectStatus


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    initiative_id: uuid.UUID
    name: str
    repository: str | None
    status: ProjectStatus
    version: int
    created_at: datetime
    updated_at: datetime


class BudgetCreate(BaseModel):
    monthly_limit: MonthlyLimit
    currency: Currency = "USD"
    enforcement_mode: BudgetEnforcementMode = BudgetEnforcementMode.WARN


class BudgetUpdate(BaseModel):
    expected_version: ExpectedVersion
    monthly_limit: MonthlyLimit
    currency: Currency
    enforcement_mode: BudgetEnforcementMode


class BudgetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    monthly_limit: Decimal
    currency: str
    enforcement_mode: BudgetEnforcementMode
    version: int
    created_at: datetime
    updated_at: datetime
