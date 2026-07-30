from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


class PrincipalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    display_name: str


class MembershipCreate(BaseModel):
    principal_id: uuid.UUID
    role: Literal["owner", "administrator", "operator", "approver", "viewer"]


class MembershipUpdate(BaseModel):
    role: Literal["owner", "administrator", "operator", "approver", "viewer"]
    status: Literal["active", "suspended", "revoked"]


class MembershipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    principal_id: uuid.UUID
    role: str
    status: str
    created_at: datetime
    updated_at: datetime


class DelegationCreate(BaseModel):
    recipient_principal_id: uuid.UUID
    action: Literal["read", "write", "approve"]
    project_id: uuid.UUID | None = None
    starts_at: datetime
    expires_at: datetime

    @model_validator(mode="after")
    def validate_window(self) -> DelegationCreate:
        if self.starts_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("delegation times must include a timezone")
        if self.expires_at <= self.starts_at:
            raise ValueError("expires_at must be after starts_at")
        return self


class DelegationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    grantor_principal_id: uuid.UUID
    recipient_principal_id: uuid.UUID
    action: str
    project_id: uuid.UUID | None
    starts_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    created_at: datetime
    updated_at: datetime
