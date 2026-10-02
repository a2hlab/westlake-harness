# spec-checks regression triage (master 621614ce2a, offline classification only)

`cd tools/spec-checks && cargo test` on master: **48 passed / 9 failed**. Each failure re-run individually; the exact failing line and the command are in `triage.csv`. No test or code under test was changed.

## Class counts

| Class | Count | Meaning |
|---|---|---|
| **A** | 4 | Acceptance gate never met — assertion text says "NOT met" / "nothing for the outer loop to read" |
| **B** | 2 | Path-related known answer — expectation hard-codes the lane tree name (`westlake-harness-bms/…`) but the actual run produced `westlake-harness/…` |
| **C** | 3 | Real drift or broken code — manifest/runner drift, or a silent-skip test that expects a non-zero exit but gets 0 |

## A (gate never met)

- `b1_wikipedia_lit_after_sandbox_prep` — "visual gate NOT met"
- `b5_wikipedia_lit` — "own-UI acceptance NOT met"
- `b7_lit_by_outer_review` — "no app survived past its B7 wall … nothing for the outer loop to read"
- `b7_no_regression` — "ZigZag not launched on 5cd … needs its own candidate generation"

## B (path-related known answer)

- `b10_installer_background` — expectation has `westlake-harness-bms/benchmark/…`, actual `westlake-harness/…`
- `white_window_offline` — same path mismatch in the expected dict

## C (real drift / broken)

- `bms_batch_offline` — `ValueError: manifest/runner drift: review and repin the plan before use`. Reproduce: `python3 -m unittest discover -s benchmark/2026-09-28-bms-route-deploy/batch -p 'test_*.py'`
- `bms_rerun_offline` — same drift in test_b4_rerun. Reproduce: `python3 -m unittest discover -s benchmark/2026-09-28-bms-route-deploy/batch -p 'test_b4_rerun.py'`
- `b10_build_silent_skip_fails` — `AssertionError: 0 == 0` (expected a failing build, got success). Reproduce: `python3 benchmark/2026-09-29-static-wall-prediction/test_static.py StaticTests.test_build_silent_skip_fails`

Note: `bms_rerun_offline` and `bms_batch_offline` share the same underlying drift error — fixing the plan repin addresses both.
