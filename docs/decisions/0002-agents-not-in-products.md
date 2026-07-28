# ADR 0002: Development agents are not embedded in customer products

## Status

Accepted

## Decision

OpenClaw, Archon and coding agents are development-platform components. They will not be shipped as runtime dependencies of CompanyOS or other products unless a separate product decision explicitly authorizes it.

## Consequences

Development credentials, memories, prompts and orchestration services remain isolated from product production environments.
