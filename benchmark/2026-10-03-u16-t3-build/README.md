# U16 t3 build — AppSchedulerBridge launch-transaction ON_START sync (oc-t4, offline)

Per `specs/u16-batch/t3-lifecycle-sync.spec.md` + cc-wiki's
`benchmark/2026-10-03-u16-t3-lifecycle-sync/` (patch + design note + risk set). Offline build
only; **not boarded** (board verification goes with the 4 native-engine risk keys:
fd-minetest, fd-mpv, fd-organicmaps, fd-stk).

## Base (verified, not from memory)

`$WORKSPACES/westlake-inputs/generations/u15-jar-v1/oh-adapter-runtime-u15-v1.jar`
= `20e748e57c6ee8bd…` — matches the U15-on-U14 `increments.csv` candidate SHA for
`/system/android/framework/oh-adapter-runtime.jar`.

## The change (smali needle, unique hit)

In `AppSchedulerBridge.nativeOnScheduleLaunchAbility`, immediately after the launch
`ClientTransaction.addCallback(launchItem)` (`.line 1696`):

    invoke-static {}, Landroid/app/servertransaction/StartActivityItem;->obtain(Landroid/app/ActivityOptions;)Landroid/app/servertransaction/StartActivityItem;
    move-result-object v3
    invoke-virtual {v1, v3}, Landroid/app/servertransaction/ClientTransaction;->setLifecycleStateRequest(Landroid/app/servertransaction/ClientTransactionItem;)V

= cc-wiki's patch: `StartActivityItem.getTargetState() == ON_START`, so onCreate → onStart run
synchronously in one main-thread transaction (AOSP `handleLaunchActivity` order) and fragment
views (breezyweather's lateinit `weatherView`) are assigned before the Looper resumes.
**onResume stays phase-2** (G2.14m AMS handshake untouched). Needle count asserted == 1 before
insert (build refuses otherwise).

## Deterministic build (t1 recipe) — GATE

baksmali → needle patch → **`smali assemble --jobs 1 -a 29`** (jcommander 1.64 on the CP;
1.78's PositiveInteger crashes on JDK 21) → python-zipfile repack onto the base jar
(classes.dex STORED, **all timestamps 1980-01-01**). Passes A and B: **jar byte-identical
(True)**. `build.sh` in this dir reproduces the canonical artifact bit-for-bit.

## Gates

- **deployed_class_diff --frozen** vs U15 `20e748e5` (class-diff.txt, verbatim):
  `0 dropped, 0 reshaped, 0 added (after allow lists), 0 frozen class(es) broken` (224 → 224 classes).
- **smali-level file comparison** (candidate re-disassembly vs base disassembly): exactly
  **1 changed file** — `adapter/activity/AppSchedulerBridge.smali`; 0 dropped, 0 added. The
  change is the needle block above (method-body only; no other file touched).

## Files

- `oh-adapter-runtime-u16-t3.jar` — the artifact (not in landing-paths; ships via the U16
  generation bundle; board verification pending with the 4 risk keys)
- `build.sh` — deterministic build script (t1 recipe)
- `class-diff.txt` — deployed_class_diff --frozen output
- `README.md`, `landing-paths.txt`
