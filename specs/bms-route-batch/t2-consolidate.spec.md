spec: task
name: "Consolidate reinstall diagnostics and focus checked captures"
inherits: project
depends: [t1-batch]
---

## Intent
Implement board item 57 in bms_batch.py with offline FakeBoard checks, preserving master guardrails and original APK identity.

## Decisions
- Resolve app-input before writes, allow an existing empty per-app directory and reject stale run evidence.
- Explicit reinstall uninstalls only a confirmed installed target and requires successful BMS output plus readback.
- Optional hilog resets before launch, dumps at the requested offset, and collects newly created faultlog files.
- Multiple screenshot offsets use click-relative timing, fresh target PIDs and focused window ownership; known 36627-byte black frames never pass capture acceptance.
- Lock holder, attachment, boot identity, launcher gate and bounded empty-output retries remain mandatory.

## Boundaries
### Allowed Changes
- benchmark/2026-09-28-bms-route-deploy/batch/**
- benchmark/2026-09-28-bms-route-deploy/sandbox-prep/source*
- specs/bms-route-batch/**
- tools/spec-checks/**
- README.md
- .octos/KNOWLEDGE-DIGEST.md
### Forbidden
- No real device commands, installer swap, external source edits, commit or push.
- No weak focus fallback or automatic visual LIT verdict.

## Completion Criteria
Scenario: Reinstall resolves unknown package keys and preserves text failures
  Test: bms_batch_offline
  Given FakeBoard installed and missing targets plus x and noice style metadata
  When reinstall is selected
  Then the resolved package is used and uninstall precedes installation only for an installed target
  And zero return code with failure text cannot pass or trigger desktop launch

Scenario: Timed diagnostics and every requested screenshot retain provenance
  Test: bms_batch_offline
  Given a FakeBoard clock with old and new faultlog files
  When hilog and shots at 5 and 20 seconds are requested
  Then reset precedes click and dump and screenshots respect their offsets
  And each screenshot retains focused window PID ownership and rejects known black frames
  And only newly observed faultlog files are received

Scenario: Unknown focus and lost identity fail closed without later writes
  Test: bms_batch_offline
  Given a launcher row with spaces or missing focus and an empty lock response or changed boot
  When the runner evaluates its gates
  Then parsing accepts valid rows and bounded retries preserve ownership checks
  And lost lock boot or transport stops the batch and remaining apps are not run

Scenario: Default planning and prepared directories remain safe offline
  Test: bms_batch_offline
  Given an existing empty app directory and malformed timing arguments or stale evidence
  When CLI and collection checks run
  Then plan mode invokes no subprocess and invalid timing or stale records are refused before device writes
  And per-app directories exist before diagnostic output is written
