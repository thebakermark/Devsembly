from __future__ import annotations

import os
from typing import cast

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from temporalio.client import Client

from devsembly.contracts import FactoryRun
from devsembly.cost_api import router as cost_router
from devsembly.database import check_database
from devsembly.errors import (
    CostGovernanceError,
    DuplicateResourceError,
    IdempotencyConflictError,
    InvalidTransitionError,
    ResourceNotFoundError,
    StaleVersionError,
)
from devsembly.genesis_api import router as genesis_router
from devsembly.workflow_api import internal_router as workflow_internal_router
from devsembly.workflow_api import router as workflow_router

app = FastAPI(title="Devsembly Factory API", version="0.1.0")
app.include_router(genesis_router)
app.include_router(workflow_router)
app.include_router(workflow_internal_router)
app.include_router(cost_router)


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


@app.exception_handler(IdempotencyConflictError)
async def idempotency_conflict(request: Request, exc: IdempotencyConflictError) -> JSONResponse:
    del request
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "code": "idempotency_conflict",
            "detail": str(exc),
            "idempotency_key": exc.idempotency_key,
        },
    )


@app.exception_handler(InvalidTransitionError)
async def invalid_transition(request: Request, exc: InvalidTransitionError) -> JSONResponse:
    del request
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "code": "invalid_transition",
            "detail": str(exc),
            "resource": exc.resource,
            "current_status": exc.current_status,
            "target_status": exc.target_status,
        },
    )


@app.exception_handler(CostGovernanceError)
async def cost_governance_error(request: Request, exc: CostGovernanceError) -> JSONResponse:
    del request
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": "cost_governance_error",
            "detail": str(exc),
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


@app.get("/runs/{workflow_id}", response_model=FactoryRun)
async def get_run(workflow_id: str) -> FactoryRun:
    client = await temporal_client()
    handle = client.get_workflow_handle(workflow_id)
    try:
        return cast(FactoryRun, await handle.result())
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
