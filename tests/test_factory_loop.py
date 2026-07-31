from __future__ import annotations

import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

import devsembly.factory as factory_module
from devsembly.contracts import (
    FactoryRun,
    ProductRequest,
    ProjectContext,
    RunStatus,
    ValidationEvidence,
)
from devsembly.factory import create_task_packet, execute_autonomous_run, independent_review
from devsembly.providers import BuildResult
from devsembly.workflow_dispatcher import TemporalWorkflowStarter


def request(*, with_project_context: bool = False) -> ProductRequest:
    context = None
    if with_project_context:
        context = ProjectContext(
            organization_id=uuid.uuid4(),
            initiative_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
        )
    return ProductRequest(
        title="Add a fixture endpoint",
        objective="Create a tested endpoint in the fixture repository.",
        repository_url="https://github.com/example/fixture",
        allowed_paths=["src/", "tests/"],
        validation_commands=["pytest -q"],
        project_context=context,
    )


@pytest.mark.asyncio
async def test_delivery_loop_creates_work_item_before_build_and_draft_pr(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    events: list[str] = []

    class Workspace:
        root = tmp_path

        def cleanup(self) -> None:
            events.append("cleanup")

    class CodingProvider:
        async def build(self, task: object, workspace: Path) -> BuildResult:
            del task, workspace
            events.append("build")
            return BuildResult("implemented", ["src/fixture.py"])

        async def repair(self, *args: object) -> BuildResult:
            raise AssertionError(f"unexpected repair: {args}")

    class SourceControlProvider:
        async def ensure_work_item(self, *args: object) -> str:
            events.append("issue")
            return "https://github.com/example/fixture/issues/1"

        async def publish_draft_change_request(self, *args: object) -> str:
            events.append("draft-pr")
            return "https://github.com/example/fixture/pull/2"

    async def checkout(task: object) -> Workspace:
        del task
        events.append("workspace")
        return Workspace()

    async def paths(root: Path) -> list[str]:
        del root
        return ["src/fixture.py", "tests/test_fixture.py"]

    async def validate(task: object, root: Path, attempt: int) -> list[ValidationEvidence]:
        del task, root
        events.append("validate")
        return [ValidationEvidence(command="pytest -q", exit_code=0, attempt=attempt)]

    monkeypatch.setattr(factory_module, "checkout_task", checkout)
    monkeypatch.setattr(factory_module, "changed_paths", paths)
    monkeypatch.setattr(factory_module, "_validate", validate)
    monkeypatch.setattr(factory_module, "CommandCodingProvider", CodingProvider)
    monkeypatch.setattr(factory_module, "GitHubCliSourceControlProvider", SourceControlProvider)

    run = await create_task_packet(FactoryRun(request=request()))
    run = await execute_autonomous_run(run)
    run = await independent_review(run)

    assert events == ["workspace", "issue", "build", "validate", "draft-pr", "cleanup"]
    assert run.status is RunStatus.COMPLETED
    assert run.work_item_url.endswith("/issues/1")
    assert run.change_request_url.endswith("/pull/2")
    assert run.changed_paths == ["src/fixture.py", "tests/test_fixture.py"]


@pytest.mark.asyncio
async def test_completed_run_is_proposed_to_governed_project_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal_id = uuid.uuid4()
    captured: dict[str, object] = {}

    class MemoryService:
        def __init__(self, unit_of_work: object) -> None:
            del unit_of_work

        async def propose(self, *scope: uuid.UUID, **values: object) -> SimpleNamespace:
            captured["scope"] = scope
            captured.update(values)
            return SimpleNamespace(id=proposal_id)

    monkeypatch.setattr(factory_module, "MemoryContextService", MemoryService)
    run = FactoryRun(
        request=request(with_project_context=True),
        status=RunStatus.COMPLETED,
        work_item_url="https://github.com/example/fixture/issues/1",
        change_request_url="https://github.com/example/fixture/pull/2",
        changed_paths=["src/fixture.py"],
        evidence=[ValidationEvidence(command="pytest -q", exit_code=0)],
    )

    result = await factory_module.record_run_memory(run)

    assert result.memory_proposal_id == proposal_id
    assert captured["source_uri"] == run.change_request_url
    assert "fixture/issues/1" in str(captured["content"])


@pytest.mark.asyncio
async def test_validation_command_does_not_invoke_a_shell(tmp_path: Path) -> None:
    evidence = await factory_module._run_command(
        'python -c "import sys; sys.exit(7)" && touch should-not-exist',
        tmp_path,
        0,
    )

    assert evidence.exit_code != 0
    assert not (tmp_path / "should-not-exist").exists()


@pytest.mark.asyncio
async def test_dispatcher_routes_only_software_delivery_to_factory_workflow() -> None:
    calls: list[tuple[object, dict[str, object], dict[str, object]]] = []

    class TemporalClient:
        async def start_workflow(
            self,
            workflow: object,
            payload: dict[str, object],
            **options: object,
        ) -> None:
            calls.append((workflow, payload, options))

    starter = TemporalWorkflowStarter(TemporalClient(), "factory-queue")  # type: ignore[arg-type]
    await starter.start({"workflow_kind": "software_delivery"}, "governed-1")
    await starter.start({"workflow_kind": "generic"}, "generic-1")

    assert calls[0][0] is factory_module.GovernedFactoryWorkflow.run
    assert calls[1][0].__qualname__ == "CommittedWorkflow.run"  # type: ignore[union-attr]
    assert calls[0][2]["task_queue"] == "factory-queue"
