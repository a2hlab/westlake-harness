spec: task
name: "U7 approved provenance and reboot replay"
depends: [t1-executor]
---
## Intent
Execute the outer ACK(95) 06:58 follow-up, with explicit host-side replay replacing automatic boot service as clarified by the outer.
## Decisions
- Bind T7D-REPRO-BACKTRACE-001 to original T7d bytes, nine inputs, frozen tools and three reproduction receipts; it is not a runtime safety exemption.
- Recover recorded U5 baseline overlays after reboot, then apply the same U7 bundle with a new journal. Do not change device startup configuration.
## Boundaries
### Allowed
- scripts/lab/u7_executor.py
- knowledge/gates/image-provenance-exceptions.json
- benchmark/2026-10-01-u7-executor/**
- tools/spec-checks/tests/u7_executor.rs
- specs/u7-executor/t2-solidify.spec.md
- .octos/KNOWLEDGE-DIGEST.md
- .octos/OPS-RUNBOOK.md
### Forbidden
- Frozen tool mutation, native or image binary changes, automatic boot services, writes to 5ea or 5cd
## Acceptance Criteria
Scenario: Exact approved provenance
  Test: u7_approved_provenance
  Given the approved original T7d outputs and three independent reproduction receipts
  When approval is revoked or any bound input, output, tool or evidence changes
  Then provenance is rejected; only the exact approved exception is deployable
Scenario: Explicit new-boot baseline recovery
  Test: u7_baseline_replay
  Given recorded persistent baseline overlays from a prior boot
  When the host explicitly restores the baseline
  Then hashes are checked before writes, parent stays stopped through all binds, foreign overlays and same-boot replay are refused
Scenario: Board identity and screenshots
  Test: u7_board_evidence
  审核: human
  Given an exclusive 61b window of at most 45 minutes
  When U7 is applied and then reapplied after a board reboot
  Then 312 identities, parent and child views, one ART and both U7 fingerprints match, controls and five selected apps have screenshots, and any failure returns to U5 with a receipt
