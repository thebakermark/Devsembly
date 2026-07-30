from __future__ import annotations

import os
from typing import cast
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from temporalio.client import Client

from devsembly.contracts import FactoryRun, ProductRequest
from devsembly.database import check_database
from devsembly.errors import (
    DuplicateResourceError,
    ResourceNotFoundError,
    StaleVersionError,
)
from devsembly.factory import FactoryWorkflow
from devsembly.genesis_api import router as genesis_router

app = FastAPI(title="Devsembly Factory API", version="0.1.0")
app.include_router(genesis_router)


@app.exception_handler(ResourceNotFoundError)
async def resource_not_found(request: Request, exc: ResourceNotFoundError) -> JSONResponse:
    del request
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "code": "resource_not_found",
            "detail": str(exc),
            "resource": exc.resource,
        },
    )


@app.exception_handler(DuplicateResourceError)
async def duplicate_resource(request: Request, exc: DuplicateResourceError) -> JSONResponse:
    del request
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "code": "duplicate_resource",
            "detail": str(exc),
            "resource": exc.resource,
        },
    )


@app.exception_handler(StaleVersionError)
async def stale_version(request: Request, exc: StaleVersionError) -> JSONResponse:
    del request
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "code": "stale_version",
            "detail": str(exc),
            "resource": exc.resource,
            "expected_version": exc.expected_version,
        },
    )


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
