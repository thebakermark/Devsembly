# Book IV — Operations Manual

**Status:** Binding baseline
**Version:** 0.1.0

This manual defines provider-independent operational requirements. Provider guides may
add commands, but cannot weaken these controls.

## Environments

Development, preview, staging, and production MUST use separate identities, secrets,
data, and network boundaries. Production credentials MUST NOT exist on development
hosts. Environment differences MUST be declared and minimized.

## Provisioning checklist

- [ ] Confirm the supported host and capacity.
- [ ] Record the approved infrastructure and recurring budget.
- [ ] Apply updates, time synchronization, firewall, and least-privilege access.
- [ ] Install pinned container and application dependencies.
- [ ] Configure provider endpoints through environment or secret references.
- [ ] Run bootstrap, repository, container, health, security, and restore checks.
- [ ] Preserve the immutable build revision and validation evidence.

Provisioning MUST be idempotent or clearly identify non-repeatable steps. It MUST NOT
embed credentials in scripts, images, logs, or documentation.

## Docker validation

Before release, operators MUST:

- render Compose configuration with required variables supplied safely;
- build the application image from a clean context;
- verify containers run as the intended user and expose only required ports;
- start dependencies, run migrations, and verify readiness;
- exercise graceful stop and restart;
- inspect health, resource use, logs, and persistent volumes;
- remove test resources without touching unrelated data.

## Deployment

Deployments MUST use an immutable reviewed revision, record actor and environment, apply
migrations through a controlled step, verify readiness and critical behavior, and
retain a tested rollback route. The same artifact SHOULD be promoted from preview to
staging to production.

## Secrets

Secrets MUST be stored in an approved secret provider, scoped to one purpose and
environment, injected by reference, redacted from evidence, and rotated after suspected
exposure. Secret inventories MUST record owner, scope, creation, rotation policy, and
revocation path without storing the secret value.

## Access control

Operators MUST use named identities, least privilege, strong authentication, and
time-bounded elevation. Shared owner accounts and direct production root access are
prohibited defaults. Access changes and emergency elevation MUST be audited and reviewed.

## Monitoring and alerting

Monitor service health, workflow queues, provider availability, database capacity,
storage integrity, errors, latency, authentication failures, policy denials, spend, and
backup freshness. Alerts MUST state severity, owner, expected response, and escalation.

## Logging and audit evidence

Logs MUST be structured, timestamped in UTC, correlated, retained by policy, and
sanitized. Audit evidence MUST record who or what acted, delegated authority, target,
decision, result, and relevant source references. Audit records MUST be append-only for
ordinary actors.

## Backup and restore

Backups MUST cover PostgreSQL, object metadata and objects, configuration, canonical
documents, and required provider exports. Encryption, retention, and off-host copies MUST
match risk. A backup is not accepted until a restore test proves data integrity and
records recovery point and recovery time.

Restore checklist:

- [ ] Declare incident scope and target recovery point.
- [ ] Protect current evidence before changing state.
- [ ] Restore into an isolated environment first.
- [ ] Verify schema, counts, checksums, ownership, and critical workflows.
- [ ] Obtain authority before replacing production state.
- [ ] Record result, gaps, and follow-up work.

## Incident response

1. Detect and create an incident record.
2. Classify severity, affected organizations, data, providers, and budgets.
3. Contain using pre-authorized reversible actions.
4. Preserve logs, events, revisions, and provider evidence.
5. Escalate to the accountable human.
6. Eradicate cause and recover through verified procedures.
7. Communicate known facts and uncertainty.
8. Review the incident and update controls, tests, and knowledge.

Agents MAY perform explicitly delegated containment. They MUST NOT conceal evidence,
declare legal conclusions, or take unapproved destructive action.

## Disaster recovery

Recovery plans MUST define service dependencies, authority, recovery point objective,
recovery time objective, provider exit data, alternate access, and communication.
Exercises SHOULD include loss of the Development Host, database, object store, workflow
provider, source-control provider, and primary operator access.

## Dependency failure

For a failed dependency:

1. stop unsafe retries and prevent duplicate side effects;
2. verify provider and network health;
3. classify transient, degraded, incompatible, or permanent failure;
4. preserve correlation and idempotency identifiers;
5. apply bounded retry, fallback, queue, or safe-stop policy;
6. escalate when time, cost, or risk limits are reached;
7. reconcile state after recovery.

## Provider replacement

Replacement requires compatible contracts, data export, configuration and permission
review, conformance evidence, cost comparison, migration rehearsal, cutover approval,
rollback, and post-cutover reconciliation. Provider-specific identifiers MUST be mapped
without becoming canonical domain identifiers.

## Cost and budget controls

Operators MUST track actual and forecast recurring cost by organization, project,
capability, and provider. Alerts SHOULD fire before hard limits. The Genesis reference
deployment targets `$50/month`; optional services must remain disabled or self-hosted
when they would exceed the approved limit. Increasing a budget requires explicit human
authority and a decision record.

## Change management

Every change MUST have a work item, risk and impact classification, validation plan,
rollback, owner, approval requirement, implementation window where applicable, and
post-change verification. Emergency changes receive the same evidence after containment.

## Release and rollback checklist

- [ ] Confirm approved revision, checks, migrations, and dependency versions.
- [ ] Confirm backup and rollback point.
- [ ] Confirm budget, capacity, security, and operator readiness.
- [ ] Deploy to the authorized environment.
- [ ] Verify health and critical acceptance behavior.
- [ ] Monitor the stabilization window.
- [ ] Roll back on defined failure thresholds.
- [ ] Record outcome, evidence, cost, and lessons.
