# Contract Review: U14 partial composition and scope

## Intent

Compose the available native and JAR components while keeping missing boot images visibly pending.

## Decisions

- Keep artifact comparison against U13 91272eaf independent of the parameterized transaction baseline.
- Do not build native outputs, use a VM, deploy, mutate approvals, or authorize a window.
- Verify every selected artifact hash; change only the declared private aliases and existing ICU pair.
- Remove the old bundle descriptor and old paired receipt from the partial output.
- Require an explicit transaction baseline argument for finalization, not a hidden U12 default.

## Boundaries

**Allowed:**
- benchmark/2026-10-03-u14-final-assembly/**
- specs/u14-final-assembly/**
- tools/spec-checks/tests/u14_final_assembly.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

**Out of Scope:**
- Native compilation, VM access and device operations.

## Verification Summary

| Total | Passed | Failed | Skipped | Uncertain | Pass Rate |
| --- | --- | --- | --- | --- | --- |
| 3 | 3 | 0 | 0 | 0 | 100.0% |

- ✅ Pinned partial composition is disabled
  - test: `u14_final_composition`
- ✅ Private alias drift is rejected
  - test: `u14_final_composition`
- ✅ Missing transaction baseline is rejected
  - test: `u14_final_composition`

## Coverage Matrix

| Rule | Scenario | Test | Found | Verdict | Provenance |
|------|----------|------|-------|---------|------------|
| — | Pinned partial composition is disabled | u14_final_composition | found | pass | computational |
| — | Private alias drift is rejected | u14_final_composition | found | pass | computational |
| — | Missing transaction baseline is rejected | u14_final_composition | found | pass | computational |
