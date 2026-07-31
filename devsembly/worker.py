from __future__ import annotations

import asyncio
import os

from temporalio.client import Client
from temporalio.worker import Worker

from devsembly.factory import (
    FactoryWorkflow,
    create_task_packet,
    execute_autonomous_run,
    independent_review,
)
from devsembly.github_provider import reconcile_github_page
from devsembly.temporal_workflows import CommittedWorkflow, GitHubSnapshotWorkflow


async def main() -> None:
    client = await Client.connect(os.getenv("DEVSEMBLY_TEMPORAL_ADDRESS", "localhost:7233"))
    task_queue = os.getenv("DEVSEMBLY_TEMPORAL_TASK_QUEUE", "devsembly-factory")
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[FactoryWorkflow, CommittedWorkflow, GitHubSnapshotWorkflow],
        activities=[
            create_task_packet,
            execute_autonomous_run,
            independent_review,
            reconcile_github_page,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
