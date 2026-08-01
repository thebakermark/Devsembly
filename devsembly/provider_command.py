from __future__ import annotations

import json
import os
import shlex
from collections.abc import Callable
from pathlib import Path

from devsembly.contracts import TaskPacket, ValidationEvidence
from devsembly.providers import BuildResult
from devsembly.sandbox import (
    DockerExecutionSandbox,
    ExecutionSandbox,
    SandboxError,
    SandboxLimits,
    SandboxRequest,
)
from devsembly.workspace import changed_paths, enforce_allowed_paths


class CommandCodingProvider:
    """Runs a configured provider command inside the isolated workspace.

    The command receives a JSON task packet on stdin and must edit files only inside
    the workspace. Only an explicit environment allowlist is inherited, preventing
    source-control and infrastructure credentials from reaching the coding provider.
    """

    def __init__(
        self,
        command: str | None = None,
        *,
        heartbeat: Callable[[str], None] | None = None,
        timeout_seconds: float = 1_800,
        sandbox: ExecutionSandbox | None = None,
    ) -> None:
        self.command = command or os.getenv("DEVSEMBLY_CODING_PROVIDER_COMMAND", "")
        self.heartbeat = heartbeat
        self.timeout_seconds = timeout_seconds
        self.sandbox = sandbox or DockerExecutionSandbox()

    @staticmethod
    def _provider_environment() -> dict[str, str]:
        return {
            "HOME": "/tmp",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PATH": "/usr/local/bin:/usr/bin:/bin:/app/node_modules/.bin",
        }

    async def _execute(
        self,
        payload: dict[str, object],
        workspace: Path,
        allowed_paths: list[str],
    ) -> BuildResult:
        if not self.command:
            raise RuntimeError("DEVSEMBLY_CODING_PROVIDER_COMMAND is not configured")
        arguments = shlex.split(self.command)
        if not arguments:
            raise RuntimeError("DEVSEMBLY_CODING_PROVIDER_COMMAND must be an argument vector")
        if self.heartbeat is not None:
            self.heartbeat(f"coding-provider:{payload.get('action', 'unknown')}")
        result = await self.sandbox.execute(
            SandboxRequest(
                command=arguments,
                workspace=workspace,
                stdin=json.dumps(payload).encode(),
                environment=self._provider_environment(),
                limits=SandboxLimits(timeout_seconds=self.timeout_seconds),
                purpose="coding",
            )
        )
        if result.metadata.exit_code != 0:
            raise SandboxError(
                "Coding provider failed inside sandbox: "
                f"{result.stderr.decode(errors='replace')[-4000:]}",
                result.metadata,
            )
        paths = await changed_paths(workspace)
        enforce_allowed_paths(paths, allowed_paths)
        summary = result.stdout.decode(errors="replace").strip()[-4000:] or "Provider completed."
        return BuildResult(summary=summary, changed_paths=paths, sandbox_execution=result.metadata)

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
