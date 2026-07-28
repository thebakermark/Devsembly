# Backups and recovery

## Back up

- Git repositories and configuration
- PostgreSQL databases
- object storage
- workflow definitions
- agent configuration, excluding unencrypted secrets
- Coolify configuration
- monitoring configuration

## Rules

- Store backups off the source VM.
- Encrypt backups in transit and at rest.
- Use daily, weekly, and monthly retention tiers.
- Test restoration on a schedule.
- Document recovery-time and recovery-point objectives.

## Recovery test

A backup is not considered valid until a clean environment can restore it and pass smoke tests.
