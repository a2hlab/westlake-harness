spec: task
name: "U7 stopped-parent executor"
inherits: project
---
## Intent
Provide production apply, rollback and dry-run entry points with journaled, stopped-parent activation and honest image provenance.
## Decisions
- Use file bind overlays to preserve all existing directory and JAR mount layers; never remove a baseline overlay.
- Reject preflight drift before writes; keep the service stopped when rollback cannot prove a coherent baseline.
- Missing build provenance is unknown and blocks apply, but permits an explicitly non-deployable offline report.
## Boundaries
### Allowed
- scripts/lab/generation_bundle.py
- scripts/lab/u7_executor.py
- scripts/lab/sweep_bind_deploy.py
- scripts/lab/deploy_generation.py
- benchmark/2026-10-01-u7-executor/**
- specs/u7-executor/**
- tools/spec-checks/tests/u7_executor.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md
### Forbidden
- Device I/O during implementation or changes to native/image/frozen gate policy
## Acceptance Criteria
Scenario: Whole transaction ordering
  Test: u7_transaction
  Given native aliases and all Java members with existing overlay layers
  When activation succeeds
  Then every bind occurs while parent is stopped and start happens only after full identity verification
Scenario: Failure and interruption recovery
  Test: u7_recovery
  Given a failure or ambiguous command completion at any mount boundary
  When rollback runs or resumes
  Then only owned mounts are removed and baseline hashes and layer stacks match before restart; drift retains a stopped service
Scenario: Offline gates and binding
  Test: u7_preflight
  Given missing components, changed gate inputs, unknown build provenance or a rejected native gate
  When preflight runs
  Then no device object is created and apply is refused; dry-run reports unknown honestly
Scenario: Complete format and receipt
  Test: u7_format
  Given the exact 28-member boot group and a nine-input/27-output image receipt
  When the bundle is checked
  Then malformed paths and mismatched identities are rejected and receipt omissions remain unknown
