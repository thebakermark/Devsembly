from __future__ import annotations

import asyncio
import os
from pathlib import Path

from devsembly.contracts import TaskPacket


async def _run(*args: str, cwd: Path) -> tuple[int, str, str]:
    process = await asyncio.create_subprocess_exec(
        *args,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return process.returncode or 0, stdout.decode(errors="replace"), stderr.decode(errors="replace")


class GitHubCliSourceControlProvider:
    """GitHub implementation of the source-control provider boundary."""

    async def publish_draft_change_request(
        self,
        task: TaskPacket,
        workspace: Path,
        title: str,
        body: str,
    ) -> str:
        token = os.getenv("DEVSEMBLY_SOURCE_CONTROL_TOKEN")
        if not token:
            raise RuntimeError("DEVSEMBLY_SOURCE_CONTROL_TOKEN is not configured")
        env = os.environ.copy()
        env["GH_TOKEN"] = token

        for args in (
            ("git", "add", "--all"),
            ("git", "commit", "-m", f"Devsembly run {task.run_id}"),
            ("git", "push", "--set-upstream", "origin", task.branch_name),
        ):
            process = await asyncio.create_subprocess_exec(
                *args,
                cwd=workspace,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await process.communicate()
            if process.returncode != 0:
                raise RuntimeError(
                    f"Source-control command failed: {stderr.decode(errors='replace')[-4000:]}"
                )

        process = await asyncio.create_subprocess_exec(
            "gh",
            "pr",
            "create",
            "--draft",
            "--base",
            task.base_branch,
            "--head",
            task.branch_name,
            "--title",
            title,
            "--body",
            body,
            cwd=workspace,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(
                f"Draft change request failed: {stderr.decode(errors='replace')[-4000:]}"
            )
        return stdout.decode(errors="replace").strip()
