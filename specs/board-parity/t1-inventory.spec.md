spec: task
name: "Inventory three-board hashes and mapped runtime identity"
inherits: project
---

## Intent
Deliver benchmark/2026-09-29-board-parity/README.md and results.json with full runtime file parity, live appspawn-x/HelloWorld mappings, and evidence-based alignment advice.

## Decisions
- Capture complete requested trees recursively and distinguish missing paths from transport failure.
- Compare maps device/inode to process-root stat; prefer map_files hashes where available.
- Never claim active bytes from a pathname whose inode does not match maps.

## Boundaries
### Allowed Changes
- benchmark/2026-09-29-board-parity/**
- specs/board-parity/**
- tools/spec-checks/src/lib.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md
- .octos/OPS-RUNBOOK.md
### Forbidden
- Device writes, launches, locks, deployment, commits and pushes.
- Fabricated hashes or reuse of historical observations as a fresh snapshot.

## Completion Criteria
Scenario: All requested component trees have contemporaneous observations
  Test: board_parity_live_evidence
  Given three explicitly allowed board serials
  When read-only recursive inventory completes with stable boot identities
  Then full hashes and differences retain raw evidence and missing paths remain explicit

Scenario: Mapped objects are distinguished from replaced pathname files
  Test: board_parity_offline
  Given fixtures with matching and mismatching map inode and root inode plus transport failures
  When the parser classifies live identity
  Then inode mismatches and unavailable reads cannot become verified mappings

Scenario: Every board has appspawn and HelloWorld mapping evidence
  Test: board_parity_live_evidence
  Given a running appspawn-x and HelloWorld child on each board
  When maps and process identity are read without launching applications
  Then each required process retains maps and matching mapped-object hashes or explicit gaps preventing full completion
