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
class OutboxMessage:
    id: uuid.UUID
    occurred_at: datetime
    topic: str
    aggregate_id: str
    payload: dict[str, object]
