from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from devsembly import models
from devsembly.auth import AuthorizedPrincipal, CurrentPrincipal, authorize_request
from devsembly.database import SessionFactory
from devsembly.identity_schemas import (
    DelegationCreate,
    DelegationRead,
    MembershipCreate,
    MembershipRead,
    MembershipUpdate,
    PrincipalRead,
)

router = APIRouter(tags=["Identity and authorization"])
organization_router = APIRouter(
    prefix="/api/v1/organizations/{organization_id}",
    tags=["Identity and authorization"],
    dependencies=[Depends(authorize_request)],
)


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail={"code": "resource_not_found"})


@router.get("/api/v1/me", response_model=PrincipalRead)
async def get_current_principal(principal: CurrentPrincipal) -> PrincipalRead:
    return PrincipalRead(id=principal.principal_id, display_name=principal.display_name)


@organization_router.get("/memberships", response_model=list[MembershipRead])
async def list_memberships(
    organization_id: uuid.UUID, principal: AuthorizedPrincipal
) -> list[MembershipRead]:
    del principal
    async with SessionFactory() as session:
        records = await session.scalars(
            select(models.OrganizationMembership)
            .where(models.OrganizationMembership.organization_id == organization_id)
            .order_by(models.OrganizationMembership.created_at)
        )
        return [MembershipRead.model_validate(record) for record in records]


@organization_router.post(
    "/memberships", response_model=MembershipRead, status_code=status.HTTP_201_CREATED
)
async def create_membership(
    organization_id: uuid.UUID,
    payload: MembershipCreate,
    principal: AuthorizedPrincipal,
) -> MembershipRead:
    async with SessionFactory() as session, session.begin():
        if await session.get(models.Principal, payload.principal_id) is None:
            raise _not_found()
        membership = models.OrganizationMembership(
            organization_id=organization_id,
            principal_id=payload.principal_id,
            role=payload.role,
            status="active",
        )
        session.add(membership)
        session.add(
            models.AuditEvent(
                actor_type="human",
                actor_id=str(principal.principal_id),
                action="membership.created",
                object_type="organization",
                object_id=str(organization_id),
                payload={"principal_id": str(payload.principal_id), "role": payload.role},
            )
        )
        try:
            await session.flush()
        except IntegrityError as exc:
            raise HTTPException(status_code=409, detail={"code": "duplicate_membership"}) from exc
        return MembershipRead.model_validate(membership)


@organization_router.put("/memberships/{membership_id}", response_model=MembershipRead)
async def update_membership(
    organization_id: uuid.UUID,
    membership_id: uuid.UUID,
    payload: MembershipUpdate,
    principal: AuthorizedPrincipal,
) -> MembershipRead:
    async with SessionFactory() as session, session.begin():
        membership = await session.scalar(
            select(models.OrganizationMembership).where(
                models.OrganizationMembership.id == membership_id,
                models.OrganizationMembership.organization_id == organization_id,
            )
        )
        if membership is None:
            raise _not_found()
        removes_owner = membership.role == "owner" and (
            payload.role != "owner" or payload.status != "active"
        )
        if removes_owner:
            active_owner_count = await session.scalar(
                select(func.count())
                .select_from(models.OrganizationMembership)
                .where(
                    models.OrganizationMembership.organization_id == organization_id,
                    models.OrganizationMembership.role == "owner",
                    models.OrganizationMembership.status == "active",
                )
            )
            if active_owner_count == 1:
                raise HTTPException(status_code=409, detail={"code": "last_owner_required"})
        membership.role = payload.role
        membership.status = payload.status
        session.add(
            models.AuditEvent(
                actor_type="human",
                actor_id=str(principal.principal_id),
                action="membership.updated",
                object_type="membership",
                object_id=str(membership.id),
                payload={"role": payload.role, "status": payload.status},
            )
        )
        await session.flush()
        return MembershipRead.model_validate(membership)


@organization_router.post(
    "/delegations", response_model=DelegationRead, status_code=status.HTTP_201_CREATED
)
async def create_delegation(
    organization_id: uuid.UUID,
    payload: DelegationCreate,
    principal: AuthorizedPrincipal,
) -> DelegationRead:
    async with SessionFactory() as session, session.begin():
        membership = await session.scalar(
            select(models.OrganizationMembership).where(
                models.OrganizationMembership.organization_id == organization_id,
                models.OrganizationMembership.principal_id == payload.recipient_principal_id,
                models.OrganizationMembership.status == "active",
            )
        )
        if membership is None:
            raise _not_found()
        if payload.project_id is not None:
            project = await session.scalar(
                select(models.Project)
                .join(models.Initiative, models.Project.initiative_id == models.Initiative.id)
                .where(
                    models.Project.id == payload.project_id,
                    models.Initiative.organization_id == organization_id,
                )
            )
            if project is None:
                raise _not_found()
        delegation = models.AuthorizationDelegation(
            organization_id=organization_id,
            grantor_principal_id=principal.principal_id,
            recipient_principal_id=payload.recipient_principal_id,
            action=payload.action,
            project_id=payload.project_id,
            starts_at=payload.starts_at,
            expires_at=payload.expires_at,
        )
        session.add(delegation)
        session.add(
            models.AuditEvent(
                actor_type="human",
                actor_id=str(principal.principal_id),
                action="delegation.created",
                object_type="delegation",
                object_id=str(delegation.id),
                payload={
                    "recipient_principal_id": str(payload.recipient_principal_id),
                    "action": payload.action,
                    "project_id": (None if payload.project_id is None else str(payload.project_id)),
                    "expires_at": payload.expires_at.isoformat(),
                },
            )
        )
        await session.flush()
        return DelegationRead.model_validate(delegation)


@organization_router.post("/delegations/{delegation_id}/revoke", response_model=DelegationRead)
async def revoke_delegation(
    organization_id: uuid.UUID,
    delegation_id: uuid.UUID,
    principal: AuthorizedPrincipal,
) -> DelegationRead:
    async with SessionFactory() as session, session.begin():
        delegation = await session.scalar(
            select(models.AuthorizationDelegation).where(
                models.AuthorizationDelegation.id == delegation_id,
                models.AuthorizationDelegation.organization_id == organization_id,
            )
        )
        if delegation is None:
            raise _not_found()
        if delegation.revoked_at is None:
            delegation.revoked_at = datetime.now(UTC)
            session.add(
                models.AuditEvent(
                    actor_type="human",
                    actor_id=str(principal.principal_id),
                    action="delegation.revoked",
                    object_type="delegation",
                    object_id=str(delegation.id),
                    payload={},
                )
            )
            await session.flush()
        return DelegationRead.model_validate(delegation)
