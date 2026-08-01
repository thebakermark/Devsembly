# Plugin Model

**Status:** Proposed; dynamic loading and marketplace deferred
**Version:** 0.1.0

## Purpose

A plugin packages one or more provider adapters or platform extensions with explicit
contracts, permissions, configuration, lifecycle, provenance, and conformance evidence.

## Manifest

A manifest declares plugin ID, publisher, semantic version, license, supported Kernel
range, capabilities and contract versions, entry points, configuration schemas, required
permissions, network and data access, secrets, migrations, health, events, dependencies,
resource limits, support, signing, and uninstall behavior.

## Trust and isolation

Plugins are untrusted until reviewed. Installation requires provenance and signature
verification, permission review, compatibility validation, and conformance tests.
Runtime isolation should restrict filesystem, network, process, credentials, and data
scope according to the manifest. A plugin cannot grant itself more access.

## Lifecycle

`discovered -> reviewed -> installed -> configured -> enabled -> degraded -> disabled -> uninstalled`

Upgrade supports compatibility checks, migration, rollback, and side-by-side validation
where practical. Uninstall identifies retained data and revokes credentials.

## Genesis posture

Genesis uses statically installed adapters and configuration. It does not dynamically
execute third-party plugins or operate a marketplace. The manifest and schema provide a
future-compatible design target.

## Validation

Tests cover invalid manifest, incompatible Kernel version, undeclared permission,
signature failure, dependency conflict, lifecycle transitions, migration rollback,
disable, uninstall, and retained-data disclosure.
