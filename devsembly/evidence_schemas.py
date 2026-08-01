from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import (
    Base64Bytes,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    model_validator,
)

from devsembly.domain import EvidenceKind, EvidenceRetentionClass


def _strip(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


EvidenceName = Annotated[
    str,
    BeforeValidator(_strip),
    Field(min_length=1, max_length=250),
]
ContentType = Annotated[
    str,
    BeforeValidator(_strip),
    Field(min_length=1, max_length=200, pattern=r"^[^\x00-\x20\x7f]+/[^\x00-\x20\x7f]+$"),
]


class EvidenceCreate(BaseModel):
    kind: EvidenceKind
    name: EvidenceName
    content_type: ContentType
    content_base64: Annotated[Base64Bytes, Field(max_length=10 * 1024 * 1024)]
    retention_class: EvidenceRetentionClass = EvidenceRetentionClass.STANDARD
    workflow_run_id: uuid.UUID | None = None
    workflow_step_attempt_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def attempt_requires_run(self) -> EvidenceCreate:
        if self.workflow_step_attempt_id is not None and self.workflow_run_id is None:
            raise ValueError("workflow_step_attempt_id requires workflow_run_id")
        return self


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    workflow_run_id: uuid.UUID | None
    workflow_step_attempt_id: uuid.UUID | None
    kind: EvidenceKind
    name: str
    content_type: str
    object_key: str
    sha256: str
    size_bytes: int
    retention_class: EvidenceRetentionClass
    retain_until: datetime | None
    created_at: datetime
