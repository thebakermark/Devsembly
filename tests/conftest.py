from __future__ import annotations

import uuid

import pytest

from devsembly.api import app
from devsembly.auth import (
    IdentityManager,
    PrincipalContext,
    authorize_request,
    get_identity_manager,
    internal_control_authorized,
)

TEST_PRINCIPAL = PrincipalContext(
    principal_id=uuid.UUID("00000000-0000-4000-8000-000000000001"),
    issuer="https://issuer.test",
    subject="test-user",
    display_name="Test User",
)


class MemoryIdentityManager(IdentityManager):
    def __init__(self) -> None:
        self.organization_ids: set[uuid.UUID] = set()

    async def bootstrap_organization_owner(
        self, organization_id: uuid.UUID, principal: PrincipalContext
    ) -> None:
        assert principal == TEST_PRINCIPAL
        self.organization_ids.add(organization_id)

    async def authorized_organization_ids(self, principal: PrincipalContext) -> set[uuid.UUID]:
        assert principal == TEST_PRINCIPAL
        return set(self.organization_ids)


@pytest.fixture(autouse=True)
def authorize_existing_api_tests() -> None:
    identities = MemoryIdentityManager()
    app.dependency_overrides[authorize_request] = lambda: TEST_PRINCIPAL
    app.dependency_overrides[get_identity_manager] = lambda: identities
    app.dependency_overrides[internal_control_authorized] = lambda: None
    yield
    app.dependency_overrides.clear()
