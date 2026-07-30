# Genesis local development

This guide starts the first runnable Devsembly control-plane slice defined by the Genesis reference implementation plan.

## Prerequisites

- Docker with Compose v2
- Git
- At least 4 GB of free memory for the complete local stack

## Start the stack

```bash
cp .env.example .env
```

Replace both example passwords in `.env`, then run:

```bash
docker compose up --build
```

Compose performs the following sequence:

1. starts PostgreSQL, Redis, MinIO, Temporal and the Temporal UI;
2. waits for PostgreSQL and Temporal health checks;
3. runs `alembic upgrade head` through the one-shot `migrate` service;
4. starts the FastAPI control plane and Temporal worker.

## Local endpoints

- API documentation: `http://127.0.0.1:8000/docs`
- Genesis workflow contract: [`../genesis/workflow-run-api.md`](../genesis/workflow-run-api.md)
- Liveness: `http://127.0.0.1:8000/health/live`
- Readiness: `http://127.0.0.1:8000/health/ready`
- Temporal UI: `http://127.0.0.1:8088`
- MinIO console: `http://127.0.0.1:9001`

All published ports bind to loopback by default and are not intended for direct internet exposure.

## Run validation

```bash
python -m pip install -e '.[dev]'
ruff check .
mypy devsembly
pytest
```

The project-scoped workflow API persists an `accepted` run before provider execution.
The earlier direct `POST /runs` Temporal start route is intentionally unavailable. A
later dispatcher will start only committed workflow runs.

## Migration workflow

After changing SQLAlchemy models:

```bash
alembic revision --autogenerate -m "describe the schema change"
alembic upgrade head
```

Review every generated migration before committing it. Production schema changes must not use `Base.metadata.create_all()`.

## Reset local state

The following command deletes local database, Redis and object-store data:

```bash
docker compose down -v
```

Do not use it when local evidence or workflow history must be preserved.
