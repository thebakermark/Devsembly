from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import cast

from devsembly.audit import current_audit_actor
from devsembly.domain import (
    ContextPackage,
    MemoryKind,
    MemorySensitivity,
    MemoryStatus,
    OutboxMessage,
    ProjectMemory,
    ProjectStateAssertionStatus,
    ProjectStateRevision,
)
from devsembly.errors import ResourceNotFoundError
from devsembly.unit_of_work import UnitOfWork

UnitOfWorkFactory = Callable[[], UnitOfWork]
Clock = Callable[[], datetime]

_TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]*", re.IGNORECASE)
_INJECTION_PATTERN = re.compile(
    r"(?:ignore|disregard) (?:all |any )?(?:previous|prior) instructions|"
    r"(?:system|developer) (?:prompt|message)|reveal (?:secrets|credentials)",
    re.IGNORECASE,
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode()).hexdigest()


def _estimate_tokens(value: str) -> int:
    return max(1, (len(value.encode("utf-8")) + 3) // 4)


def _keywords(value: str) -> set[str]:
    return {
        match.group(0).lower()
        for match in _TOKEN_PATTERN.finditer(value)
        if len(match.group(0)) > 2
    }


class MemoryContextService:
    def __init__(self, unit_of_work: UnitOfWorkFactory, clock: Clock = _utc_now) -> None:
        self._unit_of_work = unit_of_work
        self._clock = clock

    async def propose(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
        *,
        kind: MemoryKind,
        title: str,
        content: str,
        sensitivity: MemorySensitivity,
        source_revision_id: uuid.UUID | None,
        source_uri: str | None,
        assertion_status: ProjectStateAssertionStatus,
        confidence: Decimal,
        retention_until: datetime | None,
        proposed_by: str,
    ) -> ProjectMemory:
        now = self._clock()
        async with self._unit_of_work() as unit:
            await self._require_project(unit, organization_id, initiative_id, project_id)
            if source_revision_id is not None:
                revisions = await unit.project_state_revisions.list(project_id)
                if all(item.id != source_revision_id for item in revisions):
                    raise ResourceNotFoundError("project state revision")
            memory = ProjectMemory(
                id=uuid.uuid4(),
                project_id=project_id,
                kind=kind,
                title=title,
                content=content,
                content_sha256=hashlib.sha256(content.encode()).hexdigest(),
                status=MemoryStatus.PROPOSED,
                sensitivity=sensitivity,
                source_revision_id=source_revision_id,
                source_uri=source_uri,
                assertion_status=assertion_status,
                confidence=confidence,
                retention_until=retention_until,
                superseded_by=None,
                invalidated_at=None,
                proposed_by=proposed_by,
                decided_by=None,
                decision_reason=None,
                version=1,
                created_at=now,
                updated_at=now,
            )
            await unit.project_memories.add(memory)
            await unit.outbox.add(
                self._message(
                    now,
                    "genesis.memory.proposed",
                    memory.id,
                    organization_id,
                    initiative_id,
                    project_id,
                    {"memory_kind": kind.value, "sensitivity": sensitivity.value},
                )
            )
            await unit.commit()
            return memory

    async def list_memories(
        self, organization_id: uuid.UUID, initiative_id: uuid.UUID, project_id: uuid.UUID
    ) -> Sequence[ProjectMemory]:
        async with self._unit_of_work() as unit:
            await self._require_project(unit, organization_id, initiative_id, project_id)
            return await unit.project_memories.list(project_id)

    async def resolve(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
        memory_id: uuid.UUID,
        expected_version: int,
        *,
        status: MemoryStatus,
        decided_by: str,
        reason: str,
    ) -> ProjectMemory:
        now = self._clock()
        async with self._unit_of_work() as unit:
            await self._require_project(unit, organization_id, initiative_id, project_id)
            resolved = await unit.project_memories.resolve(
                project_id,
                memory_id,
                expected_version,
                status=status.value,
                decided_by=decided_by,
                decision_reason=reason,
                decided_at=now,
            )
            if resolved is None:
                raise ResourceNotFoundError("project memory")
            await unit.outbox.add(
                self._message(
                    now,
                    f"genesis.memory.{status.value}",
                    memory_id,
                    organization_id,
                    initiative_id,
                    project_id,
                    {"version": resolved.version},
                )
            )
            await unit.commit()
            return resolved

    async def build_context(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
        *,
        task: str,
        token_budget: int,
        created_by: str,
    ) -> ContextPackage:
        now = self._clock()
        async with self._unit_of_work() as unit:
            await self._require_project(unit, organization_id, initiative_id, project_id)
            revision = await unit.project_state_revisions.latest(project_id)
            if revision is None:
                raise ResourceNotFoundError("project state")
            memories = await unit.project_memories.list(project_id)
            candidates, omissions = self._candidates(revision, memories, task, now)
            selected: list[dict[str, object]] = []
            tokens_used = 0
            for candidate in candidates:
                cost = cast(int, candidate["token_estimate"])
                if tokens_used + cost > token_budget:
                    omissions.append({"id": candidate["id"], "reason": "token_budget"})
                    continue
                selected.append(candidate)
                tokens_used += cost
            sorted_omissions = sorted(
                omissions, key=lambda item: (str(item["id"]), str(item["reason"]))
            )
            manifest = {
                "source_revision_id": str(revision.id),
                "source_sha256": revision.state_sha256,
                "task": task,
                "token_budget": token_budget,
                "tokens_used": tokens_used,
                "items": selected,
                "omissions": sorted_omissions,
            }
            package = ContextPackage(
                id=uuid.uuid4(),
                project_id=project_id,
                source_revision_id=revision.id,
                task=task,
                token_budget=token_budget,
                tokens_used=tokens_used,
                items=tuple(selected),
                omissions=tuple(sorted_omissions),
                manifest_sha256=_sha256(manifest),
                invalidated_at=None,
                created_by=created_by,
                created_at=now,
            )
            invalidated = await unit.context_packages.invalidate_for_source_change(
                project_id, revision.id, now
            )
            await unit.context_packages.add(package)
            await unit.outbox.add(
                self._message(
                    now,
                    "genesis.context.built",
                    package.id,
                    organization_id,
                    initiative_id,
                    project_id,
                    {
                        "source_revision_id": str(revision.id),
                        "token_budget": token_budget,
                        "tokens_used": tokens_used,
                        "included": len(selected),
                        "omitted": len(omissions),
                        "invalidated_packages": invalidated,
                        "manifest_sha256": package.manifest_sha256,
                    },
                )
            )
            await unit.commit()
            return package

    async def get_context(
        self,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
        package_id: uuid.UUID,
    ) -> ContextPackage:
        async with self._unit_of_work() as unit:
            await self._require_project(unit, organization_id, initiative_id, project_id)
            package = await unit.context_packages.get(project_id, package_id)
            if package is None:
                raise ResourceNotFoundError("context package")
            return package

    @staticmethod
    def _candidates(
        revision: ProjectStateRevision,
        memories: Sequence[ProjectMemory],
        task: str,
        now: datetime,
    ) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        task_terms = _keywords(task)
        candidates: list[dict[str, object]] = []
        omissions: list[dict[str, object]] = []
        for section, value in sorted(revision.state.items()):
            content = _canonical_json(value)
            candidate_id = f"state:{section}"
            if _INJECTION_PATTERN.search(content):
                omissions.append({"id": candidate_id, "reason": "prompt_injection_risk"})
                continue
            overlap = len(task_terms & _keywords(f"{section} {content}"))
            candidate = {
                "id": candidate_id,
                "kind": "semantic",
                "title": section.replace("_", " ").title(),
                "content": content,
                "provenance": {
                    "provider": revision.source_provider,
                    "kind": revision.source_kind,
                    "uri": revision.source_uri,
                    "observed_at": revision.observed_at.isoformat(),
                    "source_revision_id": str(revision.id),
                },
                "authority": "canonical_project_state",
                "assertion_status": revision.assertion_status.value,
                "confidence": str(revision.confidence),
                "freshness": "current",
                "sensitivity": "internal",
                "selection_reason": f"canonical source; task term overlap={overlap}",
                "score": 1000 + overlap,
                "token_estimate": _estimate_tokens(content),
            }
            candidates.append(candidate)
        for memory in memories:
            candidate_id = f"memory:{memory.id}"
            reason: str | None = None
            if memory.status is not MemoryStatus.APPROVED:
                reason = "not_approved"
            elif memory.invalidated_at is not None or memory.superseded_by is not None:
                reason = "invalidated_or_superseded"
            elif memory.retention_until is not None and memory.retention_until <= now:
                reason = "retention_expired"
            elif memory.sensitivity in {
                MemorySensitivity.CONFIDENTIAL,
                MemorySensitivity.RESTRICTED,
            }:
                reason = "sensitivity_policy"
            elif memory.assertion_status is ProjectStateAssertionStatus.DISPUTED:
                reason = "disputed"
            elif _INJECTION_PATTERN.search(memory.content):
                reason = "prompt_injection_risk"
            if reason is not None:
                omissions.append({"id": candidate_id, "reason": reason})
                continue
            overlap = len(task_terms & _keywords(f"{memory.title} {memory.content}"))
            candidates.append(
                {
                    "id": candidate_id,
                    "kind": memory.kind.value,
                    "title": memory.title,
                    "content": memory.content,
                    "provenance": {
                        "provider": "memoryos",
                        "kind": "approved_memory",
                        "uri": memory.source_uri,
                        "source_revision_id": (
                            None
                            if memory.source_revision_id is None
                            else str(memory.source_revision_id)
                        ),
                    },
                    "authority": "approved_memory",
                    "assertion_status": memory.assertion_status.value,
                    "confidence": str(memory.confidence),
                    "freshness": "current",
                    "sensitivity": memory.sensitivity.value,
                    "selection_reason": f"approved memory; task term overlap={overlap}",
                    "score": 500 + overlap,
                    "token_estimate": _estimate_tokens(memory.content),
                }
            )
        candidates.sort(key=lambda item: (-cast(int, item["score"]), str(item["id"])))
        for candidate in candidates:
            candidate.pop("score")
        return candidates, omissions

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

    @staticmethod
    def _message(
        now: datetime,
        topic: str,
        aggregate_id: uuid.UUID,
        organization_id: uuid.UUID,
        initiative_id: uuid.UUID,
        project_id: uuid.UUID,
        extra: dict[str, object],
    ) -> OutboxMessage:
        actor_type, actor_id = current_audit_actor()
        return OutboxMessage(
            id=uuid.uuid4(),
            occurred_at=now,
            topic=topic,
            aggregate_id=str(aggregate_id),
            payload={
                "organization_id": str(organization_id),
                "initiative_id": str(initiative_id),
                "project_id": str(project_id),
                **extra,
            },
            actor_type=actor_type,
            actor_id=actor_id,
        )
