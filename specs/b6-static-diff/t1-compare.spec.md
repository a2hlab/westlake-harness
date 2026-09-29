spec: task
name: "Compare R155 and task50 ELF generations"
inherits: project
---

## Intent
Deliver dynamic metadata, symbol and string inventories first, then a function-by-function instruction comparison for host, child and runtime-provider. Explain which differences merit R155 restoration without presenting static hypotheses as proven crash causes.

## Decisions
- Inventory every defined function symbol, aliases and executable coverage gaps.
- Compare address-normalized instructions and a separate register-number-normalized view; preserve non-address constants and raw instruction evidence.
- Include ordered dependencies, constructors/destructors, TLS, relocation counts, imports and exports.
- Every difference has a restoration or harmless disposition with evidence and explicit confidence limits.

## Boundaries
### Allowed Changes
- benchmark/2026-09-29-b6-static-diff/**
- specs/b6-static-diff/**
- tools/spec-checks/**
- README.md
- .octos/KNOWLEDGE-DIGEST.md
### Forbidden
- No board commands or binary mutation.
- No runtime-equivalence claim from normalized equality alone.

## Completion Criteria
Scenario: Six ELF artifacts have complete reproducible comparison inventories
  Test: b6_static_diff
  Given three R155 artifacts and three task50 candidates with expected hashes
  When the offline evidence validator runs
  Then all six identities and all inventoried functions have comparison records
  And metadata, symbols, strings and function deltas have dispositions

Scenario: Wrong input identity or normalization that erases semantic constants is rejected
  Test: b6_static_diff
  Given a mismatched input hash or instruction pair differing in a memory offset or numeric constant
  When the comparison checker runs its negative controls
  Then the hash mismatch is rejected and those instructions remain different
