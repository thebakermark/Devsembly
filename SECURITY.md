# Security Policy

Do not post vulnerabilities, secrets, production access details, or sensitive data in public issues.

## Reporting a vulnerability

Use GitHub private vulnerability reporting when enabled, or contact the repository owner privately. Include the affected component, reproduction steps, potential impact, and suggested mitigation. Do not include live secrets or personal data beyond what is necessary to reproduce the issue safely.

## Development rules

- Never commit credentials, API keys, tokens, private keys, or production data.
- Use GitHub Actions secrets or environment-scoped secrets with least-privilege identities.
- Never copy production customer data into development.
- Review all dependencies and third-party agent skills before use.
- Treat agent-created pull requests as untrusted until reviewed and validated.
- Critical and high-confidence exploitable findings block release.

## Supported versions

Until Devsembly reaches a stable release, security fixes are applied to the default branch and latest published release candidate.

A private vulnerability-reporting channel will be configured before public release.
