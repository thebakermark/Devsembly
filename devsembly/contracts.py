from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import PurePosixPath
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl, field_validator


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


class ProjectContext(BaseModel):
    """Canonical Genesis scope used to retain the outcome in MemoryOS."""

    organization_id: UUID
    initiative_id: UUID
    project_id: UUID


class ProductRequest(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    objective: str = Field(min_length=10, max_length=20_000)
    repository_url: HttpUrl
    base_branch: str = Field(default="main", pattern=r"^[A-Za-z0-9._/][A-Za-z0-9._/-]*$")
    allowed_paths: list[str] = Field(
        default_factory=lambda: ["src/", "tests/", "docs/"], min_length=1
    )
    validation_commands: list[str] = Field(default_factory=lambda: ["pytest -q"], min_length=1)
    max_repair_attempts: int = Field(default=2, ge=0, le=5)
    project_context: ProjectContext | None = None

    @field_validator("allowed_paths")
    @classmethod
    def validate_allowed_paths(cls, paths: list[str]) -> list[str]:
        for path in paths:
            parts = PurePosixPath(path).parts
            if not path or PurePosixPath(path).is_absolute() or ".." in parts:
                raise ValueError("allowed paths must be non-empty repository-relative paths")
        return paths


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
    sandbox_execution: SandboxExecutionMetadata | None = None


class SandboxExecutionMetadata(BaseModel):
    execution_id: UUID
    runtime: str
    image: str
    image_identifier: str | None = None
    command: list[str]
    purpose: str = "validation"
    user: str
    workspace_mode: str = "task-specific-rw"
    root_filesystem_read_only: bool = True
    network_policy: str = "deny-all"
    cpu_limit: float
    memory_limit_bytes: int
    pid_limit: int
    storage_limit_bytes: int
    output_limit_bytes: int
    timeout_seconds: float
    started_at: datetime
    finished_at: datetime | None = None
    exit_code: int | None = None
    termination_reason: str | None = None
    cleanup_succeeded: bool | None = None


class FactoryRun(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    status: RunStatus = RunStatus.QUEUED
    request: ProductRequest
    task_packet: TaskPacket | None = None
    evidence: list[ValidationEvidence] = Field(default_factory=list)
    changed_paths: list[str] = Field(default_factory=list)
    repair_attempts: int = 0
    work_item_url: str | None = None
    change_request_url: str | None = None
    memory_proposal_id: UUID | None = None
    summary: str | None = None
    sandbox_executions: list[SandboxExecutionMetadata] = Field(default_factory=list)
