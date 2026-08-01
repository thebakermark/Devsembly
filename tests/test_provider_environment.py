from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

import devsembly.provider_command as provider_module
from devsembly.contracts import SandboxExecutionMetadata, TaskPacket
from devsembly.provider_command import CommandCodingProvider
from devsembly.sandbox import SandboxRequest, SandboxResult


def _task() -> TaskPacket:
    return TaskPacket(
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


def test_provider_environment_excludes_source_control_token(monkeypatch) -> None:
    for name in (
        "DEVSEMBLY_MODEL_GATEWAY_URL",
        "DEVSEMBLY_SANDBOX_NETWORK",
        "DEVSEMBLY_MODEL_GATEWAY_SECRET",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-secret")
    monkeypatch.setenv("DEVSEMBLY_SOURCE_CONTROL_TOKEN", "source-control-secret")
    monkeypatch.setenv("UNRELATED_SECRET", "unrelated-secret")

    environment, policy, network = CommandCodingProvider._provider_environment(_task())

    assert "ANTHROPIC_API_KEY" not in environment
    assert "DEVSEMBLY_SOURCE_CONTROL_TOKEN" not in environment
    assert "UNRELATED_SECRET" not in environment
    assert policy == "deny-all"
    assert network is None


def test_provider_uses_only_short_lived_gateway_access(monkeypatch) -> None:
    secret = "gateway-signing-secret-that-is-at-least-32-bytes"
    monkeypatch.setenv("DEVSEMBLY_MODEL_GATEWAY_URL", "http://model-gateway:8080")
    monkeypatch.setenv("DEVSEMBLY_SANDBOX_NETWORK", "devsembly-sandbox-egress")
    monkeypatch.setenv("DEVSEMBLY_MODEL_GATEWAY_SECRET", secret)
    monkeypatch.setenv("DEVSEMBLY_MODEL_PROVIDER_API_KEY", "real-provider-key")

    task = _task()
    environment, policy, network = CommandCodingProvider._provider_environment(task)

    assert environment["ANTHROPIC_BASE_URL"] == "http://model-gateway:8080"
    assert environment["ANTHROPIC_AUTH_TOKEN"] != secret
    assert "DEVSEMBLY_MODEL_PROVIDER_API_KEY" not in environment
    assert policy == "model-gateway-only"
    assert network == "devsembly-sandbox-egress"


def test_partial_gateway_configuration_fails_closed(monkeypatch) -> None:
    monkeypatch.delenv("DEVSEMBLY_SANDBOX_NETWORK", raising=False)
    monkeypatch.delenv("DEVSEMBLY_MODEL_GATEWAY_SECRET", raising=False)
    monkeypatch.setenv("DEVSEMBLY_MODEL_GATEWAY_URL", "http://model-gateway:8080")

    with pytest.raises(RuntimeError, match="incomplete"):
        CommandCodingProvider._provider_environment(_task())


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
    task = _task()
    provider = CommandCodingProvider("provider --literal '; touch escaped'", sandbox=Sandbox())

    result = await provider.build(task, tmp_path)

    assert result.summary == "done"
    assert len(requests) == 1
    assert requests[0].command == ["provider", "--literal", "; touch escaped"]
    assert requests[0].purpose == "coding"
