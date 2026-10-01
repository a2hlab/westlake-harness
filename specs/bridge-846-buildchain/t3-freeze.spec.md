spec: task
name: "Land and freeze the bridge build chain"
inherits: project
depends: [t2-rebuild]
---
## Intent
Put the chain in the repository and the freeze registry so the bridge can be rebuilt and changed one function at a time.
## Boundaries
### Allowed
- knowledge/toolchains/bridge-846/**
- knowledge/frozen/**
- benchmark/2026-10-01-bridge-846-buildchain/**
- tools/spec-checks/tests/bridge_846_buildchain.rs
### Forbidden
- Device commands; deploying a rebuilt bridge
## Acceptance Criteria
Scenario: Chain reproducible from the repository
  Test: bridge846_reproduce
  Given only the repository recipe and the hw248 toolchain path
  When the reproduce script runs twice in fresh directories
  Then both outputs are identical to each other and match the t2 comparison result
Scenario: Freeze proposal complete
  Test: bridge846_freeze
  Given the comparison and its exception table
  When the freeze proposal is validated by check_frozen.py
  Then it names sources, patches, toolchain and build script by hash with zero violations
Scenario: Non-reproducible output refuses freezing
  Test: bridge846_freeze_reject
  Given two reproduce runs whose outputs differ or a recipe input whose hash does not match
  When the freeze proposal is validated
  Then validation fails and no frozen entry is written
