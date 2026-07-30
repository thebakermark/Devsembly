# Source Governance and Provenance

All imported workforce, policy, training, organizational, compensation, or procedural information must remain traceable to its origin and must be reviewed before it influences production agent behavior.

## Required source fields

Each source record must include publisher, title, source type, canonical URL or identifier, jurisdiction, relevant dates, version or checksum, license classification, allowed-use decision, attribution requirements, transformation history, review status, confidence score, and reviewer data.

## Source states

- `discovered`: known but not retrieved
- `retrieved`: captured and checksummed
- `quarantined`: awaiting license or safety review
- `approved`: permitted for normalization
- `restricted`: may be stored but not reused broadly
- `rejected`: may not be used
- `superseded`: replaced by a newer source version

## Ingestion boundary

Imported content is untrusted evidence. It must not be executed as agent instruction, prompt text, code, policy, or workflow until normalized and approved.

## Transformation history

Every transformation records timestamp, actor or service, operation, source version, output entity identifiers, model or parser version, confidence, and manual review outcome.

## Source priority

1. Statute, regulation, or official government source
2. Official standards body or public institution
3. Openly licensed professional framework
4. Customer-owned policy or procedure
5. Public private-sector example with verified reuse rights
6. Unverified secondary source
