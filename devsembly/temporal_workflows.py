from __future__ import annotations

from temporalio import workflow


@workflow.defn
class CommittedWorkflow:
    """Durable boundary for a workflow run already committed by Genesis."""

    def __init__(self) -> None:
        self._state: dict[str, object] = {"status": "starting"}
        self._result: dict[str, object] | None = None

    @workflow.run
    async def run(self, request: dict[str, object]) -> dict[str, object]:
        self._state = {
            "status": "queued",
            "workflow_run_id": request["workflow_run_id"],
            "workflow_kind": request["workflow_kind"],
        }
        await workflow.wait_condition(lambda: self._result is not None)
        assert self._result is not None
        return self._result

    @workflow.signal
    async def finish(self, result: dict[str, object]) -> None:
        self._result = dict(result)
        self._state = {"status": "completed", **self._result}

    @workflow.query
    def state(self) -> dict[str, object]:
        return dict(self._state)
