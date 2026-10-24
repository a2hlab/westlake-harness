# T146 — T136 offline tests runnable on a fresh clone (2026-10-25)

**Environment requirement (outer re-verification finding):** these tests import the production
modules, which resolve `MAIN`/`REPO` via the normal `lab_paths`/`WORKSPACES` environment. A fresh
temporary tree WITHOUT `WORKSPACES` set fails at first import; with `WORKSPACES` explicitly set,
all 8 current groups pass (85 checks, outer independent run, zero device actions).

Public small fixtures + synthetic baseline/candidate bytes; tests read fixtures, not private runs; originals untouched (SHA snapshot verified: all non-test *.py byte-identical). No device, no hdc, no skip-masking.

## Current-production tests (ALL PASS on fresh clone)

| test | result |
|---|---|
| test_entry_v8.py | PASS (synthetic_only) |
| test_v9_review.py | PASS (7 checks) |
| test_v8_lineage.py | PASS (14) |
| test_v8_roles.py | PASS (11) |
| test_v8_budget.py | PASS (2) |
| test_recovery_lineage.py | PASS (7) |
| test_recovery_roles.py | PASS (11) |
| test_v7_lineage.py | PASS (14) |

## Full matrix (final, all pass)

Outer final independent review: 14 files, 13 suites / 160 checks all pass (test_fixtures.py helper carries no assertions, not counted); 9 fixture hashes complete; production source and all assertion ASTs unchanged. Entry tests v1/v3/v4/v5/v7/v8 all pass on public fixtures + synthetic bytes.

Version→idle-source mapping (t146_patch.py, keyed on module __file__ basename): execute.py/v3/v4 → 024115-2e76dc; v5 → 025346-5209f4; v6 → 030926-e8956c; v7 → 032931-2688cd; v8/v9 → 034802-6bb129.

## Mechanism (test-only; originals byte-identical)

- `fixtures/identity/**` (9 files) + `fixtures/manifest.json` (SHA+bytes) — public copies of small pid/stat/identity/binding records, no private data.
- `t146_patch.py` — TEST-ONLY helper: synthetic rollback/candidate bytes+SHA (never real .so), temp INPUT dir, per-version IDLE_SOURCE fixture mapping + synthetic-sha normalization (writes temp copy; keeps keep-alive). Documented as test scaffolding, not a core tool.
- Tests patched: `.private/...` paths → `fixture(...)`; `TemporaryDirectory(dir=P/'.private')` → default; entry tests call `patch_module(m)`.

Independent outer raw test receipts are preserved under `$HOME/.local/share/westlake/t146-portability-review-20261025/final-review/isolated-hzq8pqin/`. They include all 13 suites / 160 checks; synthetic tests do not establish device behavior.
