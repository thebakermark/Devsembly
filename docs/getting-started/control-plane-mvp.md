# Control-plane MVP

This is the first executable Devsembly delivery loop. It accepts a structured product request, starts a durable Temporal workflow, creates a traceable issue and isolated branch, invokes the configured coding provider, runs deterministic validation and bounded repair, publishes a draft pull request, performs an independent evidence review, and proposes the completed episode to governed project memory.

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
curl -X POST \
  http://localhost:8000/api/v1/organizations/<organization-id>/initiatives/<initiative-id>/projects/<project-id>/workflow-runs \
  -H 'content-type: application/json' \
  -d '{
    "workflow_kind": "software_delivery",
    "idempotency_key": "fixture-hello-v1",
    "input_payload": {
      "title": "Build fixture API",
      "objective": "Create and test a small API endpoint in the fixture repository.",
      "repository_url": "https://github.com/thebakermark/devsembly-factory-fixture",
      "base_branch": "main",
      "allowed_paths": ["src/", "tests/", "README.md"],
      "validation_commands": ["pytest -q"],
      "max_repair_attempts": 2
    },
    "steps": [
      {"key": "intake", "name": "Create traceable work item"},
      {"key": "implement", "name": "Implement in isolated workspace"},
      {"key": "validate", "name": "Validate and repair"},
      {"key": "publish", "name": "Publish draft pull request"},
      {"key": "remember", "name": "Propose outcome to project memory"}
    ]
  }'
```

Copy `run.id` from the response, then retrieve the persisted run and step evidence:

```bash
curl \
  http://localhost:8000/api/v1/organizations/<organization-id>/initiatives/<initiative-id>/projects/<project-id>/workflow-runs/<run-id>
```

## Completion boundary

The run is complete only when its traceable issue exists before implementation, changes remain within the declared paths, every configured validation command passes, a draft pull request exists, independent review accepts the evidence, and a MemoryOS episodic proposal records the outcome. The canonical organization, initiative, and project IDs come from the governed API path rather than caller-controlled workflow input. The proposal remains governed and does not silently become approved semantic truth.

The source-control provider is idempotent at the work-item boundary by embedding the stable run identifier in the issue. Pull requests remain draft and are never merged by this workflow.

Use a disposable fixture repository for the first development-host demonstration. Production deployment and merge remain outside this milestone.
