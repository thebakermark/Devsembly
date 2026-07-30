from __future__ import annotations

import io

from devsembly.evidence_storage import MinioEvidenceStorage


class FakeMinio:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.objects: dict[str, bytes] = {}

    def put_object(self, *args: object, **kwargs: object) -> None:
        self.calls.append((*args, kwargs))
        object_key = str(args[1])
        stream = args[2]
        assert isinstance(stream, io.BytesIO)
        self.objects[object_key] = stream.read()

    def get_object(self, bucket: str, object_key: str) -> FakeResponse:
        del bucket
        return FakeResponse(self.objects[object_key])

    def remove_object(self, bucket: str, object_key: str) -> None:
        del bucket
        self.objects.pop(object_key)


class FakeResponse(io.BytesIO):
    def release_conn(self) -> None:
        pass


def test_minio_evidence_storage_preserves_object_metadata() -> None:
    client = FakeMinio()
    storage = MinioEvidenceStorage(client, "evidence")  # type: ignore[arg-type]

    stored = storage.put("projects/a/log.txt", b"validation passed\n", "text/plain")

    assert stored.object_key == "projects/a/log.txt"
    assert stored.size_bytes == 18
    assert stored.sha256 == "16e3bbb50d11d6de04878dd016227f280125582b449c85f8c4ec00770697b6ee"
    assert client.calls[0][0:2] == ("evidence", "projects/a/log.txt")
    assert storage.get("projects/a/log.txt") == b"validation passed\n"

    storage.delete("projects/a/log.txt")
    assert client.objects == {}
