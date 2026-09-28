spec: task
name: "Execute and report the 66-key BMS sweep"
inherits: project
---

## Intent

Install the 66 original APK inputs in three round-robin shards, click their actual BMS desktop entry and preserve evidence for outer visual review.

## Decisions

- Preserve controls, blocked and tail phase order; distribute 22 keys per board with 5/4/4 historical controls.
- Derive the desktop activity from BMS entry-module mainAbility, because Android launcher aliases may differ from the historical direct-launch activity.
- Reject ambiguous desktop entries and retain prior attempts when resuming after a corrected selector or transient transport failure.
- Compare every key to the September 27 Westlake result without equating a process or successful install with visible UI.

## Boundaries

### Allowed Changes
- benchmark/2026-09-28-bms-route-deploy/**
- specs/bms-route-execution/**
- tools/spec-checks/**
- .octos/KNOWLEDGE-DIGEST.md
- .octos/OPS-RUNBOOK.md
- README.md

### Forbidden
- Do not modify APK bytes, deploy another runtime, flash boards, or push.
- Do not overwrite first-attempt evidence or automatically classify screenshots as LIT.

## Completion Criteria

Scenario: Desktop aliases and invalid identities are handled faithfully
  Test: bms_batch_offline
  Given the 66-key manifest and BMS launcher aliases different from direct-launch activities
  When the offline regression checks run
  Then exact BMS mainAbility selects the actionable desktop icon
  And wrong package, hash, board, lock, ambiguous icon and stale screenshot are rejected

Scenario: All 66 original keys retain independent outcomes and comparisons
  Test: bms_batch_evidence
  Given three assigned board shards and all retained execution attempts
  When the final evidence report is validated
  Then each manifest key has a terminal record and its September 27 comparison
  And each referenced screenshot exists and matches its recorded hash

Scenario: Screenshots are available for independent visual judgment
  Test: bms_batch_evidence
  Review: human
  Given successful captures and separately recorded install or launch failures
  When the outer reviewer reads the referenced images
  Then the reviewer can distinguish real app UI from blank surfaces, desktop and fallback
  And machine status does not assert LIT
