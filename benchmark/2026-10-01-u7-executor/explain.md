# Contract Review: U7 stopped-parent executor

## Intent

Provide production apply, rollback and dry-run entry points with journaled, stopped-parent activation and honest image provenance.

## Decisions

- Use file bind overlays to preserve all existing directory and JAR mount layers; never remove a baseline overlay.
- Reject preflight drift before writes; keep the service stopped when rollback cannot prove a coherent baseline.
- Missing build provenance is unknown and blocks apply, but permits an explicitly non-deployable offline report.

## Boundaries

**Allowed:**
- scripts/lab/generation_bundle.py
- scripts/lab/u7_executor.py
- scripts/lab/sweep_bind_deploy.py
- scripts/lab/deploy_generation.py
- benchmark/2026-10-01-u7-executor/**
- specs/u7-executor/**
- tools/spec-checks/tests/u7_executor.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

**Forbidden:**
- Device I/O during implementation or changes to native/image/frozen gate policy

## Verification Summary

| Total | Passed | Failed | Skipped | Uncertain | Pass Rate |
| --- | --- | --- | --- | --- | --- |
| 4 | 4 | 0 | 0 | 0 | 100.0% |

- ✅ Whole transaction ordering
  - test: `u7_transaction`
- ✅ Failure and interruption recovery
  - test: `u7_recovery`
- ✅ Offline gates and binding
  - test: `u7_preflight`
- ✅ Complete format and receipt
  - test: `u7_format`

## Coverage Matrix

| Rule | Scenario | Test | Found | Verdict | Provenance |
|------|----------|------|-------|---------|------------|
| — | Whole transaction ordering | u7_transaction | found | pass | computational |
| — | Failure and interruption recovery | u7_recovery | found | pass | computational |
| — | Offline gates and binding | u7_preflight | found | pass | computational |
| — | Complete format and receipt | u7_format | found | pass | computational |
