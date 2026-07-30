from __future__ import annotations

from devsembly.evidence_storage import MinioEvidenceStorage


class FakeMinio:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def put_object(self, *args: object, **kwargs: object) -> None:
        self.calls.append((*args, kwargs))


def test_minio_evidence_storage_preserves_object_metadata() -> None:
    client = FakeMinio()
    storage = MinioEvidenceStorage(client, "evidence")  # type: ignore[arg-type]

    stored = storage.put("projects/a/log.txt", b"validation passed\n", "text/plain")

    assert stored.object_key == "projects/a/log.txt"
    assert stored.size_bytes == 18
    assert stored.sha256 == "16e3bbb50d11d6de04878dd016227f280125582b449c85f8c4ec00770697b6ee"
    assert client.calls[0][0:2] == ("evidence", "projects/a/log.txt")
