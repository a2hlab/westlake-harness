# GENSHIN-T1 — bounded offline intake (status: MISSING in searched scope)

Contract: `specs/genshin-static-intake/t1-bounded-static-intake.spec.md` @ `0a52b42dd5`.
Runtime verdict: **NOT_TESTED**. Device operations: 0. Frozen changes: 0. No download/install/login/REA.

## What was wrong first (kept, not rewritten)

- `s01-index-grep`: a recursive `grep -ril` over index dirs descended into large binaries (corpus-v2, run-index,
  demo-baseline inputs) and was stopped by cc-video (TaskStop) on outer correction after >60 s; the outer loop sent no
  signal (`signal_sent=false`). Partial stdout/stderr (both 0 B) and
  argv are kept; actual rc unknown (`rc=null`) (the `.rc` file is a cancellation marker). It is **not** counted as coverage.
- `s05-files-name-siblings`: a zsh glob failure dropped every path argument, so rg only searched the private
  evidence directory. Kept, marked `INVALID_SCOPE`, excluded from coverage.
- `s09-boat-sources-sha-INVALID`: its `argv.json` was a hand-written placeholder, not a captured argv. Kept
  unchanged and marked invalid; superseded by `s10`/`s11`, which re-ran the read-only hashing through the
  argv-capturing recorder with ten explicit paths.

Rule set by this round: every receipt argv must be captured by the process launcher (`rec.sh`/subprocess),
never written afterwards; index searches use `rg --files` (names) or `rg -g '*.json|md|txt'` (text) only.

## Result

No Genshin base APK, split, OBB or asset was found **in the searched scope only**:

| Scope | Receipt | Result |
|---|---|---|
| `$WORKSPACES/westlake-inputs/**` filenames | s03 | no match (rc 1) |
| `$WORKSPACES/westlake-inputs/**/*.{json,md,txt}` ≤20 MB content, non-hidden text-index scope (no `--hidden`) | s04 | no match (rc 1) |
| `$WORKSPACES/00.Workspace/**`, `$WORKSPACES/vm-copies/**` filenames | s07 | no match (rc 1) |
| APK stores (westlake-inputs/apks, 00.Workspace/APKS, vm-copies/apks-77, demo-baseline originals), globs .apk/.apks/.xapk/.obb | s08 | 441 distinct APK/XAPK path entries (393 .apk + 48 .xapk, no OBB), none Genshin by name; not content/package deduplicated; manifests not read |
| repo text indexes | s06 | 2 doc pointers only: package `com.miHoYo.Yuanshen`, and a *remote* macserver Android emulator said to host Genshin |

**Not searched** (no claim about them): OrbStack `a2hlab`, hw248, the remote macserver, other `$WORKSPACES`
siblings (generations, worktrees, build dirs, tarballs), the rest of `$HOME`, and the manifests of the 441
APK/XAPK path entries (a renamed package would be missed). No `Westlake`/`real-work` directory exists under `$WORKSPACES`;
their location is UNKNOWN.

`input-index.json` and `static-matrix.json` therefore carry empty arrays plus the searched scope; every
Genshin dimension (version, SDK, ABI, JNI, DT_NEEDED, GLES/Vulkan/Unity) is UNKNOWN, nothing is PASS.

## BoatAttack comparison (reference only)

`boatattack-comparison.json` uses the six handoff sources (SHA prefixes a0f1b73e / 4c2b6a10 / c0550cd5 /
de5fa08b / e28f4bc3 / 87daed17, all re-verified in s10) plus t2b spec and provenance-closure:

- Reusable **candidates** (conditional on Genshin's own first fatal point landing there): shared bridge/runtime
  (f28bd1b3, archived rc0 build), JNI `RegisterNatives` graphics shim (Surface/BBQ/ANativeWindow↔OHNativeWindow),
  window-size/landscape session, touch projection mechanism (Boat coordinates are not reusable).
- **Not reusable**: C7 libunity / C4 libil2cpp app-private patched artifacts and Boat game logic.
- Boat's 61b acceptance (visual/touch with disclosed limits) is never Genshin evidence.

## Next action

Outer loop decides: supply an authorized Genshin base APK + splits/OBB, or authorize read-only filename search on
OrbStack a2hlab / hw248 / the remote macserver; then rerun t1 static reads on the exact SHA. Exact binary questions
go to Codex/OC, not REA here. No device task is proposed.

## Files

`results.json` (status, scope, elapsed 376 s / 900 s, limits, unknowns, next_action, command receipts with argv/rc/raw_refs),
`input-index.json`, `static-matrix.json`, `boatattack-comparison.json`, `source-index.json`.
Raw stdout/stderr/rc/argv live in `$GENSHIN_T1_PRIVATE` = `$HOME/.local/share/westlake/genshin-static-intake-20261021`
(each ref carries sha256 + size). Check: `cargo test --test genshin_static_intake` in `tools/spec-checks`.
