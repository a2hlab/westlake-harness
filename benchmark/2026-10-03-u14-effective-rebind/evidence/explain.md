# Contract Review: U14 per-board conditional binding and ABI slot

## Intent

Provide parameterized common and 61b U13 transaction bases, preserve the board-local installer, and accept only a hash-pinned native ABI slot replacement after its donor arrives.

## Decisions

- No device, VM, compilation, image bake or active approval registry changes.
- U13 promotion remains unconfirmed; all generated bundles remain disabled.
- Common U13 content is 91272eaf; 61b content is 8861a11a. Planned identities come from U13 candidate maps, never from its T8 reference files.
- Only westlake_native/libwestlake_native_abi.so may change in the existing U14 artifact inventory. Images, JARs, root and Flutter ABI aliases remain byte-identical.
- Exception previews are unapplied and new findings remain unapproved.

## Boundaries

**Allowed:**
- benchmark/2026-10-03-u14-effective-rebind/**
- specs/u14-effective-rebind/**
- tools/spec-checks/tests/u14_effective_rebind.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

**Out of Scope:**
- Promotion, authorization, native builds, image rebakes and production VM replay.

## Verification Summary

| Total | Passed | Failed | Skipped | Uncertain | Pass Rate |
| --- | --- | --- | --- | --- | --- |
| 6 | 6 | 0 | 0 | 0 | 100.0% |

- ✅ Combined variant parameters bind planned U13 identities
  - test: `u14_effective_binding`
- ✅ Wrong baseline or installer identity is rejected
  - test: `u14_effective_binding`
- ✅ ABI-only artifact delta rejects unrelated changes
  - test: `u14_effective_binding`
- ✅ Fresh preview never applies pending approval
  - test: `u14_effective_preview`
- ✅ Exact image approval cannot authorize another pair
  - test: `u14_effective_preview`
- ✅ Diagnostic T8 references are explicit and replay is disabled
  - test: `u14_effective_binding`

## Coverage Matrix

| Rule | Scenario | Test | Found | Verdict | Provenance |
|------|----------|------|-------|---------|------------|
| — | Combined variant parameters bind planned U13 identities | u14_effective_binding | found | pass | computational |
| — | Wrong baseline or installer identity is rejected | u14_effective_binding | found | pass | computational |
| — | ABI-only artifact delta rejects unrelated changes | u14_effective_binding | found | pass | computational |
| — | Fresh preview never applies pending approval | u14_effective_preview | found | pass | computational |
| — | Exact image approval cannot authorize another pair | u14_effective_preview | found | pass | computational |
| — | Diagnostic T8 references are explicit and replay is disabled | u14_effective_binding | found | pass | computational |
