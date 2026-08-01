from __future__ import annotations

import os
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, Response
from temporalio.client import Client

from devsembly.audit import reset_current_audit_actor, set_current_audit_actor
from devsembly.cost_api import router as cost_router
from devsembly.database import check_database
from devsembly.errors import (
    CostGovernanceError,
    DuplicateResourceError,
    EvidenceIntegrityError,
    IdempotencyConflictError,
    InvalidTransitionError,
    ProjectStateValidationError,
    ResourceNotFoundError,
    StaleVersionError,
)
from devsembly.evidence_api import router as evidence_router
from devsembly.genesis_api import router as genesis_router
from devsembly.github_sync_api import conflict_router as github_conflict_router
from devsembly.github_sync_api import router as github_sync_router
from devsembly.identity_api import organization_router as identity_organization_router
from devsembly.identity_api import router as identity_router
from devsembly.memory_api import router as memory_router
from devsembly.outbox_publisher import worker_readiness
from devsembly.pie_api import router as pie_router
from devsembly.workflow_api import internal_router as workflow_internal_router
from devsembly.workflow_api import router as workflow_router
from devsembly.workflow_dispatcher import WORKER_NAME as DISPATCHER_WORKER_NAME

app = FastAPI(title="Devsembly Factory API", version="0.1.0")
app.include_router(genesis_router)
app.include_router(workflow_router)
app.include_router(workflow_internal_router)
app.include_router(cost_router)
app.include_router(identity_router)
app.include_router(identity_organization_router)
app.include_router(evidence_router)
app.include_router(pie_router)
app.include_router(memory_router)
app.include_router(github_sync_router)
app.include_router(github_conflict_router)


@app.middleware("http")
async def audit_actor_scope(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    token = set_current_audit_actor("service", "genesis-control-plane")
    try:
        return await call_next(request)
    finally:
        reset_current_audit_actor(token)


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
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "code": "cost_governance_error",
            "detail": str(exc),
        },
    )


@app.exception_handler(EvidenceIntegrityError)
async def evidence_integrity_error(request: Request, exc: EvidenceIntegrityError) -> JSONResponse:
    del request
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "code": "evidence_integrity_error",
            "detail": str(exc),
            "evidence_id": exc.evidence_id,
        },
    )


@app.exception_handler(ProjectStateValidationError)
async def project_state_validation_error(
    request: Request, exc: ProjectStateValidationError
) -> JSONResponse:
    del request
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"code": "project_state_validation_error", "detail": exc.detail},
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

    try:
        outbox_status = await worker_readiness()
        checks["outbox_publisher"] = "ok" if outbox_status["ready"] is True else "unavailable"
    except Exception as exc:  # noqa: BLE001 - readiness reports dependency failures
        checks["outbox_publisher"] = f"unavailable: {type(exc).__name__}"

    try:
        dispatcher_status = await worker_readiness(worker_name=DISPATCHER_WORKER_NAME)
        checks["temporal_dispatcher"] = (
            "ok" if dispatcher_status["ready"] is True else "unavailable"
        )
    except Exception as exc:  # noqa: BLE001 - readiness reports dependency failures
        checks["temporal_dispatcher"] = f"unavailable: {type(exc).__name__}"

    if any(value != "ok" for value in checks.values()):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=checks)

    return {"status": "ready", **checks}


@app.get("/health")
async def health() -> dict[str, str]:
    return await readiness()
