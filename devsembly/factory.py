from __future__ import annotations

import asyncio
from datetime import timedelta
from pathlib import Path

from temporalio import activity, workflow

from devsembly.contracts import (
    FactoryRun,
    ProductRequest,
    RunStatus,
    TaskPacket,
    ValidationEvidence,
)
from devsembly.provider_command import CommandCodingProvider
from devsembly.source_control import GitHubCliSourceControlProvider
from devsembly.workspace import changed_paths, checkout_task, enforce_allowed_paths


@activity.defn
async def create_task_packet(run: FactoryRun) -> FactoryRun:
    request = run.request
    run.status = RunStatus.PLANNING
    run.task_packet = TaskPacket(
        run_id=run.id,
        title=request.title,
        objective=request.objective,
        repository_url=request.repository_url,
        base_branch=request.base_branch,
        branch_name=f"factory/{run.id}",
        allowed_paths=request.allowed_paths,
        acceptance_criteria=[
            "Requested behavior is implemented",
            "Automated validation passes",
            "Only allowed paths are changed",
            "Implementation is documented",
        ],
        validation_commands=request.validation_commands,
        max_repair_attempts=request.max_repair_attempts,
    )
    return run


async def _run_command(command: str, cwd: Path, attempt: int) -> ValidationEvidence:
    process = await asyncio.create_subprocess_shell(
        command,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return ValidationEvidence(
        command=command,
        exit_code=process.returncode or 0,
        stdout=stdout.decode(errors="replace")[-20_000:],
        stderr=stderr.decode(errors="replace")[-20_000:],
        attempt=attempt,
    )


async def _validate(task: TaskPacket, workspace: Path, attempt: int) -> list[ValidationEvidence]:
    evidence: list[ValidationEvidence] = []
    for command in task.validation_commands:
        result = await _run_command(command, workspace, attempt)
        evidence.append(result)
        if result.exit_code != 0:
            break
    return evidence


@activity.defn
async def execute_autonomous_run(run: FactoryRun) -> FactoryRun:
    task = run.task_packet
    if task is None:
        raise ValueError("Task packet must be created before execution")

    run.status = RunStatus.CHECKING_OUT
    workspace = await checkout_task(task)
    coding_provider = CommandCodingProvider()
    source_control = GitHubCliSourceControlProvider()
    try:
        run.status = RunStatus.BUILDING
        build = await coding_provider.build(task, workspace.root)
        run.summary = build.summary

        for attempt in range(task.max_repair_attempts + 1):
            paths = await changed_paths(workspace.root)
            enforce_allowed_paths(paths, task.allowed_paths)
            run.changed_paths = paths
            if not paths:
                run.status = RunStatus.ESCALATED
                run.summary = "Coding provider completed without producing changes."
                return run

            run.status = RunStatus.VALIDATING
            evidence = await _validate(task, workspace.root, attempt)
            run.evidence.extend(evidence)
            if all(item.exit_code == 0 for item in evidence):
                break
            if attempt >= task.max_repair_attempts:
                run.status = RunStatus.ESCALATED
                run.summary = "Validation failed after the allowed repair attempts."
                return run

            run.status = RunStatus.REPAIRING
            run.repair_attempts += 1
            repair = await coding_provider.repair(task, workspace.root, evidence, attempt + 1)
            run.summary = repair.summary

        run.status = RunStatus.PUBLISHING
        evidence_summary = "\n".join(
            f"- `{item.command}`: exit {item.exit_code} (attempt {item.attempt})"
            for item in run.evidence
        )
        body = (
            "## Devsembly autonomous run\n\n"
            f"**Objective:** {task.objective}\n\n"
            f"**Changed paths:** {', '.join(run.changed_paths)}\n\n"
            "## Validation evidence\n\n"
            f"{evidence_summary}\n\n"
            "This is a draft change request. Human review and approval are required."
        )
        run.change_request_url = await source_control.publish_draft_change_request(
            task,
            workspace.root,
            task.title,
            body,
        )
        run.status = RunStatus.REVIEWING
        run.summary = "Autonomous coding run completed and published for human review."
        return run
    except Exception as exc:  # noqa: BLE001 - activity must preserve failure context
        run.status = RunStatus.ESCALATED
        run.summary = f"Autonomous execution failed: {type(exc).__name__}: {exc}"
        return run
    finally:
        workspace.cleanup()


@activity.defn
async def independent_review(run: FactoryRun) -> FactoryRun:
    failed = [item for item in run.evidence if item.exit_code != 0]
    if run.status == RunStatus.ESCALATED or failed:
        run.status = RunStatus.ESCALATED
        if not run.summary:
            run.summary = "Independent review rejected the run."
    elif not run.change_request_url:
        run.status = RunStatus.ESCALATED
        run.summary = "Independent review found no published change request."
    else:
        run.status = RunStatus.COMPLETED
    return run


@workflow.defn
class FactoryWorkflow:
    @workflow.run
    async def run(self, request: ProductRequest) -> FactoryRun:
        run = FactoryRun(request=request)
        planning_timeout = timedelta(minutes=5)
        execution_timeout = timedelta(minutes=45)
        run = await workflow.execute_activity(
            create_task_packet, run, start_to_close_timeout=planning_timeout
        )
        run = await workflow.execute_activity(
            execute_autonomous_run, run, start_to_close_timeout=execution_timeout
        )
        run = await workflow.execute_activity(
            independent_review, run, start_to_close_timeout=planning_timeout
        )
        return run
