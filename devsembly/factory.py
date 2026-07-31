from __future__ import annotations

import asyncio
import json
import shlex
import uuid
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from temporalio import activity, workflow

from devsembly.contracts import (
    FactoryRun,
    ProductRequest,
    RunStatus,
    TaskPacket,
    ValidationEvidence,
)
from devsembly.domain import (
    MemoryKind,
    MemorySensitivity,
    ProjectStateAssertionStatus,
    WorkflowAttemptStatus,
    WorkflowRunStatus,
)
from devsembly.memory_service import MemoryContextService
from devsembly.provider_command import CommandCodingProvider
from devsembly.source_control import GitHubCliSourceControlProvider
from devsembly.unit_of_work import SqlAlchemyUnitOfWork
from devsembly.workflow_service import WorkflowService
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
    arguments = shlex.split(command)
    if not arguments:
        raise ValueError("Validation command must not be empty")
    process = await asyncio.create_subprocess_exec(
        *arguments,
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
        run.work_item_url = await source_control.ensure_work_item(
            task,
            workspace.root,
            task.title,
            "## Objective\n\n"
            f"{task.objective}\n\n"
            "## Acceptance criteria\n\n"
            + "\n".join(f"- {item}" for item in task.acceptance_criteria),
        )
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
            f"**Work item:** {run.work_item_url}\n\n"
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


@activity.defn
async def record_run_memory(run: FactoryRun) -> FactoryRun:
    """Propose a completed delivery episode to governed project memory."""
    context = run.request.project_context
    if run.status is not RunStatus.COMPLETED or context is None:
        return run
    content = json.dumps(
        {
            "run_id": str(run.id),
            "objective": run.request.objective,
            "work_item_url": run.work_item_url,
            "change_request_url": run.change_request_url,
            "changed_paths": run.changed_paths,
            "repair_attempts": run.repair_attempts,
            "validation": [item.model_dump(mode="json") for item in run.evidence],
            "summary": run.summary,
        },
        sort_keys=True,
    )
    service = MemoryContextService(lambda: SqlAlchemyUnitOfWork())
    proposal = await service.propose(
        context.organization_id,
        context.initiative_id,
        context.project_id,
        kind=MemoryKind.EPISODIC,
        title=f"Delivery run: {run.request.title}",
        content=content,
        sensitivity=MemorySensitivity.INTERNAL,
        source_revision_id=None,
        source_uri=run.change_request_url,
        assertion_status=ProjectStateAssertionStatus.VERIFIED,
        confidence=Decimal(1),
        retention_until=None,
        proposed_by="service:devsembly-factory",
    )
    run.memory_proposal_id = proposal.id
    return run


def _committed_scope(
    request: dict[str, object],
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    return (
        uuid.UUID(str(request["organization_id"])),
        uuid.UUID(str(request["initiative_id"])),
        uuid.UUID(str(request["project_id"])),
        uuid.UUID(str(request["workflow_run_id"])),
    )


@activity.defn
async def begin_committed_delivery(request: dict[str, object]) -> None:
    """Advance a persisted, dispatched run before external execution begins."""
    organization_id, initiative_id, project_id, workflow_run_id = _committed_scope(request)
    service = WorkflowService(lambda: SqlAlchemyUnitOfWork())
    detail = await service.get_workflow_run(
        organization_id, initiative_id, project_id, workflow_run_id
    )
    await service.update_workflow_run_status(
        organization_id,
        initiative_id,
        project_id,
        workflow_run_id,
        detail.run.version,
        target_status=WorkflowRunStatus.RUNNING,
        temporal_workflow_id=None,
    )


@activity.defn
async def complete_committed_delivery(request: dict[str, object], run: FactoryRun) -> FactoryRun:
    """Persist step evidence and the terminal status for a governed delivery run."""
    organization_id, initiative_id, project_id, workflow_run_id = _committed_scope(request)
    service = WorkflowService(lambda: SqlAlchemyUnitOfWork())
    detail = await service.get_workflow_run(
        organization_id, initiative_id, project_id, workflow_run_id
    )
    succeeded = run.status is RunStatus.COMPLETED
    attempt_status = WorkflowAttemptStatus.SUCCEEDED if succeeded else WorkflowAttemptStatus.FAILED
    outcome: dict[str, object] = {
        "factory_run_id": str(run.id),
        "work_item_url": run.work_item_url,
        "change_request_url": run.change_request_url,
        "changed_paths": run.changed_paths,
        "validation_count": len(run.evidence),
        "repair_attempts": run.repair_attempts,
        "memory_proposal_id": (
            None if run.memory_proposal_id is None else str(run.memory_proposal_id)
        ),
        "summary": run.summary,
    }
    for step_detail in detail.steps:
        await service.record_workflow_step_attempt(
            organization_id,
            initiative_id,
            project_id,
            workflow_run_id,
            step_detail.step.id,
            step_detail.step.version,
            status=attempt_status,
            result_payload=outcome if succeeded else None,
            error_payload=None if succeeded else outcome,
            started_at=None,
        )
    refreshed = await service.get_workflow_run(
        organization_id, initiative_id, project_id, workflow_run_id
    )
    await service.update_workflow_run_status(
        organization_id,
        initiative_id,
        project_id,
        workflow_run_id,
        refreshed.run.version,
        target_status=(WorkflowRunStatus.SUCCEEDED if succeeded else WorkflowRunStatus.FAILED),
        temporal_workflow_id=None,
    )
    return run


@workflow.defn
class GovernedFactoryWorkflow:
    """Execute software delivery only after Genesis has committed and dispatched intent."""

    @workflow.run
    async def run(self, request: dict[str, object]) -> FactoryRun:
        if request.get("workflow_kind") != "software_delivery":
            raise ValueError("GovernedFactoryWorkflow requires workflow_kind=software_delivery")
        raw_payload = request.get("input_payload")
        if not isinstance(raw_payload, dict):
            raise TypeError("software_delivery input_payload must be an object")
        payload = dict(raw_payload)
        payload["project_context"] = {
            "organization_id": request["organization_id"],
            "initiative_id": request["initiative_id"],
            "project_id": request["project_id"],
        }
        product_request = ProductRequest.model_validate(payload)
        run = FactoryRun(request=product_request)
        short_timeout = timedelta(minutes=5)
        await workflow.execute_activity(
            begin_committed_delivery, request, start_to_close_timeout=short_timeout
        )
        run = await workflow.execute_activity(
            create_task_packet, run, start_to_close_timeout=short_timeout
        )
        run = await workflow.execute_activity(
            execute_autonomous_run,
            run,
            start_to_close_timeout=timedelta(minutes=45),
        )
        run = await workflow.execute_activity(
            independent_review, run, start_to_close_timeout=short_timeout
        )
        run = await workflow.execute_activity(
            record_run_memory, run, start_to_close_timeout=short_timeout
        )
        return await workflow.execute_activity(
            complete_committed_delivery,
            args=[request, run],
            start_to_close_timeout=short_timeout,
        )


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
        run = await workflow.execute_activity(
            record_run_memory, run, start_to_close_timeout=planning_timeout
        )
        return run
