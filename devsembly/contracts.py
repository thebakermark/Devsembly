from __future__ import annotations

from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl


class RunStatus(StrEnum):
    QUEUED = "queued"
    PLANNING = "planning"
    CHECKING_OUT = "checking_out"
    BUILDING = "building"
    VALIDATING = "validating"
    REPAIRING = "repairing"
    PUBLISHING = "publishing"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    ESCALATED = "escalated"


class ProductRequest(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    objective: str = Field(min_length=10, max_length=20_000)
    repository_url: HttpUrl
    base_branch: str = "main"
    allowed_paths: list[str] = Field(default_factory=lambda: ["src/", "tests/", "docs/"])
    validation_commands: list[str] = Field(default_factory=lambda: ["pytest -q"])
    max_repair_attempts: int = Field(default=2, ge=0, le=5)


class TaskPacket(BaseModel):
    run_id: UUID
    title: str
    objective: str
    repository_url: HttpUrl
    base_branch: str
    branch_name: str
    allowed_paths: list[str]
    acceptance_criteria: list[str]
    validation_commands: list[str]
    max_repair_attempts: int


class ValidationEvidence(BaseModel):
    command: str
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    attempt: int = 0


class FactoryRun(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    status: RunStatus = RunStatus.QUEUED
    request: ProductRequest
    task_packet: TaskPacket | None = None
    evidence: list[ValidationEvidence] = Field(default_factory=list)
    changed_paths: list[str] = Field(default_factory=list)
    repair_attempts: int = 0
    change_request_url: str | None = None
    summary: str | None = None
