# Contract Review: U14 actual receipt and review evidence

## Intent

Keep actual gate rejection and missing bake evidence distinct from approved execution.

## Decisions

- Keep artifact comparison against U13 91272eaf independent of the parameterized transaction baseline.
- Do not build native outputs, use a VM, deploy, mutate approvals, or authorize a window.
- Retain raw native, open-site, strings and class-diff outputs without applying exceptions.
- Paired receipts require the actual nine input hashes, 27 output hashes, argv, tools, live logs and successful compiler/logging statuses.
- Validate the two remote guard amendments separately from the frozen compiler and driver.

## Boundaries

**Allowed:**
- benchmark/2026-10-03-u14-final-assembly/**
- specs/u14-final-assembly/**
- tools/spec-checks/tests/u14_final_assembly.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

**Out of Scope:**
- Outer approvals, production VM replay and screenshot signoff.

## Verification Summary

| Total | Passed | Failed | Skipped | Uncertain | Pass Rate |
| --- | --- | --- | --- | --- | --- |
| 3 | 3 | 0 | 0 | 0 | 100.0% |

- ✅ Raw rejection is retained
  - test: `u14_final_evidence`
- ✅ Incomplete or failed bake is rejected
  - test: `u14_final_evidence`
- ✅ Actual complete receipt is accepted
  - test: `u14_final_evidence`

## Coverage Matrix

| Rule | Scenario | Test | Found | Verdict | Provenance |
|------|----------|------|-------|---------|------------|
| — | Raw rejection is retained | u14_final_evidence | found | pass | computational |
| — | Incomplete or failed bake is rejected | u14_final_evidence | found | pass | computational |
| — | Actual complete receipt is accepted | u14_final_evidence | found | pass | computational |
