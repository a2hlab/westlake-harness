# first_wall.py — parameterized first-wall table + U10-vs-U9 diff (#90)

`u9_first_wall.py` (hardcoded to U9) generalized to `first_wall.py` with `--runtime / --run-pattern / --signoff`
(+ `--run-index / --label / --out / --compare-to`). Phase 1 (this commit, offline): parameterize + reproduce the U9
table. Phase 2 (after U10 sign-off): run with U10 params → U10 first-wall table → per-key diff vs U9.

## Phase 1 — reproduce U9 (done, verified)
```
python3 first_wall.py --label u9 --out .
# defaults: --runtime a8cb9a5a45a6 --run-pattern approved-j10g
#           --signoff .../2026-10-01-u9-sweep/outer-signoff.json
```
Output `u9-first-wall.{json,md}` here **reproduces the committed U9 table** (`2026-10-01-u9-sweep/u9-first-wall.json`,
commit `c671f4fc8`) — **51 non-lit keys, 0 field diffs** (family/cause/verdict/u10_covered all match; self-check in the
commit log). The `u9-first-wall.json` here (schema `first-wall-v2`, `label: u9`) is kept as the **baseline for the U10
diff**.

## Phase 2 — U10 (run once U10 is signed; BLOCKED on U10 sign-off)
When the U10 three-board window is signed and its run_index rows exist:
```
python3 first_wall.py --label u10 \
    --runtime <signed U10 RUNTIME fp>      # 5ea/5cd fe5d9e139746, 61b 519148f0f41a per cx-t0 r2 (confirm from the signed sign-off)
    --run-pattern <U10 window run substring>   # e.g. the U10 rollout run name (as 'approved-j10g' was for U9)
    --signoff <signed U10 outer-signoff.json> \
    --out . --compare-to u9-first-wall.json
```
This writes `u10-first-wall.{json,md}` and `u10-vs-u9-diff.{json,md}`.

**Note on `--run-pattern` / `--runtime`:** a U10 full window may be three per-board runs with different RUNTIME fps
(5ea/5cd vs 61b). If so, run `first_wall.py` once per board fp and union, or pick the run-pattern that selects the
signed U10 rollout; the run_index row match is `runtime_fp == --runtime AND --run-pattern in row.run`. cx-t0's signed
sign-off names the exact fps + run; use those.

## The diff classes (per key, U10 vs U9)
- **unchanged** — non-lit in both, same family + cause (same wall).
- **moved** — non-lit in both, family/cause changed → the `detail` shows `<U9 wall> -> <U10 wall>` (moved to where).
- **disappeared** — non-lit in U9, **lit** in U10 → the U9 wall is gone (a U10 fix landed).
- **new-wall** — lit in U9, non-lit in U10 → a regression U10 introduced (investigate).

## Focus keys (the diff md surfaces these first)
`toutiao` (U9 wall: libflipped→libstdc++; U10 adds libstdc++ → expect **disappeared** or **moved** to the next native
wall), `fd-meet` (abort-visibility → U10ShareResidentCompat), `firefox` + `fd-fennec_fdroid` (native:signal /
strerror_r → compat shim), `cv2-com-nbossard-packlist` (Predicate stub), `fd-tutanota` (J10f WebSettings). These are the
keys whose U9 cause maps to a named U10 fix (`U10_COVERAGE` in the script) — the diff is the empirical check of whether
the fix actually moved/removed the wall (ground truth = the U10 hilog, not the coverage map).

## Caveat
The table is a **first-wall** classifier: it reports the first fatal per non-lit key from run_index. "disappeared (now
lit)" means the key left the non-lit set — confirm with the U10 screenshot (lit), not just the absence of a fatal.
A "moved" key is the useful signal (a fix passed one wall and exposed the next). `u10_covered` column is U9-only
(the task's U10 fix set); for `--label u10` it is blank.

Evidence: U9 defaults reproduce `2026-10-01-u9-sweep/u9-first-wall.json` (`c671f4fc8`); run_index
`westlake-inputs/run-index/index.jsonl`; U9 sign-off `2026-10-01-u9-sweep/outer-signoff.json`.
