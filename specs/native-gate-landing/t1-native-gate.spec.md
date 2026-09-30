spec: task
name: "Wire deployment to native preflight"
inherits: project
---
## Intent
Reject missing or drifted native evidence before device dispatch and validate restoration independently.
## Boundaries
### Allowed
- scripts/lab/deploy_generation.py
- scripts/lab/deploy_generation.sh
- scripts/lab/deployment_native_gate.py
- scripts/lab/test_deploy_frozen.py
- knowledge/gates/native-predeploy-exceptions.json
- benchmark/2026-10-01-native-gate-landing/**
- benchmark/2026-10-01-u5-sweep/results.json
- benchmark/2026-10-01-u5-sweep/facts-all.txt
- specs/native-gate-landing/**
- tools/spec-checks/tests/native_gate_landing.rs
- README.md
### Forbidden
- Device commands or changes to native scanners and frozen policy
## Acceptance Criteria
Scenario: Pre-dispatch rejection
  Test: native_landing_dispatch
  Given missing inputs native rejection or changed evidence
  When any deployment mode is invoked
  Then no device dispatch occurs and rollback checks its own restored package
Scenario: Approved table only
  Test: native_landing_registry
  Given the approved A table and its evidence
  When the landing registry is audited
  Then exactly 257 identity-bound entries remain and no N8 entry is permanent
Scenario: Frozen policy retained
  Test: native_landing_frozen
  Given a mismatching frozen artifact or rollback target
  When deployment preflight runs
  Then deployment rejects before mutations
