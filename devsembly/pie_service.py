from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from decimal import Decimal

from devsembly.audit import current_audit_actor
from devsembly.domain import (
    OutboxMessage,
    ProjectStateAssertionStatus,
    ProjectStateRevision,
)
from devsembly.errors import IdempotencyConflictError, ResourceNotFoundError, StaleVersionError
from devsembly.unit_of_work import UnitOfWork

UnitOfWorkFactory = Callable[[], UnitOfWork]
Clock = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


class ProjectIntelligenceService:
    def __init__(self, unit_of_work: UnitOfWorkFactory, clock: Clock = _utc_now) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    async def latest(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> ProjectStateRevision:
        async with self._unit_of_work() as unit:
            await self._require_project(unit, organization_id, initiative_id, project_id)
            revision = await unit.project_state_revisions.latest(project_id)
            if revision is None:
                raise ResourceNotFoundError("project state")
            return revision

    async def get_version(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
        version: int,
    ) -> ProjectStateRevision:
        async with self._unit_of_work() as unit:
            await self._require_project(unit, organization_id, initiative_id, project_id)
            revision = await unit.project_state_revisions.get_version(project_id, version)
            if revision is None:
                raise ResourceNotFoundError("project state revision")
            return revision

    async def list_revisions(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> Sequence[ProjectStateRevision]:
        async with self._unit_of_work() as unit:
            await self._require_project(unit, organization_id, initiative_id, project_id)
            return await unit.project_state_revisions.list(project_id)

    async def reconcile(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
        *,
        expected_version: int,
        idempotency_key: str,
        schema_version: str,
        state: dict[str, object],
        source_provider: str,
        source_kind: str,
        source_event_id: str | None,
        source_uri: str | None,
        source_occurred_at: datetime | None,
        assertion_status: ProjectStateAssertionStatus,
        confidence: Decimal,
        confidence_explanation: str,
    ) -> ProjectStateRevision:
        now = self._clock()
        state_sha256 = hashlib.sha256(_canonical_json(state)).hexdigest()
        request_fingerprint = hashlib.sha256(
            _canonical_json(
                {
                    "schema_version": schema_version,
                    "state_sha256": state_sha256,
                    "source_provider": source_provider,
                    "source_kind": source_kind,
                    "source_event_id": source_event_id,
                    "source_uri": source_uri,
                    "source_occurred_at": (
                        None if source_occurred_at is None else source_occurred_at.isoformat()
                    ),
                    "assertion_status": assertion_status.value,
                    "confidence": str(confidence),
                    "confidence_explanation": confidence_explanation,
                }
            )
        ).hexdigest()

        async with self._unit_of_work() as unit:
            await self._require_project(unit, organization_id, initiative_id, project_id)
            existing = await unit.project_state_revisions.get_by_idempotency_key(
                project_id, idempotency_key
            )
            if existing is not None:
                if existing.request_fingerprint != request_fingerprint:
                    raise IdempotencyConflictError(idempotency_key)
                return existing

            latest = await unit.project_state_revisions.latest(project_id)
            current_version = 0 if latest is None else latest.version
            if current_version != expected_version:
                raise StaleVersionError("project state", expected_version)

            revision = ProjectStateRevision(
                id=uuid.uuid4(),
                project_id=project_id,
                version=current_version + 1,
                parent_revision_id=None if latest is None else latest.id,
                schema_version=schema_version,
                state=state,
                state_sha256=state_sha256,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
                source_provider=source_provider,
                source_kind=source_kind,
                source_event_id=source_event_id,
                source_uri=source_uri,
                source_occurred_at=source_occurred_at,
                observed_at=now,
                assertion_status=assertion_status,
                confidence=confidence,
                confidence_explanation=confidence_explanation,
                created_at=now,
            )
            await unit.project_state_revisions.add(revision)
            actor_type, actor_id = current_audit_actor()
            await unit.outbox.add(
                OutboxMessage(
                    id=uuid.uuid4(),
                    occurred_at=now,
                    topic="genesis.project-intelligence.state-reconciled",
                    aggregate_id=str(revision.id),
                    payload={
                        "organization_id": str(organization_id),
                        "initiative_id": str(initiative_id),
                        "project_id": str(project_id),
                        "project_state_revision_id": str(revision.id),
                        "version": revision.version,
                        "schema_version": schema_version,
                        "state_sha256": state_sha256,
                        "source_provider": source_provider,
                        "source_kind": source_kind,
                        "assertion_status": assertion_status.value,
                        "confidence": str(confidence),
                    },
                    actor_type=actor_type,
                    actor_id=actor_id,
                )
            )
            await unit.commit()
            return revision

    @staticmethod
    async def _require_project(
        unit: UnitOfWork,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> None:
        initiative = await unit.initiatives.get(organization_id, initiative_id)
        if initiative is None:
            raise ResourceNotFoundError("initiative")
        project = await unit.projects.get(initiative_id, project_id)
        if project is None:
            raise ResourceNotFoundError("project")
