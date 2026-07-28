# Configure OpenClaw and agents

OpenClaw is used only for the development factory, not embedded in CompanyOS or other customer products.

## Persistent lead agents

1. Chief Orchestrator
2. Product Director
3. Architecture Director
4. Engineering Director
5. Quality Director
6. Security Director
7. Platform Director
8. Documentation Director

## Required controls

- Dedicated Linux service account
- Development-only secrets
- Repository-scoped GitHub token or app access
- No production database access
- No production root SSH access
- No direct merge permission for protected branches
- Full audit logging
- Retry limits and escalation on repeated failure

## Task execution

Each task receives:

- a GitHub issue
- acceptance criteria
- an isolated Git worktree
- relevant documentation
- model and tool limits
- required validation steps
- a completion report
