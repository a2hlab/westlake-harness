# api-leverage — startup-path reachability of high-leverage candidate APIs (entry #12/#18, lane oc-t0)

Date: 2026-09-28. Status: **PAUSED mid-run by outer-loop route switch (#18)** — the
analysis targets the Westlake 6.1 runtime and the campaign pivoted; results below are
what was computed before the pause. No board access, no image reading (pure offline).

Worktree `~/orca/workspaces/westlake-harness-lev`, branch `analysis/app-lighting-api-leverage`.

## What was asked

The outer loop had a correlation list: APIs that appear in many un-lit apps and few lit
apps (from the 09-27 sweep labels × static gap map × oc-t4 native scans). Entry #12 asked:
for each candidate, is it **startup-path reachable** (reached statically at stage
"process start" or "first activity") per app? Candidates used by lit apps on the same
path are marked **not lethal**. Ranking = `startup_blocked` desc, `startup_lit` asc.

## Method

- Tool: harness `startup-reach` (`harness/westlake_gap/reach.py`, staged static
  call-graph from manifest entry points; stages 0=process start, 1=first activity,
  2=next screens, 3=later, 255=not reached).
  Known-answer tests first: `tests/test_reach.py` **4/4 OK** on the Mac before any run.
- Ran on the build VM against VM-local APKs (`~/a2hlab/app-inputs/<key>/`), runtime
  index `~/a2hlab/static/runtime-index.json`, scans `~/a2hlab/static/scans/<key>.json`.
  VM needed a local venv (`androguard`, `networkx`, `pyelftools`) + a VM-local repo
  copy — the OrbStack /Users→VM path translation corrupted APK paths otherwise
  (FileNotFoundError on a mirrored `~/OrbStack/...` path).
- Coverage at pause: **75/101 scans computed**, incl. **63/66 swept keys**
  (x, noice have no static scan — noice≡fd-noice is covered by its fd- twin;
  toutiao was still computing at the pause and is absent). Raw reach outputs stay on
  the VM (`~/a2hlab/static/reach-20260928/`), not committed.
- Aggregator: `scripts/aggregate_leverage.py` — joins reach output with 09-27 sweep
  labels (66 launches, 13 distinct LIT), attributes each candidate to its minimal
  startup stage per app:
  - Java method candidates via `platform_stage` (framework class/method match);
  - service-name candidates by joining scan `service_requests` sites → `caller_stage`;
  - `androidx.window.extensions` probes via `existence_probes` → `caller_stage`;
  - native symbol families via scan `native_imports` importing library → `library_stage`.

## Results (63 swept keys: 13 LIT / 50 blocked)

| candidate | startup_blocked | startup_lit | verdict |
|---|---|---|---|
| activity:onWindowFocusChanged | 49 | 12 | not lethal (also on lit path) |
| view:dispatchDraw | 44 | 11 | not lethal |
| view:onWindowSystemUiVisibilityChanged | 39 | 11 | not lethal |
| pm:resolveService | 15 | 1 | **top discriminator** |
| netcb:onCapabilitiesChanged | 14 | 0 | **discriminator** |
| svc:sensor | 14 | 0 | **discriminator** |
| netcb:onAvailable | 13 | 1 | **discriminator** |
| svc:account | 11 | 1 | discriminator |
| native:ANativeWindow_* | 11 | 3 | mixed |
| pm:getInstallerPackageName | 9 | 1 | weak |
| svc:camera | 9 | 2 | weak |
| pm:getNameForUid | 7 | 0 | weak |
| svc:bluetooth | 7 | 0 | weak |
| pm:getInstallSourceInfo | 6 | 0 | weak |
| svc:download | 6 | 0 | weak |
| native:AMediaCodec* | 3 | 0 | weak |
| native:AHardwareBuffer* | 2 | 0 | weak |
| native:AMediaFormat* | 1 | 0 | weak |

Headline: the **window/render callback family** (onWindowFocusChanged / dispatchDraw /
onWindowSystemUiVisibilityChanged) is startup-reachable almost everywhere — lit apps
included — so it is **not** the wall. The sharpest startup-path discriminators are
**`PackageManager.resolveService`** (15 blocked vs 1 lit) and the
**network-callback / sensor-service** families (14/0, 13/1, 14/0).

Full per-app stage tables: `results.json`.

## Caveats (R2)

- reach computed for 75/101 scans: verified; toutiao + 25 co-* commercial keys absent
  at pause (co-* are unswept and out of entry scope anyway).
- stage attribution is **static reachability**, not runtime proof — correlation
  refined, causation still unproven.
- `svc:*` candidates join on scan call-sites; a dynamic-only `getSystemService` path
  (reflection) would be missed.
- ranking counts exclude unswept apps by design.

## Files

- `results.json` — machine-readable: candidates, per-app stages, labels, coverage.
- `scripts/run_reach_all.sh` — serial VM runner (superseded by parallel).
- `scripts/reach_par.sh` / `scripts/reach_swept.sh` — parallel workers (mkdir-claim
  locks, idempotent, resumable; swept-first variant).
- `scripts/aggregate_leverage.py` — label join + candidate×stage aggregation + ranking.
