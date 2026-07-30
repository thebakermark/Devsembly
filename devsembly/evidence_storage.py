from __future__ import annotations

import hashlib
import io
import os
from dataclasses import dataclass
from typing import Protocol

from minio import Minio


@dataclass(frozen=True, slots=True)
class StoredObject:
    object_key: str
    sha256: str
    size_bytes: int


class EvidenceStorage(Protocol):
    def put(self, object_key: str, content: bytes, content_type: str) -> StoredObject: ...
    def get(self, object_key: str) -> bytes: ...
    def delete(self, object_key: str) -> None: ...


class MinioEvidenceStorage:
    """Small provider adapter; PostgreSQL remains authoritative for evidence metadata."""

    def __init__(self, client: Minio, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    @classmethod
    def from_environment(cls) -> MinioEvidenceStorage:
        endpoint = os.getenv("DEVSEMBLY_MINIO_ENDPOINT", "localhost:9000")
        access_key = os.getenv("MINIO_ROOT_USER", "devsembly")
        secret_key = os.getenv("MINIO_ROOT_PASSWORD", "replace-with-another-long-random-password")
        bucket = os.getenv("DEVSEMBLY_EVIDENCE_BUCKET", "devsembly-evidence")
        client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=os.getenv("DEVSEMBLY_MINIO_SECURE", "false").lower() == "true",
        )
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
        return cls(client, bucket)

    def put(self, object_key: str, content: bytes, content_type: str) -> StoredObject:
        digest = hashlib.sha256(content).hexdigest()
        self._client.put_object(
            self._bucket, object_key, io.BytesIO(content), len(content), content_type=content_type
        )
        return StoredObject(object_key=object_key, sha256=digest, size_bytes=len(content))

    def get(self, object_key: str) -> bytes:
        response = self._client.get_object(self._bucket, object_key)
        try:
            return bytes(response.read())
        finally:
            response.close()
            response.release_conn()

    def delete(self, object_key: str) -> None:
        self._client.remove_object(self._bucket, object_key)
