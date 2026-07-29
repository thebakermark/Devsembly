from __future__ import annotations

import asyncio
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

from temporalio import activity, workflow

from devsembly.contracts import (
    FactoryRun,
    ProductRequest,
    RunStatus,
    TaskPacket,
    ValidationEvidence,
)


@activity.defn
async def create_task_packet(run: FactoryRun) -> FactoryRun:
    request = run.request
    run.status = RunStatus.PLANNING
    run.task_packet = TaskPacket(
        run_id=run.id,
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
    )
    return run


@activity.defn
async def execute_mock_builder(run: FactoryRun) -> FactoryRun:
    """Safe vertical-slice worker; replace with OpenHands/Codex provider adapter."""
    run.status = RunStatus.BUILDING
    run.summary = "Mock builder produced a bounded implementation artifact."
    return run


async def _run_command(command: str, cwd: Path) -> ValidationEvidence:
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
    )


@activity.defn
async def validate_run(run: FactoryRun) -> FactoryRun:
    run.status = RunStatus.VALIDATING
    assert run.task_packet is not None
    with TemporaryDirectory(prefix="devsembly-") as directory:
        workspace = Path(directory)
        # The MVP validates command execution independently from the builder.
        # Repository checkout and sandbox-provider adapters are the next slice.
        for command in run.task_packet.validation_commands:
            evidence = await _run_command(command, workspace)
            run.evidence.append(evidence)
            if evidence.exit_code != 0:
                run.status = RunStatus.ESCALATED
                run.summary = f"Validation failed: {command}"
                return run
    run.status = RunStatus.REVIEWING
    return run


@activity.defn
async def independent_review(run: FactoryRun) -> FactoryRun:
    failed = [item for item in run.evidence if item.exit_code != 0]
    if failed:
        run.status = RunStatus.ESCALATED
        run.summary = "Independent review rejected failed validation evidence."
    else:
        run.status = RunStatus.COMPLETED
        run.summary = "Factory vertical slice completed with independent evidence."
    return run


@workflow.defn
class FactoryWorkflow:
    @workflow.run
    async def run(self, request: ProductRequest) -> FactoryRun:
        run = FactoryRun(request=request)
        timeout = timedelta(minutes=5)
        run = await workflow.execute_activity(
            create_task_packet, run, start_to_close_timeout=timeout
        )
        run = await workflow.execute_activity(
            execute_mock_builder, run, start_to_close_timeout=timeout
        )
        run = await workflow.execute_activity(validate_run, run, start_to_close_timeout=timeout)
        run = await workflow.execute_activity(
            independent_review, run, start_to_close_timeout=timeout
        )
        return run
