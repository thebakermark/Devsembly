# ADR 0013 — Human Authority Is Final

- **Status:** Accepted
- **Date:** 2026-07-30
- **Decision owners:** Devsembly Architecture
- **Applies to:** All automation and governance

## Context

Agents and workflows can recommend, execute, validate, and coordinate at high speed.
Ability to act does not establish legitimate authority, acceptable risk, organizational
purpose, or accountability. Unbounded automation can amplify error and obscure
responsibility.

## Decision

Humans define intent, policy, delegation, budgets, risk acceptance, and constitutional
change, and retain final authority. Agents act only within explicit, revocable
delegation. Production release, constitutional change, destructive or irreversible
action, material financial commitment, high-risk security change, and exceptions to
binding governance require explicit authorized human decision.

No agent may approve its own high-risk work or enlarge its authority. Emergency
automation is limited to pre-authorized containment and immediate escalation.

## Consequences

Accountability and intervention remain clear. Some workflows pause for approval and
cannot be fully autonomous. Interfaces and runbooks must make approvals timely,
informed, and auditable.

## Alternatives considered

- **Full agent autonomy:** rejected because technical capability cannot create
  legitimacy or accountability.
- **Human review of every action:** rejected as unnecessary; bounded low-risk delegation
  is allowed.
- **Provider permissions define authority:** rejected because access is not governance.

## Security impact

High-risk actions require separation of duties, strong human identity, explicit scope,
fresh approval, and immutable audit evidence. Break-glass access is time-bounded,
monitored, and reviewed.

## Budget impact

Agents cannot change limits or create unapproved commitments. Approval workflows add
human time but prevent uncontrolled cost. Low-risk work may operate within pre-approved
budgets.

## Implementation constraints

- Delegations identify grantor, recipient, action, scope, limit, duration, conditions,
  and revocation.
- Policy enforcement fails closed for missing high-risk authority.
- Approval records bind exact action, revision, environment, and cost where applicable.
- Agents and service identities remain distinct from human principals.

## Validation criteria

Tests prove unauthorized actions are denied, delegated low-risk work succeeds only
within scope, high-risk workflows pause for the correct human, approvals cannot be
reused outside their bound target, and all results are audited.

## Review triggers

Review when law, safety, customer contracts, incident learning, or new automation changes
the required approval boundary. The principle of final human constitutional authority
can change only through constitutional amendment.

## References

- [Book I — Constitution](../../genesis/book-1-constitution.md)
- [Book V — Agent Handbook](../../genesis/book-5-agent-handbook.md)
- [Trust model](../../security/trust-model.md)
