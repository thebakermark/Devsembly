from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from urllib.parse import urlparse

from devsembly.contracts import TaskPacket


@dataclass
class Workspace:
    root: Path
    _temporary: TemporaryDirectory[str]

    def cleanup(self) -> None:
        self._temporary.cleanup()


async def _run(*args: str, cwd: Path | None = None) -> tuple[int, str, str]:
    process = await asyncio.create_subprocess_exec(
        *args,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return process.returncode or 0, stdout.decode(errors="replace"), stderr.decode(errors="replace")


def validate_repository_url(repository_url: str) -> None:
    parsed = urlparse(repository_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Only HTTPS repository URLs are accepted")
    if parsed.username or parsed.password:
        raise ValueError("Credentials must not be embedded in repository URLs")


async def checkout_task(task: TaskPacket) -> Workspace:
    repository_url = str(task.repository_url)
    validate_repository_url(repository_url)
    temporary = TemporaryDirectory(prefix=f"devsembly-{task.run_id}-")
    root = Path(temporary.name) / "repository"
    code, _, stderr = await _run(
        "git",
        "clone",
        "--depth",
        "1",
        "--branch",
        task.base_branch,
        repository_url,
        str(root),
    )
    if code != 0:
        temporary.cleanup()
        raise RuntimeError(f"Repository checkout failed: {stderr[-2000:]}")
    code, _, stderr = await _run("git", "checkout", "-b", task.branch_name, cwd=root)
    if code != 0:
        temporary.cleanup()
        raise RuntimeError(f"Branch creation failed: {stderr[-2000:]}")
    return Workspace(root=root, _temporary=temporary)


async def changed_paths(root: Path) -> list[str]:
    code, stdout, stderr = await _run(
        "git", "status", "--porcelain=v2", "-z", "--untracked-files=all", cwd=root
    )
    if code != 0:
        raise RuntimeError(f"Unable to inspect workspace: {stderr[-2000:]}")
    records = stdout.split("\0")
    paths: list[str] = []
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        kind = record[0]
        if kind == "1":
            fields = record.split(" ", 8)
            if len(fields) != 9:
                raise RuntimeError("Unable to parse ordinary git status record")
            paths.append(fields[8])
        elif kind == "2":
            fields = record.split(" ", 9)
            if len(fields) != 10 or index >= len(records):
                raise RuntimeError("Unable to parse renamed git status record")
            paths.append(fields[9])
            index += 1  # porcelain v2 emits the original path as a separate NUL record
        elif kind in {"?", "!"}:
            paths.append(record[2:])
        elif kind == "u":
            fields = record.split(" ", 10)
            if len(fields) != 11:
                raise RuntimeError("Unable to parse unmerged git status record")
            paths.append(fields[10])
        else:
            raise RuntimeError(f"Unsupported git status record type: {kind!r}")
    return paths


def enforce_allowed_paths(paths: list[str], allowed_paths: list[str]) -> None:
    boundaries = [PurePosixPath(prefix) for prefix in allowed_paths]
    disallowed: list[str] = []
    for path in paths:
        candidate = PurePosixPath(path)
        if candidate.is_absolute() or ".." in candidate.parts:
            disallowed.append(path)
            continue
        if not any(
            candidate == boundary or candidate.is_relative_to(boundary) for boundary in boundaries
        ):
            disallowed.append(path)
    if disallowed:
        raise PermissionError(f"Provider changed paths outside the task boundary: {disallowed}")
