# Genesis Ontologies

**Status:** Binding concept map; intentionally bounded
**Version:** 0.1.0

The canonical organization concepts are defined in
[Book VI](../book-6-organizational-genome.md) and the existing
[Organizational Genome ontology](../../architecture/organizational-genome/ontology.md).
The [core relationships](core-relationships.md) connect those concepts to Kernel,
provider, workflow, budget, memory, decision, and evidence contracts.

## Rules

- Ontology terms clarify domain meaning; they do not grant runtime permission.
- Relationships use stable identifiers and effective versions.
- Canonical reusable concepts remain separate from tenant operational instances.
- Provenance and authority are explicit relationships, not inferred from text similarity.
- A dedicated graph database is not required; relational links are sufficient for
  Genesis.
- New concepts require a demonstrated use case, owner, definition, invariants, and
  compatibility review.
