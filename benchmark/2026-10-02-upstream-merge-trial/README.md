# Upstream tool trial-merge (origin/master, ymote's PR #19-22) — result

Offline trial (user authorized copying upstream tools). No push. Branch `upstream-merge-test`
(`git merge origin/master` into feat/wikipedia-line). origin/master = `f673d1f2f1`; merge-base =
`e3100e15` (PR #18). This records whether the gap-map toolchain merges, its tests pass, and whether its
first-blocker scorer lines up with our U9 observed first fatals.

## 1. Merge — clean, 0 conflicts
`git merge origin/master` on upstream-merge-test: **0 conflicts**. Predicted beforehand by
`comm -12` of (our base->HEAD changed, 6225 files) and (upstream base->origin changed, 302 files) = **empty
intersection** (and no add/add: no path added on both sides). Upstream brought **292 new + 10 modified** files;
we had touched none of them. Upstream did **not** modify our `.octos/KNOWLEDGE-DIGEST.md`, `.octos/OPS-RUNBOOK.md`
or `README.md` (so there is no documentation.json to write).

Upstream change, grouped: `harness/westlake_gap/` 10, `probes/` 27, `tests/` 4, `scripts/*.py` 7,
`benchmark/{blockers-ledger,loop-outcomes}.json`+`LOOP-100.md` 3, and 251 files under `benchmark/2026-09-2x-*`
blind-batch RESULT dirs (data, not tools — excluded from the landing manifest).

## 2. Tests — both suites green
- Upstream `tests/` (the gap-map tool's own tests), run in the merged tree with the repo's rule
  `PYTHONPATH=harness:tests`: **`Ran 109 tests ... OK (skipped=3)`**. (Without that PYTHONPATH `import
  westlake_gap` resolves to the master worktree's older copy and 23 tests error/fail on missing new functions —
  a path artifact, not a merge problem; with it, all green.)
- Our `scripts/lab/tests` (run in the master worktree, where `lab_paths.py` and the other deps exist; the merge
  does not touch `scripts/lab/`): **`Ran 95 tests ... OK`**. (This stale wiki worktree lacks `lab_paths.py`, so it
  cannot run them locally — a pre-existing worktree-staleness issue the merge does not change.)

## 3. gap-map trial against our U9 51 unlit keys — tool runs, but needs 3 adaptations to score route-A
Pipeline: `harness.westlake_gap.lifecycle --json <hilog>` (observed first blocker) -> `scripts/score_first_blockers.py
<lifecycle.json> <map-root>...` (score each against its gap map). Ran `lifecycle` on all **51** U9 unlit-key hilogs
(from `benchmark/2026-10-01-u9-sweep/outer-signoff.json` runs) and `score_first_blockers.py` against the 101 upstream
corpus gap maps. The tools execute end-to-end, but against our runs:

1. **`lifecycle` mis-fires on route-A hilogs.** For ~all of our `dead` keys it reports the first blocker as
   `native-loading: path is outside app domain: /system/android/lib64/libwestlake_html_compat.so` — a route-A line
   present in every route-A child hilog — instead of the real fatal our `u9-first-wall` extracts
   (`[CHILD_CK] J_invokeStaticMain_main_threw: <java/native exception>`). It does not know route-A's `[CHILD_CK]`
   marker and does not skip the ubiquitous html_compat "path outside app domain" load attempt.
   - Where it *does* agree: for our `no-fatal`/`alive-white-window` keys it returns `no-blocker` (reached the drawing
     rung) — consistent with our `no-fatal` (the app ran, drew no content). So the white-lottery keys line up; the
     dead keys do not.
2. **No U9-specific gap maps.** `score_first_blockers.py` -> **`no-map` for all 51**: the corpus maps are keyed by
   upstream app names (`com.keylesspalace.tusky`), ours by `fd-tusky` / `cv2-<pkg>`. Scoring our runs needs per-key
   maps built from a **U9 runtime index** (`snapshot-runtime` over our U9 BCP + bridge/runtime ELFs) scanned over our
   51 APKs — that index does not exist yet.
3. **App-name alignment.** Even with U9 maps, the lifecycle app key (hilog dir name) must match the map dir name.

Net: the toolchain is sound and merges clean; to score **our** U9 runs it needs (a) a route-A profile for
`lifecycle` (the `[CHILD_CK]` fatal marker + ignore the html_compat line), (b) a U9 runtime index + a scan of our 51
APKs to produce per-key gap maps, (c) fd-<key> <-> package-name mapping. None are blockers — they are the adaptation
work to adopt it. Evidence: `score-trial.md` (per-key lifecycle-vs-u9-first-wall table + the score=no-map output).

## 4. Landing
- **Tools land.py can copy** (ALLOWED prefixes `scripts/`, `benchmark/`): the 7 `scripts/*.py`
  (`fix_queue, loop_report, oh_events, predict_first_screen, score_checks, score_first_blockers, score_observed`) and
  the 3 ledger files (`benchmark/{blockers-ledger,loop-outcomes}.json`, `benchmark/LOOP-100.md`). Manifest:
  `landing-paths-upstream-tools.txt`; preflight raw below.
- **Tools outside land.py's ALLOWED prefixes** (`harness/westlake_gap/` 10, `probes/` 27, `tests/` 4): land.py would
  REFUSE these. Bring them with **`git merge origin/master` into master** — the trial proved that merge is clean
  (0 conflicts); that is the right vehicle for a cross-tree tool import anyway (they already live in the git remote).
- **documentation.json**: none — upstream did not touch our DIGEST / RUNBOOK / README.
- The 251 `benchmark/2026-09-2x-*-blind` result dirs are upstream's data, not tools — not landed here (they come with
  the git merge if wanted).
