# Control-plane MVP

This is the first executable Devsembly vertical slice. It accepts a structured product request, starts a durable Temporal workflow, creates a task packet, executes a safe mock builder, runs validation independently, performs an independent evidence review, and returns a terminal result.

## Start

```bash
docker compose up --build
```

Services:

- Factory API: `http://localhost:8000`
- API documentation: `http://localhost:8000/docs`
- Temporal UI: `http://localhost:8088`

## Submit a run

```bash
curl -X POST http://localhost:8000/runs \
  -H 'content-type: application/json' \
  -d '{
    "title": "Build fixture API",
    "objective": "Create and test a small API endpoint in the fixture repository.",
    "repository_url": "https://github.com/thebakermark/Devsembly",
    "validation_commands": ["python -c \"print(123)\""]
  }'
```

Copy the returned `workflow_id`, then retrieve the result:

```bash
curl http://localhost:8000/runs/<workflow_id>
```

## Current boundary

The worker intentionally uses a mock builder. The next implementation replaces it with provider adapters for OpenHands, Codex, and Claude Code, then adds repository checkout, disposable Docker workspaces, GitHub branch/PR creation, audit persistence, and bounded repair loops.
