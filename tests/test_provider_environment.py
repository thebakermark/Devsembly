from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

import devsembly.provider_command as provider_module
from devsembly.contracts import SandboxExecutionMetadata, TaskPacket
from devsembly.provider_command import CommandCodingProvider
from devsembly.sandbox import SandboxRequest, SandboxResult


def test_provider_environment_excludes_source_control_token(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-secret")
    monkeypatch.setenv("DEVSEMBLY_SOURCE_CONTROL_TOKEN", "source-control-secret")
    monkeypatch.setenv("UNRELATED_SECRET", "unrelated-secret")

    environment = CommandCodingProvider._provider_environment()

    assert "ANTHROPIC_API_KEY" not in environment
    assert "DEVSEMBLY_SOURCE_CONTROL_TOKEN" not in environment
    assert "UNRELATED_SECRET" not in environment


@pytest.mark.asyncio
async def test_provider_cannot_request_host_execution(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    requests: list[SandboxRequest] = []

    class Sandbox:
        async def execute(self, request: SandboxRequest) -> SandboxResult:
            requests.append(request)
            now = datetime.now(UTC)
            metadata = SandboxExecutionMetadata(
                execution_id=uuid.uuid4(),
                runtime="test",
                image="fixture",
                command=request.command,
                purpose=request.purpose,
                user="65532:65532",
                cpu_limit=1,
                memory_limit_bytes=1024,
                pid_limit=8,
                storage_limit_bytes=1024,
                output_limit_bytes=1024,
                timeout_seconds=10,
                started_at=now,
                finished_at=now,
                exit_code=0,
                termination_reason="completed",
                cleanup_succeeded=True,
            )
            return SandboxResult(stdout=b"done", stderr=b"", metadata=metadata)

    async def paths(root: Path) -> list[str]:
        del root
        return ["src/result.py"]

    monkeypatch.setattr(provider_module, "changed_paths", paths)
    task = TaskPacket(
        run_id=uuid.uuid4(),
        title="Fixture",
        objective="Exercise the sandbox provider boundary.",
        repository_url="https://github.com/example/fixture",
        base_branch="main",
        branch_name="factory/fixture",
        allowed_paths=["src"],
        acceptance_criteria=["Sandbox used"],
        validation_commands=["pytest -q"],
        max_repair_attempts=0,
    )
    provider = CommandCodingProvider("provider --literal '; touch escaped'", sandbox=Sandbox())

    result = await provider.build(task, tmp_path)

    assert result.summary == "done"
    assert len(requests) == 1
    assert requests[0].command == ["provider", "--literal", "; touch escaped"]
    assert requests[0].purpose == "coding"
