spec: task
name: "BMS install desktop launch capture batch"
inherits: project
---

## Intent

Deliver one command for hash-checked APK installation, BMS readback, exact desktop icon launch and fresh screenshot collection. The default remains an offline plan; real execution is reserved for the assigned deployment lane after item 19.

## Decisions

- The manifest orders 13 controls, 43 blocked apps, then 10 tail keys, without deduplicating APK identities.
- Desktop selection requires a unique actionable SceneBoard icon matching package and activity.
- Each record retains install result, bundle query result, foreground observations, screenshot path/hash and pending visual review.
- Validate attachment, OH6.1 identity and the caller lane lock before device writes; stop the batch on lost transport or boot changes.

## Boundaries

### Allowed Changes
- benchmark/2026-09-28-bms-route-deploy/batch/**
- specs/bms-route-batch/**
- tools/spec-checks/**
- README.md
- .octos/KNOWLEDGE-DIGEST.md

### Forbidden
- No real device execution in this preparation task.
- No runtime/base replacement, flashing, remote push, or automatic LIT verdict.

## Completion Criteria

Scenario: Plan and simulated install launch capture keep per-key evidence
  Test: bms_batch_offline
  Given a 66-key manifest and a simulated board transport
  When the offline plan and batch tests run
  Then the 13 controls precede 43 blocked and 10 tail entries
  And install readback, desktop click, foreground evidence and screenshot provenance are retained

Scenario: Wrong identity, ambiguous icon, and stale capture are rejected
  Test: bms_batch_offline
  Given a wrong APK hash or serial, missing lock, duplicate icon, or stale capture
  When the batch processes the invalid input
  Then it rejects that input without claiming visual success
  And boot changes and transport loss stop subsequent device writes
