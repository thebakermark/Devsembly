from __future__ import annotations

import asyncio
import hashlib
import uuid
from collections.abc import Callable, Sequence
from contextlib import suppress
from datetime import UTC, datetime, timedelta

from devsembly.audit import current_audit_actor
from devsembly.domain import (
    Evidence,
    EvidenceKind,
    EvidenceRetentionClass,
    OutboxMessage,
)
from devsembly.errors import EvidenceIntegrityError, ResourceNotFoundError
from devsembly.evidence_storage import EvidenceStorage
from devsembly.unit_of_work import UnitOfWork

UnitOfWorkFactory = Callable[[], UnitOfWork]
Clock = Callable[[], datetime]

RETENTION_DAYS: dict[EvidenceRetentionClass, int | None] = {
    EvidenceRetentionClass.TRANSIENT: 30,
    EvidenceRetentionClass.STANDARD: 365,
    EvidenceRetentionClass.COMPLIANCE: 2557,
    EvidenceRetentionClass.PERMANENT: None,
}


def _utc_now() -> datetime:
    return datetime.now(UTC)


class EvidenceService:
    def __init__(
        self,
        unit_of_work: UnitOfWorkFactory,
        storage: EvidenceStorage,
        clock: Clock = _utc_now,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._storage = storage
        self._clock = clock

    async def ingest(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
        *,
        kind: EvidenceKind,
        name: str,
        content_type: str,
        content: bytes,
        retention_class: EvidenceRetentionClass,
        workflow_run_id: uuid.UUID | None,
        workflow_step_attempt_id: uuid.UUID | None,
    ) -> Evidence:
        now = self._clock()
        digest = hashlib.sha256(content).hexdigest()
        evidence_id = uuid.uuid4()
        object_key = (
            f"organizations/{organization_id}/projects/{project_id}/evidence/{digest}/{evidence_id}"
        )
        retention_days = RETENTION_DAYS[retention_class]
        retain_until = None if retention_days is None else now + timedelta(days=retention_days)

        stored = False
        try:
            async with self._unit_of_work() as unit:
                await self._require_project(unit, organization_id, initiative_id, project_id)
                await self._validate_workflow_links(
                    unit,
                    project_id,
                    workflow_run_id,
                    workflow_step_attempt_id,
                )
                saved = await asyncio.to_thread(
                    self._storage.put, object_key, content, content_type
                )
                stored = True
                evidence = Evidence(
                    id=evidence_id,
                    project_id=project_id,
                    workflow_run_id=workflow_run_id,
                    workflow_step_attempt_id=workflow_step_attempt_id,
                    kind=kind,
                    name=name,
                    content_type=content_type,
                    object_key=saved.object_key,
                    sha256=saved.sha256,
                    size_bytes=saved.size_bytes,
                    retention_class=retention_class,
                    retain_until=retain_until,
                    created_at=now,
                )
                await unit.evidence.add(evidence)
                actor_type, actor_id = current_audit_actor()
                await unit.outbox.add(
                    OutboxMessage(
                        id=uuid.uuid4(),
                        occurred_at=now,
                        topic="genesis.evidence.ingested",
                        aggregate_id=str(evidence.id),
                        payload={
                            "organization_id": str(organization_id),
                            "project_id": str(project_id),
                            "evidence_id": str(evidence.id),
                            "sha256": evidence.sha256,
                            "retention_class": retention_class.value,
                        },
                        actor_type=actor_type,
                        actor_id=actor_id,
                    )
                )
                await unit.commit()
                return evidence
        except Exception:
            if stored:
                with suppress(Exception):
                    await asyncio.to_thread(self._storage.delete, object_key)
            raise

    async def get(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
        evidence_id: uuid.UUID,
    ) -> Evidence:
        async with self._unit_of_work() as unit:
            await self._require_project(unit, organization_id, initiative_id, project_id)
            evidence = await unit.evidence.get(project_id, evidence_id)
            if evidence is None:
                raise ResourceNotFoundError("evidence")
            return evidence

    async def list(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> Sequence[Evidence]:
        async with self._unit_of_work() as unit:
            await self._require_project(unit, organization_id, initiative_id, project_id)
            return await unit.evidence.list(project_id)

    async def retrieve(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
        evidence_id: uuid.UUID,
    ) -> tuple[Evidence, bytes]:
        evidence = await self.get(organization_id, initiative_id, project_id, evidence_id)
        content = await asyncio.to_thread(self._storage.get, evidence.object_key)
        digest = hashlib.sha256(content).hexdigest()
        if digest != evidence.sha256 or len(content) != evidence.size_bytes:
            raise EvidenceIntegrityError(str(evidence.id))
        return evidence, content

    @staticmethod
    async def _require_project(
        unit: UnitOfWork,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> None:
        organization = await unit.organizations.get(organization_id)
        initiative = await unit.initiatives.get(organization_id, initiative_id)
        project = await unit.projects.get(initiative_id, project_id)
        if organization is None or initiative is None or project is None:
            raise ResourceNotFoundError("project")

    @staticmethod
    async def _validate_workflow_links(
        unit: UnitOfWork,
        project_id: uuid.UUID,
        workflow_run_id: uuid.UUID | None,
        workflow_step_attempt_id: uuid.UUID | None,
    ) -> None:
        if workflow_run_id is None:
            return
        workflow_run = await unit.workflow_runs.get(project_id, workflow_run_id)
        if workflow_run is None:
            raise ResourceNotFoundError("workflow run")
        if workflow_step_attempt_id is None:
            return
        for step in await unit.workflow_steps.list(workflow_run_id):
            attempts = await unit.workflow_step_attempts.list(step.id)
            if any(attempt.id == workflow_step_attempt_id for attempt in attempts):
                return
        raise ResourceNotFoundError("workflow step attempt")
