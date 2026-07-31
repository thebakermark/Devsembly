from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from devsembly.contracts import TaskPacket, ValidationEvidence


@dataclass(frozen=True)
class BuildResult:
    summary: str
    changed_paths: list[str]


class AICodingProvider(Protocol):
    async def build(self, task: TaskPacket, workspace: Path) -> BuildResult: ...

    async def repair(
        self,
        task: TaskPacket,
        workspace: Path,
        evidence: list[ValidationEvidence],
        attempt: int,
    ) -> BuildResult: ...


class SourceControlProvider(Protocol):
    async def ensure_work_item(
        self,
        task: TaskPacket,
        workspace: Path,
        title: str,
        body: str,
    ) -> str: ...

    async def publish_draft_change_request(
        self,
        task: TaskPacket,
        workspace: Path,
        title: str,
        body: str,
    ) -> str: ...


class NoopCodingProvider:
    """Safe default until an executable AI coding provider is configured."""

    async def build(self, task: TaskPacket, workspace: Path) -> BuildResult:
        return BuildResult("No executable AI coding provider is configured.", [])

    async def repair(
        self,
        task: TaskPacket,
        workspace: Path,
        evidence: list[ValidationEvidence],
        attempt: int,
    ) -> BuildResult:
        return BuildResult(f"Repair attempt {attempt} skipped; no provider is configured.", [])
