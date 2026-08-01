from __future__ import annotations

import json
import os
import shlex
from collections.abc import Callable
from pathlib import Path

from devsembly.contracts import TaskPacket, ValidationEvidence
from devsembly.model_gateway import ModelGatewayTokenCodec
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
    def _provider_environment(task: TaskPacket) -> tuple[dict[str, str], str, str | None]:
        environment = {
            "HOME": "/tmp",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PATH": "/usr/local/bin:/usr/bin:/bin:/app/node_modules/.bin",
        }
        gateway_values = {
            "url": os.getenv("DEVSEMBLY_MODEL_GATEWAY_URL", ""),
            "network": os.getenv("DEVSEMBLY_SANDBOX_NETWORK", ""),
            "secret": os.getenv("DEVSEMBLY_MODEL_GATEWAY_SECRET", ""),
        }
        configured = [bool(value) for value in gateway_values.values()]
        if any(configured) and not all(configured):
            raise RuntimeError("Model gateway configuration is incomplete")
        if all(configured):
            environment.update(
                {
                    "ANTHROPIC_BASE_URL": gateway_values["url"],
                    "ANTHROPIC_AUTH_TOKEN": ModelGatewayTokenCodec(gateway_values["secret"]).issue(
                        str(task.run_id)
                    ),
                }
            )
            return environment, "model-gateway-only", gateway_values["network"]
        return environment, "deny-all", None

    async def _execute(
        self,
        payload: dict[str, object],
        workspace: Path,
        task: TaskPacket,
    ) -> BuildResult:
        if not self.command:
            raise RuntimeError("DEVSEMBLY_CODING_PROVIDER_COMMAND is not configured")
        arguments = shlex.split(self.command)
        if not arguments:
            raise RuntimeError("DEVSEMBLY_CODING_PROVIDER_COMMAND must be an argument vector")
        if self.heartbeat is not None:
            self.heartbeat(f"coding-provider:{payload.get('action', 'unknown')}")
        environment, network_policy, network_name = self._provider_environment(task)
        result = await self.sandbox.execute(
            SandboxRequest(
                command=arguments,
                workspace=workspace,
                stdin=json.dumps(payload).encode(),
                environment=environment,
                limits=SandboxLimits(timeout_seconds=self.timeout_seconds),
                purpose="coding",
                network_policy=network_policy,
                network_name=network_name,
            )
        )
        if result.metadata.exit_code != 0:
            raise SandboxError(
                "Coding provider failed inside sandbox: "
                f"{result.stderr.decode(errors='replace')[-4000:]}",
                result.metadata,
            )
        paths = await changed_paths(workspace)
        enforce_allowed_paths(paths, task.allowed_paths)
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
            task,
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
            task,
        )
