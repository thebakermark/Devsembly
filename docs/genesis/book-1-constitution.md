# Book I — Constitution

**Status:** Binding
**Version:** 0.1.0

## Article 1 — Purpose, vision, and mission

Devsembly's purpose is to help humans engineer organizations that responsibly transform
intent into repeatable, evidence-backed outcomes.

Its vision is an open, provider-independent operating architecture in which people and
agents collaborate through explicit capability, authority, knowledge, and workflow
contracts.

Its mission is to deliver a secure, budget-aware software and organizational assembly
system that plans, executes, validates, records, and improves work under human control.

## Article 2 — Values

Devsembly values human agency, truth over appearance, evidence over assertion,
understanding over opaque speed, least privilege, provider independence, fiscal
responsibility, deliberate evolution, and learning from outcomes.

## Article 3 — Human authority

1. A human authority owns organizational intent, constitutional policy, delegated
   authority, risk acceptance, and budget ceilings.
2. Agents may act only within explicit, revocable delegation.
3. Human authority is final for production release, constitutional amendment,
   destructive or irreversible action, high-risk security change, material financial
   commitment, and exceptions to binding governance.
4. Emergency automation may perform only pre-authorized containment actions and must
   create immediate evidence and escalation.
5. Technical capability, provider access, or agent seniority never creates authority.

## Article 4 — Architecture governance

Accepted ADRs govern significant durable technical decisions. Architecture changes must
identify affected capabilities, dependencies, security, budget, data, migration,
rollback, and validation. Implementations that contradict accepted ADRs are defects
unless an approved superseding ADR exists.

Genesis v0.1 is governed by the accepted modular-monolith, workflow, identity, and
persistence ADRs. Future-state components remain proposed until separately accepted.

## Article 5 — Provider independence

Core policy and workflow logic must depend on capability contracts, not provider product
APIs. Providers must declare configuration, permissions, health, lifecycle, cost,
failure, observability, data handling, and exit behavior. Initial provider selection does
not grant permanent architectural privilege.

## Article 6 — Knowledge and memory governance

Authoritative knowledge must be identifiable, versioned, attributable, access-controlled,
and correctable. Material decisions and evidence require provenance and retention rules.
Generated summaries must link to their sources and disclose uncertainty. Agent memory is
not authority and must not silently override current canonical artifacts.

## Article 7 — Security governance

Security follows least privilege, separation of duties, defense in depth, secure
defaults, explicit trust boundaries, auditable access, bounded automation, and safe
failure. Secrets must not enter ordinary documentation, logs, prompts, or domain records.
High-risk actions require approval independent from the actor proposing or executing
them.

## Article 8 — Engineering governance

Every change must start from traceable intent, define acceptance criteria, respect domain
boundaries, include proportionate tests and documentation, and produce reproducible
validation evidence. No actor approves its own high-risk work. Known limitations and
failed checks must be disclosed.

## Article 9 — AI governance

1. Agents must identify their role, authority, tools, and data scope.
2. Agent output is a proposal or delegated action, not inherently a decision.
3. Material recommendations must preserve evidence, assumptions, uncertainty, and cost.
4. Agents must not fabricate completion, evidence, citations, access, or validation.
5. Agent behavior must be observable, interruptible, and bounded by retry and budget
   limits.
6. Independent review is required for high-risk agent-generated work.

## Article 10 — Organizational Genome authority

The Organizational Genome is the canonical model for organization structure,
capabilities, roles, authority, policy, process, knowledge, objectives, initiatives,
projects, budgets, assignments, and evidence. Reusable templates are versioned canonical
assets. Tenant operational records and overlays remain separate and cannot mutate the
canonical source.

## Article 11 — Fiscal governance

Budgets are policy boundaries, not reporting annotations. Plans must state recurring and
one-time cost, assumptions, forecast uncertainty, and lower-cost alternatives. A hard
limit cannot be exceeded without explicit authority. Genesis preserves the `$50/month`
reference constraint and must not imply that future-scale services are already funded.

## Article 12 — Amendment process

A constitutional amendment requires:

1. a traceable proposal stating the exact text and reason;
2. impact analysis across authority, security, knowledge, architecture, budget, and
   existing ADRs;
3. a public review period appropriate to the impact;
4. independent constitutional and security review;
5. explicit approval by the designated human constitutional authority;
6. a new library version, effective date, migration guidance, and immutable history.

An agent may draft or analyze an amendment but may not approve it.

## Constitutional test

A decision is constitutional only when it:

- advances the purpose and does not violate Book 0;
- preserves human final authority and clear delegation;
- keeps provider choice behind capability contracts;
- protects knowledge provenance, security, and auditability;
- respects approved budget and risk limits;
- supports explanation, interruption, recovery, and learning;
- creates no contradiction with a higher authority artifact.

Failure of any item blocks the decision unless this Constitution itself is amended.
