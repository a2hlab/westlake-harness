spec: task
name: "Inventory the 846 bridge: toolchain, inputs, function-to-source map"
inherits: project
---
## Intent
Turn the binary into a checklist: which toolchain, which libraries it links, and for every defined function which source file in which tree defines it.
## Boundaries
### Allowed
- benchmark/2026-10-01-bridge-846-buildchain/**
- specs/bridge-846-buildchain/**
- tools/spec-checks/tests/bridge_846_buildchain.rs
### Forbidden
- Device commands; edits to deployed artifacts or the frozen registry
## Acceptance Criteria
Scenario: Toolchain identified
  Test: bridge846_toolchain
  Given the 84695d62 binary and its .comment, build-id and DT_NEEDED
  When the inventory script runs
  Then it records the exact compiler and linker identity (llvm-project 99548401bd80, LLD 15.0.4) and locates the matching toolchain with its sha256 (DevEco Studio bundled SDK on the Mac is the known candidate), or writes unknown
Scenario: Every defined function mapped
  Test: bridge846_function_map
  Given every defined .symtab STT_FUNC of 84695d62 (2720 functions; 4121 counts all defined symbols)
  When they are matched against the candidate source trees (real-work oh61-v7-b2133b5b, source-closure verify, real-work history near 2026-08-03..08-10)
  Then each function is mapped to a source file and commit or marked unknown, and the unknown count is reported
Scenario: Missing toolchain is not guessed
  Test: bridge846_toolchain_unknown
  Given no toolchain on a2hlab or hw248 matches the recorded clang and LLD identity
  When the inventory script runs
  Then it exits non-zero, reports the identity as unmatched and proposes no substitute toolchain
