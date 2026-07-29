from __future__ import annotations

import os
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from temporalio.client import Client

from devsembly.contracts import FactoryRun, ProductRequest
from devsembly.factory import FactoryWorkflow

app = FastAPI(title="Devsembly Factory API", version="0.1.0")


async def temporal_client() -> Client:
    address = os.getenv("DEVSEMBLY_TEMPORAL_ADDRESS", "localhost:7233")
    return await Client.connect(address)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/runs", response_model=dict[str, str], status_code=202)
async def start_run(request: ProductRequest) -> dict[str, str]:
    client = await temporal_client()
    workflow_id = f"factory-{uuid4()}"
    await client.start_workflow(
        FactoryWorkflow.run,
        request,
        id=workflow_id,
        task_queue="devsembly-factory",
    )
    return {"workflow_id": workflow_id, "status": "queued"}


@app.get("/runs/{workflow_id}", response_model=FactoryRun)
async def get_run(workflow_id: str) -> FactoryRun:
    client = await temporal_client()
    handle = client.get_workflow_handle(workflow_id)
    try:
        return await handle.result()
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
