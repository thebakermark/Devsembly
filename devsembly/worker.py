from __future__ import annotations

import asyncio
import os

from temporalio.client import Client
from temporalio.worker import Worker

from devsembly.factory import (
    FactoryWorkflow,
    GovernedFactoryWorkflow,
    begin_committed_delivery,
    complete_committed_delivery,
    create_task_packet,
    evidence_gate,
    execute_autonomous_run,
    independent_review,
    record_run_memory,
)
from devsembly.github_provider import reconcile_github_page
from devsembly.sandbox import DockerExecutionSandbox
from devsembly.temporal_workflows import CommittedWorkflow, GitHubSnapshotWorkflow


async def main() -> None:
    await DockerExecutionSandbox().cleanup_stale()
    client = await Client.connect(os.getenv("DEVSEMBLY_TEMPORAL_ADDRESS", "localhost:7233"))
    task_queue = os.getenv("DEVSEMBLY_TEMPORAL_TASK_QUEUE", "devsembly-factory")
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[
            FactoryWorkflow,
            GovernedFactoryWorkflow,
            CommittedWorkflow,
            GitHubSnapshotWorkflow,
        ],
        activities=[
            begin_committed_delivery,
            complete_committed_delivery,
            create_task_packet,
            evidence_gate,
            execute_autonomous_run,
            independent_review,
            record_run_memory,
            reconcile_github_page,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
