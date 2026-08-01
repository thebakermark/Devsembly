# Evidence API v1

**Status:** Current
**Version:** 1.0.0

The Evidence API ingests immutable project evidence into a MinIO-compatible object
store while PostgreSQL remains authoritative for identity, ownership, integrity, and
retention metadata. Every operation resolves the complete organization, initiative,
and project path and passes through the OIDC-backed authorization boundary.

## Operations

The project evidence base path is:

```text
/api/v1/organizations/{organization_id}/initiatives/{initiative_id}/projects/{project_id}/evidence
```

| Operation | Method and path | Required permission |
|---|---|---|
| Ingest evidence | `POST` on the base path | `write` |
| List project evidence | `GET` on the base path | `read` |
| Read evidence metadata | `GET /{evidence_id}` | `read` |
| Download verified content | `GET /{evidence_id}/content` | `read` |

A valid evidence identifier under the wrong parent path returns `404`. Authentication
does not grant project access by itself; an active organization role or bounded
delegation must authorize the operation.

## Ingestion contract

The request supplies:

- a kind: `validation`, `source_control`, `workflow`, or `other`;
- a display name and media type;
- Base64-encoded content, limited to 10 MiB after decoding;
- a retention class;
- optional workflow-run and workflow-step-attempt links.

Callers cannot choose the object key, digest, size, or retention deadline. The service
validates all parent and workflow links, computes SHA-256 and byte size, generates a
tenant- and project-scoped object key, writes the object, then commits its metadata and
`genesis.evidence.ingested` outbox event together. A database failure triggers
best-effort removal of the newly written object.

Evidence metadata is immutable after creation. Object retrieval recomputes SHA-256 and
size; a mismatch returns `502 evidence_integrity_error` and does not return the stored
bytes.

## Retention policy

Retention deadlines are based on the server clock:

| Class | Minimum retention | Intended use |
|---|---:|---|
| `transient` | 30 days | Reproducible short-lived diagnostics |
| `standard` | 365 days | Normal project and workflow evidence |
| `compliance` | 2,557 days | Seven-year governance and compliance evidence |
| `permanent` | No automatic deadline | Constitutional or enduring provenance |

The first API slice records and enforces retention metadata invariants. Automated
disposition, legal holds, storage-provider object locking, and restore evidence require
separate governed lifecycle work. No API in this version deletes evidence.

## Storage and failure boundary

PostgreSQL owns the evidence record and MinIO owns the immutable bytes. The object key
contains organization, project, digest, and evidence identifiers; caller filenames do
not enter storage paths. Retrieval responses use the recorded media type, force a
generated attachment filename, and include `X-Content-SHA256` plus
`X-Content-Type-Options: nosniff`.

The API container receives `DEVSEMBLY_MINIO_ENDPOINT`,
`DEVSEMBLY_EVIDENCE_BUCKET`, `MINIO_ROOT_USER`, and `MINIO_ROOT_PASSWORD` from
Compose. `DEVSEMBLY_MINIO_SECURE` controls TLS for an external compatible provider.
