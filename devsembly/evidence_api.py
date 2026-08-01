from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from devsembly.auth import authorize_request
from devsembly.evidence_schemas import EvidenceCreate, EvidenceRead
from devsembly.evidence_service import EvidenceService
from devsembly.evidence_storage import EvidenceStorage, MinioEvidenceStorage
from devsembly.unit_of_work import SqlAlchemyUnitOfWork

router = APIRouter(
    prefix=(
        "/api/v1/organizations/{organization_id}/initiatives/{initiative_id}"
        "/projects/{project_id}/evidence"
    ),
    tags=["Evidence"],
    dependencies=[Depends(authorize_request)],
)


def get_evidence_storage() -> EvidenceStorage:
    return MinioEvidenceStorage.from_environment()


Storage = Annotated[EvidenceStorage, Depends(get_evidence_storage)]


def get_evidence_service(storage: Storage) -> EvidenceService:
    return EvidenceService(lambda: SqlAlchemyUnitOfWork(), storage)


Service = Annotated[EvidenceService, Depends(get_evidence_service)]


@router.post("", response_model=EvidenceRead, status_code=status.HTTP_201_CREATED)
async def ingest_evidence(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    payload: EvidenceCreate,
    service: Service,
) -> EvidenceRead:
    evidence = await service.ingest(
        organization_id,
        initiative_id,
        project_id,
        kind=payload.kind,
        name=payload.name,
        content_type=payload.content_type,
        content=bytes(payload.content_base64),
        retention_class=payload.retention_class,
        workflow_run_id=payload.workflow_run_id,
        workflow_step_attempt_id=payload.workflow_step_attempt_id,
    )
    return EvidenceRead.model_validate(evidence)


@router.get("", response_model=list[EvidenceRead])
async def list_evidence(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    service: Service,
) -> list[EvidenceRead]:
    evidence = await service.list(organization_id, initiative_id, project_id)
    return [EvidenceRead.model_validate(item) for item in evidence]


@router.get("/{evidence_id}", response_model=EvidenceRead)
async def get_evidence(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    evidence_id: uuid.UUID,
    service: Service,
) -> EvidenceRead:
    evidence = await service.get(organization_id, initiative_id, project_id, evidence_id)
    return EvidenceRead.model_validate(evidence)


@router.get("/{evidence_id}/content")
async def retrieve_evidence_content(
    organization_id: uuid.UUID,
    initiative_id: uuid.UUID,
    project_id: uuid.UUID,
    evidence_id: uuid.UUID,
    service: Service,
) -> Response:
    evidence, content = await service.retrieve(
        organization_id, initiative_id, project_id, evidence_id
    )
    return Response(
        content=content,
        media_type=evidence.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="evidence-{evidence.id}"',
            "X-Content-SHA256": evidence.sha256,
            "X-Content-Type-Options": "nosniff",
            "X-Evidence-Id": str(evidence.id),
        },
    )
