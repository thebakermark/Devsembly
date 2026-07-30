from __future__ import annotations

import os
from typing import cast
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from temporalio.client import Client

from devsembly.contracts import FactoryRun, ProductRequest
from devsembly.database import check_database
from devsembly.factory import FactoryWorkflow

app = FastAPI(title="Devsembly Factory API", version="0.1.0")


async def temporal_client() -> Client:
    address = os.getenv("DEVSEMBLY_TEMPORAL_ADDRESS", "localhost:7233")
    return await Client.connect(address)


@app.get("/health/live")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness() -> dict[str, str]:
    checks: dict[str, str] = {}

    try:
        await temporal_client()
        checks["temporal"] = "ok"
    except Exception as exc:  # noqa: BLE001 - readiness reports dependency failures
        checks["temporal"] = f"unavailable: {type(exc).__name__}"

    try:
        await check_database()
        checks["postgres"] = "ok"
    except Exception as exc:  # noqa: BLE001 - readiness reports dependency failures
        checks["postgres"] = f"unavailable: {type(exc).__name__}"

    if any(value != "ok" for value in checks.values()):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=checks)

    return {"status": "ready", **checks}


@app.get("/health")
async def health() -> dict[str, str]:
    return await readiness()


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
        return cast(FactoryRun, await handle.result())
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
