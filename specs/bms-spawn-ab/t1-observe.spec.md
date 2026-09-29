spec: task
name: "Compare HelloWorld and Wikipedia desktop launch chains"
inherits: project
---

## Intent

Capture same-board cold desktop launches and identify the first evidenced difference in the AMS to runtime chain.

## Decisions

- Sample target UID processes across the first 15 seconds and retain launch-window hilog, faultlog inventory, BMS metadata and mount/runtime identity.
- Inspect the accepted restore scripts to separate global runtime preparation from per-app setup.
- Keep conclusions bounded when polling or logs cannot establish a specific fork/exec/crash event.

## Boundaries

### Allowed Changes
- benchmark/2026-09-28-bms-route-deploy/spawn-ab/**
- specs/bms-spawn-ab/**
- tools/spec-checks/src/lib.rs
- .octos/KNOWLEDGE-DIGEST.md
- .octos/OPS-RUNBOOK.md
- README.md

### Forbidden
- No writes to 61b or 5cd, no APK replacement, no runtime patches, no reboot and no push.

## Completion Criteria

Scenario: Both launch trials retain comparable evidence
  Test: bms_spawn_ab_evidence
  Given locked 5ea with an unchanged boot and runtime generation
  When HelloWorld and Wikipedia are launched sequentially from their exact desktop icons
  Then both trials retain 15-second process samples, hilog, fault inventory and BMS metadata
  And all archived evidence hashes match the manifest

Scenario: The launch divergence and restore preparation are explained
  Test: bms_spawn_ab_evidence
  Review: human
  Given the two raw launch records and accepted restore sources
  When the reviewer follows the cited evidence
  Then the report identifies the first evidenced divergence and remaining uncertainty
  And global preparation, per-app preparation and template desktop labels are distinguished
