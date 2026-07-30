from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from devsembly.contracts import TaskPacket, ValidationEvidence
from devsembly.providers import BuildResult
from devsembly.workspace import changed_paths, enforce_allowed_paths


class CommandCodingProvider:
    """Runs a configured provider command inside the isolated workspace.

    The command receives a JSON task packet on stdin and must edit files only inside
    the workspace. Credentials and provider-specific setup stay outside the core.
    """

    def __init__(self, command: str | None = None) -> None:
        self.command = command or os.getenv("DEVSEMBLY_CODING_PROVIDER_COMMAND", "")

    async def _execute(
        self,
        payload: dict[str, object],
        workspace: Path,
        allowed_paths: list[str],
    ) -> BuildResult:
        if not self.command:
            raise RuntimeError("DEVSEMBLY_CODING_PROVIDER_COMMAND is not configured")
        process = await asyncio.create_subprocess_shell(
            self.command,
            cwd=workspace,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate(json.dumps(payload).encode())
        if process.returncode != 0:
            raise RuntimeError(f"Coding provider failed: {stderr.decode(errors='replace')[-4000:]}")
        paths = await changed_paths(workspace)
        enforce_allowed_paths(paths, allowed_paths)
        summary = stdout.decode(errors="replace").strip()[-4000:] or "Provider completed."
        return BuildResult(summary=summary, changed_paths=paths)

    async def build(self, task: TaskPacket, workspace: Path) -> BuildResult:
        return await self._execute(
            {
                "action": "build",
                "objective": task.objective,
                "acceptance_criteria": task.acceptance_criteria,
                "allowed_paths": task.allowed_paths,
                "validation_commands": task.validation_commands,
            },
            workspace,
            task.allowed_paths,
        )

    async def repair(
        self,
        task: TaskPacket,
        workspace: Path,
        evidence: list[ValidationEvidence],
        attempt: int,
    ) -> BuildResult:
        return await self._execute(
            {
                "action": "repair",
                "attempt": attempt,
                "objective": task.objective,
                "acceptance_criteria": task.acceptance_criteria,
                "allowed_paths": task.allowed_paths,
                "validation_commands": task.validation_commands,
                "evidence": [item.model_dump(mode="json") for item in evidence],
            },
            workspace,
            task.allowed_paths,
        )
