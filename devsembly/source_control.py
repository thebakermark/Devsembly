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

    @staticmethod
    def _environment() -> dict[str, str]:
        token = os.getenv("DEVSEMBLY_SOURCE_CONTROL_TOKEN")
        if not token:
            raise RuntimeError("DEVSEMBLY_SOURCE_CONTROL_TOKEN is not configured")
        environment = os.environ.copy()
        environment["GH_TOKEN"] = token
        return environment

    async def ensure_work_item(
        self,
        task: TaskPacket,
        workspace: Path,
        title: str,
        body: str,
    ) -> str:
        """Create one traceable issue per run, reusing it after an activity retry."""
        environment = self._environment()
        marker = f"devsembly-run:{task.run_id}"
        lookup = await asyncio.create_subprocess_exec(
            "gh",
            "issue",
            "list",
            "--state",
            "all",
            "--search",
            f"{marker} in:body",
            "--json",
            "url",
            "--jq",
            ".[0].url // empty",
            "--limit",
            "1",
            cwd=workspace,
            env=environment,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await lookup.communicate()
        if lookup.returncode != 0:
            raise RuntimeError(
                f"Work-item lookup failed: {stderr.decode(errors='replace')[-4000:]}"
            )
        if existing := stdout.decode(errors="replace").strip():
            return existing

        create = await asyncio.create_subprocess_exec(
            "gh",
            "issue",
            "create",
            "--title",
            title,
            "--body",
            f"{body}\n\n<!-- {marker} -->",
            cwd=workspace,
            env=environment,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await create.communicate()
        if create.returncode != 0:
            raise RuntimeError(
                f"Work-item creation failed: {stderr.decode(errors='replace')[-4000:]}"
            )
        return stdout.decode(errors="replace").strip()

    async def publish_draft_change_request(
        self,
        task: TaskPacket,
        workspace: Path,
        title: str,
        body: str,
    ) -> str:
        env = self._environment()

        existing_pr = await asyncio.create_subprocess_exec(
            "gh",
            "pr",
            "list",
            "--state",
            "all",
            "--head",
            task.branch_name,
            "--json",
            "url",
            "--jq",
            ".[0].url // empty",
            "--limit",
            "1",
            cwd=workspace,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await existing_pr.communicate()
        if existing_pr.returncode != 0:
            raise RuntimeError(
                f"Change-request lookup failed: {stderr.decode(errors='replace')[-4000:]}"
            )
        if existing := stdout.decode(errors="replace").strip():
            return existing

        auth = await asyncio.create_subprocess_exec(
            "gh",
            "auth",
            "setup-git",
            cwd=workspace,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await auth.communicate()
        if auth.returncode != 0:
            raise RuntimeError(
                f"Git authentication setup failed: {stderr.decode(errors='replace')[-4000:]}"
            )

        for args in (
            ("git", "config", "user.name", "Devsembly Factory"),
            ("git", "config", "user.email", "factory@devsembly.local"),
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
