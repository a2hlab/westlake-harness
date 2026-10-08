spec: task
name: "Evidence-bound tool catalogue"
inherits: project
---
## Intent
Catalogue the requested scripts and Rust contract adapters at the fixed master snapshot. Provide source roles, addition history, callers, tests, categories, weekly growth and five evidenced incident chains for an expert presentation.
## Decisions
- `tools.json` uses one row per Python, shell or Rust source file in the requested scope.
- `README.md` distinguishes source evidence from historical inference and absent evidence.
## Boundaries
### Allowed
- benchmark/2026-10-08-harness-tools-inventory/**
- specs/harness-tools-inventory/**
- tools/spec-checks/tests/harness_tools_inventory.rs
- README.md
### Forbidden
- Device operations, remote operations, pushes and changes to existing tool behavior
## Acceptance Criteria
Scenario: Complete pinned inventory
  Test: inventory_complete
  Given the pinned master tree and requested file filters
  When tools.json and README.md are checked
  Then each source file occurs exactly once with source role history callers and test fields
  And category and weekly totals equal the source inventory
Scenario: Unsupported origin is not invented
  Test: inventory_unknown
  Given a tool without a documentary incident origin or observed caller
  When inventory evidence is checked
  Then absent evidence is explicit and no runtime invocation is asserted
Scenario: Missing or changed evidence rejects
  Test: inventory_evidence
  Given path line or source identity drift
  When the inventory validator checks references
  Then it rejects missing references and changed source hashes
