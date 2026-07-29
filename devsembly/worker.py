from __future__ import annotations

import asyncio
import os

from temporalio.client import Client
from temporalio.worker import Worker

from devsembly.factory import (
    FactoryWorkflow,
    create_task_packet,
    execute_mock_builder,
    independent_review,
    validate_run,
)


async def main() -> None:
    client = await Client.connect(
        os.getenv("DEVSEMBLY_TEMPORAL_ADDRESS", "localhost:7233")
    )
    worker = Worker(
        client,
        task_queue="devsembly-factory",
        workflows=[FactoryWorkflow],
        activities=[
            create_task_packet,
            execute_mock_builder,
            validate_run,
            independent_review,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
