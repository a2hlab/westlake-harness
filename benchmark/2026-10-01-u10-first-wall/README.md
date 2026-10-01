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
    --runtime <U10 facts.txt RUNTIME value>    # from the U10 shard facts.txt RUNTIME line — see caliber note
    --run-pattern <U10 window run substring>   # e.g. the U10 rollout run name (as 'approved-j10g' was for U9)
    --signoff <signed U10 outer-signoff.json> \
    --out . --compare-to u9-first-wall.json
```
This writes `u10-first-wall.{json,md}` and `u10-vs-u9-diff.{json,md}`.

**CALIBER (outer-ring, corrected 2026-10-01 23:2x):** `--runtime` must be the value on the **RUNTIME line of the shard
`facts.txt`** (the bms_batch caliber — this is what `run_index.runtime_fp` is populated from, and what the row match
`runtime_fp == --runtime` compares). The caliber **changed** between U9 and U10: bms_batch switched the facts RUNTIME
value to the **123-item install-chain caliber** after the fingerprint update, so:
- **U9:** facts RUNTIME = `a8cb9a5a45a6` (pre-update caliber), **same across all three boards** → one run covers all.
- **U10:** facts RUNTIME = the 123-item caliber, **per-board**: 5cd/5ea `fe5d9e139746`, 61b `519148f0f41a` (these happen
  to equal the fps cx-t0 named — because for U10 the facts caliber IS that 123-item caliber). So run `first_wall.py`
  **twice** (`--runtime fe5d9e139746` and `--runtime 519148f0f41a`) and **union** the non-lit keys; a key is "disappeared
  (now lit)" only if it is non-lit in neither board's table.

Always **read the U10 facts RUNTIME line first** and use exactly those values — don't assume U9's value carries over.
Match rule: `runtime_fp == --runtime AND --run-pattern in row.run`.

## U10 observation (2026-10-01, FAILED candidate — unsigned; `--observe`)
Ran once oc-t4 rebuilt run_index (fe5d9e139746 42 rows + 519148f0f41a 20 rows, run `u10-bundle/window`):
```
python3 first_wall.py --observe --label u10 --runtime fe5d9e139746,519148f0f41a \
    --run-pattern u10-bundle/window --out . --compare-to u9-first-wall.json
```
`--observe` builds from run_index rows directly (no sign-off exists for a failed candidate); verdict is **process
survival at t20 (alive/dead), NOT lit/white** — screenshots are the outer ring's ground truth. 58 keys ran; diff vs U9:
`ran-ok? 33, not_run 28, moved 9, cleared? 7, unchanged 7, regression? 2`. Products: `u10-first-wall.{json,md}`,
`u10-vs-u9-diff.{json,md}`. **For U10.1 pre-read only, not a sign-off.** Headline (focus keys):
- **toutiao, fd-tutanota → `cleared?`** (U9 NPE wall gone, alive@t20 — libstdc++ / J10f fixes took; confirm lit by screenshot).
- **fd-meet → `unchanged`** (still `UnsatisfiedLinkError`), **fd-fennec_fdroid → `unchanged`** (still `native:signal`) — those U10 fixes did not clear their first wall.
- **opencamera, fd-organicmaps → `regression?`** (ok on U9 → dead on U10: ULE / NPE); **fd-app → `moved`** (U9 white → U10 ULE); **fd-plus → `moved`** (ISE → NPE). This is the **SoundPool / native-bundle regression** that triggered the U10 rollback — U10 had **11 `UnsatisfiedLinkError`** vs U9's 3 (the native bundle inherited a missing `libsoundpool`). It is why the window was cancelled, and exactly what U10.1 must fix before re-running.
- **packlist, firefox → `not_run`** (the failed window only reached part of each board); **wikipedia → `ran-ok?`** (alive@t20, no fatal).

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
