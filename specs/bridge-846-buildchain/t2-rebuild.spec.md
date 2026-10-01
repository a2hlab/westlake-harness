spec: task
name: "Rebuild the bridge and compare function by function"
inherits: project
depends: [t1-inventory]
---
## Intent
Build the bridge from the pinned sources with the identified toolchain and measure exactly how the rebuild differs from 84695d62.
## Boundaries
### Allowed
- benchmark/2026-10-01-bridge-846-buildchain/**
- knowledge/toolchains/bridge-846/**
- tools/spec-checks/tests/bridge_846_buildchain.rs
### Forbidden
- Device commands; replacing 84695d62 anywhere
## Acceptance Criteria
Scenario: Rebuild produced
  Test: bridge846_rebuild
  Given the t1 inventory and the pinned toolchain
  When the build script runs in a fresh directory
  Then it produces liboh_adapter_bridge.so and a receipt with every input hash, the exact command lines and the output hash
Scenario: Per-function comparison
  Test: bridge846_compare
  Given the rebuild and 84695d62
  When the comparison tool normalises relocations and addresses
  Then every function is classified identical, different or missing, and each difference cites the source cause or is marked unknown
Scenario: Difference blocks an equivalence claim
  Test: bridge846_compare_reject
  Given a rebuild whose functions differ from 84695d62 outside the approved exception table
  When the comparison tool runs
  Then it exits non-zero and lists each unexplained function instead of reporting equivalence
