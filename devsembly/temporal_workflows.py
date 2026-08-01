from __future__ import annotations

from datetime import timedelta

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


@workflow.defn
class GitHubSnapshotWorkflow:
    @workflow.run
    async def run(self, request: dict[str, object]) -> None:
        raw_kinds = request.get("kinds")
        kinds = (
            [str(kind) for kind in raw_kinds]
            if isinstance(raw_kinds, list)
            else ["issue", "pull_request", "milestone", "branch", "commit", "workflow_run"]
        )
        for kind in kinds:
            next_url: str | None = None
            while True:
                result = await workflow.execute_activity(
                    "reconcile_github_page",
                    {**request, "kind": kind, "next_url": next_url},
                    start_to_close_timeout=timedelta(minutes=2),
                    schedule_to_close_timeout=timedelta(minutes=15),
                    result_type=dict[str, object],
                )
                value = result.get("next_url")
                next_url = None if value is None else str(value)
                if next_url is None:
                    break
        raw_interval = request.get("interval_seconds", 1800)
        if not isinstance(raw_interval, int):
            raise TypeError("interval_seconds must be an integer")
        await workflow.sleep(timedelta(seconds=raw_interval))
        workflow.continue_as_new(args=[request])
