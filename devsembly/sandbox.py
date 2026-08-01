from __future__ import annotations

import asyncio
import contextlib
import os
import stat
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from devsembly.contracts import SandboxExecutionMetadata


class SandboxError(RuntimeError):
    def __init__(self, message: str, metadata: SandboxExecutionMetadata) -> None:
        super().__init__(message)
        self.metadata = metadata


class SandboxUnavailableError(SandboxError):
    pass


@dataclass(frozen=True)
class SandboxLimits:
    cpus: float = 1.0
    memory_bytes: int = 1_073_741_824
    pids: int = 128
    storage_bytes: int = 1_073_741_824
    output_bytes: int = 1_048_576
    timeout_seconds: float = 600.0


@dataclass(frozen=True)
class SandboxRequest:
    command: list[str]
    workspace: Path
    stdin: bytes = b""
    environment: dict[str, str] = field(default_factory=dict)
    limits: SandboxLimits = field(default_factory=SandboxLimits)
    purpose: str = "validation"


@dataclass(frozen=True)
class SandboxResult:
    stdout: bytes
    stderr: bytes
    metadata: SandboxExecutionMetadata


class ExecutionSandbox(Protocol):
    async def execute(self, request: SandboxRequest) -> SandboxResult: ...


_SENSITIVE_ENV_FRAGMENTS = (
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "CREDENTIAL",
    "DATABASE_URL",
    "AWS_",
    "AZURE_",
    "GOOGLE_",
    "GITHUB_",
    "OIDC",
)


def _validate_workspace(workspace: Path) -> Path:
    root = workspace.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("Sandbox workspace must be a directory")
    for path in root.rglob("*"):
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            target = path.resolve(strict=False)
            if not target.is_relative_to(root):
                raise ValueError(
                    f"Sandbox workspace contains escaping symlink: {path.relative_to(root)}"
                )
        elif not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
            raise ValueError(
                f"Sandbox workspace contains unsupported file type: {path.relative_to(root)}"
            )
    return root


def _workspace_size(root: Path) -> int:
    return sum(
        path.stat(follow_symlinks=False).st_size for path in root.rglob("*") if path.is_file()
    )


def _validate_environment(environment: dict[str, str]) -> None:
    rejected = [
        name
        for name in environment
        if any(fragment in name.upper() for fragment in _SENSITIVE_ENV_FRAGMENTS)
    ]
    if rejected:
        raise ValueError(f"Sandbox environment contains forbidden secret names: {sorted(rejected)}")


class DockerExecutionSandbox:
    """Run untrusted commands in short-lived, deny-by-default Docker containers."""

    def __init__(
        self,
        *,
        image: str | None = None,
        docker_command: str = "docker",
        sandbox_uid: int = 65532,
        sandbox_gid: int = 65532,
    ) -> None:
        self.image = image or os.getenv("DEVSEMBLY_SANDBOX_IMAGE") or "devsembly-sandbox:latest"
        self.docker_command = docker_command
        self.sandbox_uid = sandbox_uid
        self.sandbox_gid = sandbox_gid

    def create_arguments(
        self, request: SandboxRequest, container_name: str, workspace: Path
    ) -> list[str]:
        limits = request.limits
        arguments = [
            self.docker_command,
            "create",
            "--name",
            container_name,
            "--label",
            "devsembly.sandbox=true",
            "--label",
            f"devsembly.execution_id={container_name.removeprefix('devsembly-sandbox-')}",
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges:true",
            "--user",
            f"{self.sandbox_uid}:{self.sandbox_gid}",
            "--cpus",
            str(limits.cpus),
            "--memory",
            str(limits.memory_bytes),
            "--memory-swap",
            str(limits.memory_bytes),
            "--pids-limit",
            str(limits.pids),
            "--ulimit",
            f"fsize={limits.storage_bytes}:{limits.storage_bytes}",
            "--tmpfs",
            f"/tmp:rw,nosuid,nodev,noexec,size={min(limits.storage_bytes, 268_435_456)}",
            "--mount",
            f"type=bind,source={workspace},target=/workspace,rw",
        ]
        git_metadata = workspace / ".git"
        if git_metadata.exists():
            arguments.extend(
                [
                    "--mount",
                    f"type=bind,source={git_metadata},target=/workspace/.git,readonly",
                ]
            )
        arguments.extend(["--workdir", "/workspace"])
        for name, value in sorted(request.environment.items()):
            arguments.extend(["--env", f"{name}={value}"])
        arguments.extend([self.image, *request.command])
        return arguments

    async def _invoke(self, *arguments: str, stdin: bytes = b"") -> tuple[int, bytes, bytes]:
        try:
            process = await asyncio.create_subprocess_exec(
                *arguments,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"Sandbox runtime executable is unavailable: {arguments[0]}"
            ) from exc
        stdout, stderr = await process.communicate(stdin)
        return process.returncode or 0, stdout, stderr

    async def _remove(self, container_name: str) -> bool:
        code, _, stderr = await self._invoke(self.docker_command, "rm", "--force", container_name)
        return code == 0 or b"No such container" in stderr

    async def cleanup_stale(self) -> bool:
        """Remove sandbox containers left by an interrupted single-worker runtime."""
        try:
            code, stdout, _ = await self._invoke(
                self.docker_command,
                "ps",
                "--all",
                "--quiet",
                "--filter",
                "label=devsembly.sandbox=true",
            )
        except RuntimeError:
            return False
        if code != 0:
            return False
        names = [item for item in stdout.decode().splitlines() if item]
        return all([await self._remove(name) for name in names])

    async def _image_identifier(self) -> str | None:
        try:
            code, stdout, _ = await self._invoke(
                self.docker_command, "image", "inspect", "--format", "{{.Id}}", self.image
            )
        except RuntimeError:
            return None
        return stdout.decode(errors="replace").strip() if code == 0 else None

    async def _start_attached(
        self, container_name: str, request: SandboxRequest, workspace: Path
    ) -> tuple[int, bytes, bytes, str]:
        process = await asyncio.create_subprocess_exec(
            self.docker_command,
            "start",
            "--attach",
            "--interactive",
            container_name,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        assert process.stdin is not None
        assert process.stdout is not None
        assert process.stderr is not None
        process.stdin.write(request.stdin)
        await process.stdin.drain()
        process.stdin.close()

        output = bytearray()
        errors = bytearray()
        output_limit_reached = asyncio.Event()
        total = 0

        async def read_bounded(reader: asyncio.StreamReader, target: bytearray) -> None:
            nonlocal total
            while chunk := await reader.read(65_536):
                remaining = max(0, request.limits.output_bytes - total)
                target.extend(chunk[:remaining])
                total += len(chunk)
                if total > request.limits.output_bytes:
                    output_limit_reached.set()
                    return

        readers = [
            asyncio.create_task(read_bounded(process.stdout, output)),
            asyncio.create_task(read_bounded(process.stderr, errors)),
        ]
        wait = asyncio.create_task(process.wait())
        deadline = asyncio.get_running_loop().time() + request.limits.timeout_seconds
        reason = "completed"
        try:
            while not wait.done():
                if output_limit_reached.is_set():
                    reason = "output-limit"
                    await self._remove(container_name)
                    break
                if _workspace_size(workspace) > request.limits.storage_bytes:
                    reason = "storage-limit"
                    await self._remove(container_name)
                    break
                if asyncio.get_running_loop().time() >= deadline:
                    reason = "timeout"
                    await self._remove(container_name)
                    break
                await asyncio.sleep(0.05)
            try:
                await asyncio.wait_for(wait, timeout=5)
            except TimeoutError:
                reason = "termination-failure"
                wait.cancel()
                await asyncio.gather(wait, return_exceptions=True)
            await asyncio.gather(*readers, return_exceptions=True)
        except asyncio.CancelledError:
            await self._remove(container_name)
            wait.cancel()
            for reader in readers:
                reader.cancel()
            await asyncio.gather(wait, *readers, return_exceptions=True)
            raise
        exit_code = process.returncode or 0
        if reason == "timeout":
            exit_code = 124
        elif reason in {"output-limit", "storage-limit", "termination-failure"}:
            exit_code = 125
        return exit_code, bytes(output), bytes(errors), reason

    async def execute(self, request: SandboxRequest) -> SandboxResult:
        if not request.command or not all(request.command):
            raise ValueError("Sandbox command must be a non-empty argument vector")
        _validate_environment(request.environment)
        workspace = _validate_workspace(request.workspace)
        if _workspace_size(workspace) > request.limits.storage_bytes:
            raise ValueError("Sandbox workspace exceeds its storage limit before execution")

        execution_id = uuid.uuid4()
        container_name = f"devsembly-sandbox-{execution_id}"
        metadata = SandboxExecutionMetadata(
            execution_id=execution_id,
            runtime="docker",
            image=self.image,
            image_identifier=await self._image_identifier(),
            command=request.command,
            purpose=request.purpose,
            user=f"{self.sandbox_uid}:{self.sandbox_gid}",
            cpu_limit=request.limits.cpus,
            memory_limit_bytes=request.limits.memory_bytes,
            pid_limit=request.limits.pids,
            storage_limit_bytes=request.limits.storage_bytes,
            output_limit_bytes=request.limits.output_bytes,
            timeout_seconds=request.limits.timeout_seconds,
            started_at=datetime.now(UTC),
        )
        cleanup_succeeded = False
        created = False
        try:
            create = self.create_arguments(request, container_name, workspace)
            try:
                code, _, stderr = await self._invoke(*create)
            except RuntimeError as exc:
                metadata.termination_reason = "runtime-unavailable"
                raise SandboxUnavailableError(str(exc), metadata) from exc
            if code != 0:
                metadata.termination_reason = "startup-failure"
                raise SandboxUnavailableError(
                    f"Sandbox container could not start: {stderr.decode(errors='replace')[-2000:]}",
                    metadata,
                )
            created = True
            try:
                code, stdout, stderr, reason = await self._start_attached(
                    container_name, request, workspace
                )
            except OSError as exc:
                metadata.termination_reason = "runtime-unavailable"
                raise SandboxUnavailableError(str(exc), metadata) from exc
            metadata.termination_reason = reason
            metadata.exit_code = code
            try:
                _validate_workspace(workspace)
            except ValueError as exc:
                metadata.exit_code = 125
                metadata.termination_reason = "filesystem-violation"
                raise SandboxError(str(exc), metadata) from exc
            return SandboxResult(stdout=stdout, stderr=stderr, metadata=metadata)
        except asyncio.CancelledError:
            metadata.termination_reason = "cancelled"
            if created:
                await self._remove(container_name)
            raise
        finally:
            if created:
                cleanup_succeeded = await self._remove(container_name)
            metadata.cleanup_succeeded = cleanup_succeeded if created else True
            metadata.finished_at = datetime.now(UTC)


def prepare_workspace_identity(workspace: Path, uid: int = 65532, gid: int = 65532) -> None:
    """Give the fixed non-root task identity ownership of only its temporary workspace."""
    root = _validate_workspace(workspace)
    if os.geteuid() != 0:
        if os.geteuid() == uid:
            return
        raise PermissionError(
            "Worker must run as the sandbox UID or be able to chown its task workspace"
        )
    for path in [root, *root.rglob("*")]:
        if path == root / ".git" or (root / ".git") in path.parents:
            continue
        with contextlib.suppress(FileNotFoundError):
            os.chown(path, uid, gid, follow_symlinks=False)
