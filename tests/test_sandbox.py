from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path

import pytest

from devsembly.sandbox import (
    DockerExecutionSandbox,
    SandboxLimits,
    SandboxRequest,
    SandboxUnavailableError,
)


def test_docker_boundary_is_non_root_deny_all_and_resource_bounded(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    runner = DockerExecutionSandbox(image="sandbox@sha256:fixture")
    limits = SandboxLimits(
        cpus=0.5,
        memory_bytes=268_435_456,
        pids=32,
        storage_bytes=33_554_432,
        output_bytes=4096,
        timeout_seconds=30,
    )
    request = SandboxRequest(
        command=["python", "-c", "print('ok')"], workspace=tmp_path, limits=limits
    )

    arguments = runner.create_arguments(request, "devsembly-sandbox-fixture", tmp_path.resolve())

    assert arguments[arguments.index("--user") + 1] == "65532:65532"
    assert arguments[arguments.index("--network") + 1] == "none"
    assert arguments[arguments.index("--cap-drop") + 1] == "ALL"
    assert arguments[arguments.index("--security-opt") + 1] == "no-new-privileges:true"
    assert "--read-only" in arguments
    assert arguments[arguments.index("--cpus") + 1] == "0.5"
    assert arguments[arguments.index("--memory") + 1] == "268435456"
    assert arguments[arguments.index("--pids-limit") + 1] == "32"
    assert str(tmp_path.resolve()) in arguments[arguments.index("--mount") + 1]
    mounts = [arguments[index + 1] for index, item in enumerate(arguments) if item == "--mount"]
    assert any("target=/workspace/.git,readonly" in mount for mount in mounts)
    assert "/var/run/docker.sock" not in " ".join(arguments)


def test_command_is_preserved_as_an_argument_vector(tmp_path: Path) -> None:
    runner = DockerExecutionSandbox(image="fixture")
    command = ["python", "-c", "print('safe')", "&&", "touch", "escaped"]
    arguments = runner.create_arguments(
        SandboxRequest(command=command, workspace=tmp_path),
        "devsembly-sandbox-fixture",
        tmp_path.resolve(),
    )

    assert arguments[-len(command) :] == command


@pytest.mark.asyncio
async def test_secret_environment_is_rejected_before_runtime_use(tmp_path: Path) -> None:
    request = SandboxRequest(
        command=["true"], workspace=tmp_path, environment={"GITHUB_TOKEN": "secret"}
    )

    with pytest.raises(ValueError, match="forbidden secret"):
        await DockerExecutionSandbox().execute(request)


@pytest.mark.asyncio
async def test_provider_api_key_is_rejected_even_for_gateway_policy(tmp_path: Path) -> None:
    request = SandboxRequest(
        command=["true"],
        workspace=tmp_path,
        purpose="coding",
        network_policy="model-gateway-only",
        network_name="devsembly-sandbox-egress",
        environment={
            "HOME": "/tmp",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PATH": "/usr/bin:/bin",
            "ANTHROPIC_BASE_URL": "http://model-gateway:8080",
            "ANTHROPIC_AUTH_TOKEN": "task-token",
            "ANTHROPIC_API_KEY": "provider-secret",
        },
    )

    with pytest.raises(ValueError, match="forbidden secret"):
        await DockerExecutionSandbox().execute(request)


def test_gateway_policy_selects_only_the_configured_network(tmp_path: Path) -> None:
    runner = DockerExecutionSandbox(image="fixture")
    request = SandboxRequest(
        command=["true"],
        workspace=tmp_path,
        purpose="coding",
        network_policy="model-gateway-only",
        network_name="devsembly-sandbox-egress",
        environment={
            "HOME": "/tmp",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PATH": "/usr/bin:/bin",
            "ANTHROPIC_BASE_URL": "http://model-gateway:8080",
            "ANTHROPIC_AUTH_TOKEN": "task-token",
        },
    )

    arguments = runner.create_arguments(request, "devsembly-sandbox-fixture", tmp_path.resolve())

    assert arguments[arguments.index("--network") + 1] == "devsembly-sandbox-egress"


@pytest.mark.asyncio
async def test_gateway_policy_fails_closed_when_network_is_not_internal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = DockerExecutionSandbox(image="fixture")

    async def invoke(*arguments: str, stdin: bytes = b"") -> tuple[int, bytes, bytes]:
        del stdin
        if "image" in arguments:
            return 0, b"sha256:fixture\n", b""
        if "network" in arguments:
            return 0, b"false\n", b""
        return 0, b"", b""

    monkeypatch.setattr(runner, "_invoke", invoke)
    request = SandboxRequest(
        command=["true"],
        workspace=tmp_path,
        purpose="coding",
        network_policy="model-gateway-only",
        network_name="devsembly-sandbox-egress",
        environment={
            "HOME": "/tmp",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PATH": "/usr/bin:/bin",
            "ANTHROPIC_BASE_URL": "http://model-gateway:8080",
            "ANTHROPIC_AUTH_TOKEN": "task-token",
        },
    )

    with pytest.raises(SandboxUnavailableError, match="not Docker-internal") as raised:
        await runner.execute(request)

    assert raised.value.metadata.termination_reason == "network-policy-unavailable"


@pytest.mark.asyncio
async def test_symlink_escape_is_rejected_before_runtime_use(tmp_path: Path) -> None:
    (tmp_path / "escape").symlink_to("/etc/passwd")

    with pytest.raises(ValueError, match="escaping symlink"):
        await DockerExecutionSandbox().execute(SandboxRequest(command=["true"], workspace=tmp_path))


@pytest.mark.asyncio
async def test_runtime_unavailable_fails_closed_with_auditable_metadata(tmp_path: Path) -> None:
    runner = DockerExecutionSandbox(docker_command="definitely-not-a-runtime")

    with pytest.raises(SandboxUnavailableError) as raised:
        await runner.execute(SandboxRequest(command=["true"], workspace=tmp_path))

    assert raised.value.metadata.termination_reason == "runtime-unavailable"
    assert raised.value.metadata.cleanup_succeeded is True
    assert raised.value.metadata.finished_at is not None


@pytest.mark.asyncio
async def test_cancellation_requests_container_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runner = DockerExecutionSandbox(image="fixture")
    calls: list[tuple[str, ...]] = []
    gate = asyncio.Event()

    async def invoke(*arguments: str, stdin: bytes = b"") -> tuple[int, bytes, bytes]:
        del stdin
        calls.append(arguments)
        if "inspect" in arguments:
            return 0, b"sha256:fixture\n", b""
        if "create" in arguments:
            return 0, b"container\n", b""
        return 0, b"", b""

    async def start_attached(
        container_name: str, request: SandboxRequest, workspace: Path
    ) -> tuple[int, bytes, bytes, str]:
        del container_name, request, workspace
        await gate.wait()
        return 0, b"", b"", "completed"

    monkeypatch.setattr(runner, "_invoke", invoke)
    monkeypatch.setattr(runner, "_start_attached", start_attached)
    task = asyncio.create_task(runner.execute(SandboxRequest(command=["true"], workspace=tmp_path)))
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert any("rm" in call and "--force" in call for call in calls)


@pytest.mark.asyncio
async def test_cleanup_occurs_after_success_and_command_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for exit_code in (0, 7):
        runner = DockerExecutionSandbox(image="fixture")
        calls: list[tuple[str, ...]] = []

        async def invoke(
            *arguments: str, stdin: bytes = b"", calls: list[tuple[str, ...]] = calls
        ) -> tuple[int, bytes, bytes]:
            del stdin
            calls.append(arguments)
            if "inspect" in arguments:
                return 0, b"sha256:fixture\n", b""
            return 0, b"", b""

        async def start_attached(
            container_name: str,
            request: SandboxRequest,
            workspace: Path,
            exit_code: int = exit_code,
        ) -> tuple[int, bytes, bytes, str]:
            del container_name, request, workspace
            return exit_code, b"output", b"error", "completed"

        monkeypatch.setattr(runner, "_invoke", invoke)
        monkeypatch.setattr(runner, "_start_attached", start_attached)
        result = await runner.execute(SandboxRequest(command=["true"], workspace=tmp_path))

        assert result.metadata.exit_code == exit_code
        assert result.metadata.cleanup_succeeded is True
        assert any("rm" in call and "--force" in call for call in calls)


@pytest.mark.asyncio
async def test_worker_restart_cleanup_removes_labelled_orphans(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = DockerExecutionSandbox(image="fixture")
    removed: list[str] = []

    async def invoke(*arguments: str, stdin: bytes = b"") -> tuple[int, bytes, bytes]:
        del stdin
        assert "label=devsembly.sandbox=true" in arguments
        return 0, b"orphan-one\norphan-two\n", b""

    async def remove(name: str) -> bool:
        removed.append(name)
        return True

    monkeypatch.setattr(runner, "_invoke", invoke)
    monkeypatch.setattr(runner, "_remove", remove)

    assert await runner.cleanup_stale() is True
    assert removed == ["orphan-one", "orphan-two"]


def _docker_image_available(image: str) -> bool:
    if shutil.which("docker") is None:
        return False
    return (
        subprocess.run(
            ["docker", "image", "inspect", image],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )


@pytest.mark.asyncio
@pytest.mark.skipif(
    not _docker_image_available("devsembly-sandbox:latest"),
    reason="Docker runtime or local devsembly-sandbox:latest image unavailable",
)
async def test_docker_integration_enforces_identity_network_and_cleanup(tmp_path: Path) -> None:
    tmp_path.chmod(0o777)
    runner = DockerExecutionSandbox(image="devsembly-sandbox:latest")
    request = SandboxRequest(
        command=[
            "python",
            "-c",
            (
                "import os,socket; print(os.getuid()); "
                "open('/workspace/writable', 'w').write('ok'); "
                "assert socket.socket().connect_ex(('1.1.1.1', 443)) != 0; "
                "print('network-denied')"
            ),
        ],
        workspace=tmp_path,
        limits=SandboxLimits(timeout_seconds=10),
    )

    result = await runner.execute(request)

    assert result.metadata.exit_code == 0, result.stderr.decode(errors="replace")
    assert result.stdout.splitlines()[0] == b"65532"
    assert (tmp_path / "writable").read_text() == "ok"
    assert result.metadata.network_policy == "deny-all"
    assert result.metadata.cleanup_succeeded is True
