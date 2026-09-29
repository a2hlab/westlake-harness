# 2026-09-29 Wikipedia line (B11, cc-wiki) — route-A first-screen bring-up on 5ea

Evidence-first log of the Wikipedia专线 on 5ea (v3a+r8b). Ground truth = screenshots.

## Rounds
- **R1 (r13 JAR)**: cc-t3 r13 (activity-level theme + service stubs) bind-mounted over
  `oh-adapter-runtime.jar` (SHA f1325297). Cleared the #78 theme wall
  (`Attribute not found; ID=2130969834` gone; theme 0x7f130026 resolves). New wall:
  `MainActivity.onGoOffline` → `MainFragment.getCurrentFragment()` NPE → System.exit(1),
  on the main thread. Screenshot = OH desktop (NOT lit). See `results.json` rounds[0].
- **R2 (connectivity)**: root cause proven — board `adapter-mainline-stubs.jar`
  `android.net.ConnectivityManager` reports offline (getActiveNetwork→null,
  registerDefaultNetworkCallback→no-op). Fix jar `mls-online.jar` (SHA 83c5ef21) built +
  verified (Westlake online android.net stubs). Deploy blocked by AOT boot image →
  needs an oat230 boot-image rebuild (cx-t0). See `CONNECTIVITY-BOOT-IMAGE-HANDOFF.md`.

## Files
- `results.json` — machine-readable rounds + divergences.
- `r2-investigation.md` — artifact map + interface-loadability audit.
- `CONNECTIVITY-BOOT-IMAGE-HANDOFF.md` — full recipe + inputs for cx-t0.
- `build_mls_online.py` — builds the online android.net mainline-stubs jar.
- `deploy_jar.sh` — locked single-file JAR overlay (baseline + one-umount rollback).
- `runs/` — bms_batch run dirs (screenshots/hilog/record; jpegs+hilog gitignored).

Screenshots + large hilogs are gitignored; key screenshots go via `git add -f` when the
outer ring signs off a lit page.
