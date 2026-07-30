from __future__ import annotations

import base64
import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from httpx import ASGITransport, AsyncClient

from devsembly.api import app
from devsembly.evidence_api import get_evidence_service
from devsembly.evidence_service import EvidenceService
from devsembly.evidence_storage import StoredObject
from devsembly.genesis_api import get_genesis_service
from devsembly.genesis_service import GenesisService
from tests.genesis_fakes import MemoryUnitOfWorkFactory

NOW = datetime(2026, 7, 30, 20, 0, tzinfo=UTC)


class MemoryEvidenceStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(self, object_key: str, content: bytes, content_type: str) -> StoredObject:
        del content_type
        self.objects[object_key] = content
        return StoredObject(
            object_key=object_key,
            sha256=hashlib.sha256(content).hexdigest(),
            size_bytes=len(content),
        )

    def get(self, object_key: str) -> bytes:
        return self.objects[object_key]

    def delete(self, object_key: str) -> None:
        self.objects.pop(object_key, None)


async def _create_project(client: AsyncClient, name: str) -> tuple[str, str, str]:
    organization = (
        await client.post("/api/v1/organizations", json={"name": f"{name} organization"})
    ).json()
    initiative = (
        await client.post(
            f"/api/v1/organizations/{organization['id']}/initiatives",
            json={"name": f"{name} initiative", "objective": "Preserve evidence."},
        )
    ).json()
    project = (
        await client.post(
            f"/api/v1/organizations/{organization['id']}/initiatives/{initiative['id']}/projects",
            json={"name": f"{name} project"},
        )
    ).json()
    return organization["id"], initiative["id"], project["id"]


async def test_evidence_ingestion_authorized_retrieval_and_retention() -> None:
    factory = MemoryUnitOfWorkFactory()
    storage = MemoryEvidenceStorage()
    app.dependency_overrides[get_genesis_service] = lambda: GenesisService(factory)
    app.dependency_overrides[get_evidence_service] = lambda: EvidenceService(
        factory, storage, clock=lambda: NOW
    )

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            organization_id, initiative_id, project_id = await _create_project(client, "primary")
            other_organization_id, other_initiative_id, other_project_id = await _create_project(
                client, "other"
            )
            path = (
                f"/api/v1/organizations/{organization_id}/initiatives/{initiative_id}"
                f"/projects/{project_id}/evidence"
            )
            content = b"ruff, mypy, and tests passed\n"
            created_response = await client.post(
                path,
                json={
                    "kind": "validation",
                    "name": "control-plane-ci.txt",
                    "content_type": "text/plain",
                    "content_base64": base64.b64encode(content).decode(),
                    "retention_class": "compliance",
                },
            )

            assert created_response.status_code == 201
            created = created_response.json()
            evidence_id = created["id"]
            assert created["project_id"] == project_id
            assert created["sha256"] == hashlib.sha256(content).hexdigest()
            assert created["size_bytes"] == len(content)
            assert created["retention_class"] == "compliance"
            assert datetime.fromisoformat(created["retain_until"]) == NOW + timedelta(days=2557)
            assert organization_id in created["object_key"]
            assert project_id in created["object_key"]
            assert created["sha256"] in created["object_key"]

            assert (await client.get(path)).json() == [created]
            assert (await client.get(f"{path}/{evidence_id}")).json() == created

            downloaded = await client.get(f"{path}/{evidence_id}/content")
            assert downloaded.status_code == 200
            assert downloaded.content == content
            assert downloaded.headers["content-type"] == "text/plain; charset=utf-8"
            assert downloaded.headers["x-content-sha256"] == created["sha256"]
            assert downloaded.headers["x-content-type-options"] == "nosniff"

            wrong_project_path = (
                f"/api/v1/organizations/{other_organization_id}/initiatives/{other_initiative_id}"
                f"/projects/{other_project_id}/evidence/{evidence_id}"
            )
            assert (await client.get(wrong_project_path)).status_code == 404

            missing_run = await client.post(
                path,
                json={
                    "kind": "workflow",
                    "name": "unknown-run.json",
                    "content_type": "application/json",
                    "content_base64": base64.b64encode(b"{}").decode(),
                    "workflow_run_id": str(uuid.uuid4()),
                },
            )
            assert missing_run.status_code == 404
            assert len(storage.objects) == 1
    finally:
        app.dependency_overrides.pop(get_genesis_service, None)
        app.dependency_overrides.pop(get_evidence_service, None)


async def test_retrieval_rejects_corrupted_object_content() -> None:
    factory = MemoryUnitOfWorkFactory()
    storage = MemoryEvidenceStorage()
    app.dependency_overrides[get_genesis_service] = lambda: GenesisService(factory)
    app.dependency_overrides[get_evidence_service] = lambda: EvidenceService(
        factory, storage, clock=lambda: NOW
    )

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            organization_id, initiative_id, project_id = await _create_project(client, "integrity")
            path = (
                f"/api/v1/organizations/{organization_id}/initiatives/{initiative_id}"
                f"/projects/{project_id}/evidence"
            )
            created = (
                await client.post(
                    path,
                    json={
                        "kind": "other",
                        "name": "artifact.bin",
                        "content_type": "application/octet-stream",
                        "content_base64": base64.b64encode(b"original").decode(),
                    },
                )
            ).json()
            storage.objects[created["object_key"]] = b"tampered"

            response = await client.get(f"{path}/{created['id']}/content")
            assert response.status_code == 502
            assert response.json()["code"] == "evidence_integrity_error"
    finally:
        app.dependency_overrides.pop(get_genesis_service, None)
        app.dependency_overrides.pop(get_evidence_service, None)
