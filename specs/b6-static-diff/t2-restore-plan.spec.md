spec: task
name: "Correct sealed provider baseline and group restoration evidence"
inherits: project
depends: [t1-compare]
---

## Intent
Replace the superseded provider comparison with sealed R155 80c9aee0 versus task50 8d109259 and give cx-t0 one four-group restoration checklist with binary evidence and source edit targets.

## Decisions
- Pin corrected provider identity to the old child manifest and preserve host/child evidence bytes.
- Keep mandatory nonzero callback checks and distinguish moved sealed-open installation from removal.
- Report static findings separately from unverified runtime causality; no deployment or commit.

## Boundaries
### Allowed Changes
- benchmark/2026-09-29-b6-static-diff/**
- specs/b6-static-diff/**
- tools/spec-checks/**
- README.md
- .octos/KNOWLEDGE-DIGEST.md
### Forbidden
- No device operations, external source changes, binary edits, commit or push.

## Completion Criteria
Scenario: Correct provider identity and unchanged host child evidence are independently checked
  Test: b6_static_diff
  Given the sealed provider file and both child manifest byte arrays
  When offline identity and preserved-evidence checks run
  Then both provider hashes match their child manifests and host child evidence hashes remain unchanged

Scenario: Service predicate and moved installation have regression evidence
  Test: b6_static_diff
  Given old and new provider disassembly with original instruction offsets
  When the provider protocol checker runs
  Then both nonzero field checks match and sealed open installation moves from installer to constructor

Scenario: Four protocol groups have reviewable source restoration advice
  Test: b6_static_diff
  Review: human
  Given all function assessments and the corrected provider baseline
  When cx-t0 reads RESTORE-PLAN.md
  Then service table namespace VM and stdio groups have evidence source targets and offline exit checks
  And runtime causality remains unverified without device execution
