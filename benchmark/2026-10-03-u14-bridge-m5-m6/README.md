# U14 bridge M5 / M6 as single patches on e34de8ab: three reproducible builds, diffs confined to the patched functions; M5 alone does not move dddmodel2 and raises Surface-less dialogs for 3 watchlist keys

> **Correction (after the outer's review, see `../2026-10-03-u14-jar-v1/erratum-u14-bridge-m5-m6.md`):** the dddmodel2 "0" and the group-B "no Surface" conclusions below hold only on a runtime **without M1**. U14 runs the U13 runtime 18763dd4, whose compat shim already does M1 (`[M1-COPY]`), so under U14 dddmodel2 moves with M5 (+1, medium), all 13 dialog-first keys show their own dialog on top, and the bridge-side M1 (438bc948) is not needed.

#90, offline. Built on the Mac with the DevEco OH SDK; a2hlab was not used and nothing went to a board.

**What was built.** Three bridges, each built twice in fresh generation directories, both builds byte-identical:

| variant | patches on R1 R2 R3 | sha256 |
|---|---|---|
| e34de8ab + M5 | `win-m5-dialog-zlevel.patch` (`9caf89e8`) | **`07fd530aa4c29a1fe2dd22fcb191fc797bdb8350d808a41845baec0976c1eebf`** |
| e34de8ab + M6 | `adapter-m6-finishing-background.patch` (`bb479ec0`) | **`94cc67fad87598bf36abd6014e2cd438320e6b5df0d28e4d83a5894aa724d3cb`** |
| e34de8ab + M5 + M6 | both | **`7daa5435333ab99c2360dfe5ad5b75180ba0b8118d4f69f6750764c01b546452`** |
| optional: e34de8ab + M1 + M5 + M6 | + `win-m1-session-slots.patch` (`b292a37f`) | `438bc94831c9f3679138fe6d8aecc2f5302057d35eb814995ea4fc0f0fad236f` |

The M5 and M6 bytes equal last round's single-build `u14-r1r3-m5` / `u14-r1r3-m6`, and the optional one equals
`u14-r1r3-all`. The optional build exists because one of the three predicted moves (dddmodel2) needs M1 under M5; see below.

**Gates.** Every variant passes all three:
- the per-function diff lands only on the patched functions;
- 0 text strings are dropped;
- the open sites are identical to 84695d62 and e34de8ab.

**Predictions.**

| key | M5 | M6 | M5+M6 |
|---|---|---|---|
| fd-mobile | → its own WebView-outdated dialog | 0 | as M5 |
| dddmodel2 | **0** (needs M1 too) | 0 | 0 |
| fd-AppManager | 0 | white goes away; own splash at t20 medium-low | as M6 |

- With the optional M1 + M5 + M6 build, dddmodel2 moves too (+1).
- The 13 dialog-first lit keys stay lit with every variant. Three of them (privacyfriendly memory, pin, ruler) raise a
  dialog window that has **no Surface** without M1.

## 1. What changes, function by function (`proof/`, resolved instruction-level `equiv.py` from 2026-10-02-u14-bridge-r1r3)

| variant | vs e34de8ab (2708 functions) | vs 84695d62 (2696 common) |
|---|---|---|
| M5 | 1 differs: `OHWindowManagerClient::createSession` | baseline candidate's own set (`nativeGetDefaultDisplayWidth`, `ScheduleAbilityTransaction`: the two inert a-paths, 12 a-path-only functions) **+ `createSession`**. Nothing else. |
| M6 | 1 differs: `AbilitySchedulerAdapter::ScheduleAbilityTransaction` (`FgGuardTokenIsFinishing` and the changed `FgGuardShouldVeto` are anonymous-namespace helpers inlined into it) + 1 new function, the `_JNIEnv::CallStaticBooleanMethod` inline the helper instantiates | baseline set + `CallStaticBooleanMethod` (`ScheduleAbilityTransaction` is already in the baseline set for APK-ORIENTATION) |
| M5 + M6 | exactly the union: `createSession`, `ScheduleAbilityTransaction`, + `CallStaticBooleanMethod` | baseline set + `createSession` + `CallStaticBooleanMethod` |
| optional M1+M5+M6 | the above + M1's four: `publishProcessWindowTarget`, `getRSSurfaceNode`, `destroySession`, `oh_wm_get_native_window` | – |

"Baseline set" is `../2026-10-02-u14-bridge-r1r3/proof/equiv-846-vs-candidate.txt`. No variant drops or adds anything from
it beyond the listed patch functions (compared as sets).

## 2. Strings, imports, open sites (`diffs/`)

- **Strings** (`deployed_strings_diff.py`, classified by `strings_summary.py` → `strings-summary.txt`):
  - **0 text strings dropped** in any variant;
  - text strings added are exactly the patches' own: M5 `createSession: Android TYPE_APPLICATION window -> sub-window
    zLevel %{public}d`; M6 the HiLog `[IPC] … FGGUARD WARN pass-through BACKGROUND_NEW for finishing token=…` line plus
    `adapter.core.OhTokenRegistry`, `findByOhToken`, `isDestroying` and their two JNI signatures;
  - everything else is non-text layout bytes.
  - Against 84695d62 the baseline candidate's own diff is subtracted first.
- **Imports** (`imports-vs-e34de8ab.txt`):
  - NEEDED: identical, 35 entries in the same order;
  - one new undefined symbol, for M5 only: `WindowSessionProperty::SetSubWindowZLevel(int)`. It is defined by the
    board's `libwindow_scene_common.z.so` (`9551c7fe…`), which is a direct NEEDED of the bridge and the same library
    that already provides `WindowSessionProperty::SetWindowType`;
  - M6 adds no import.
- **Open sites** (`open_site_scan.py` → `open-sites.txt`): each of 84695d62, e34de8ab and the four variants has the
  same 3 sites, with the same functions, flags, paths and namespace:
  - `preload_libmali_global` dlopen NOW|GLOBAL;
  - `nativeRegisterInputChannel_impl` dlopen `liboh_android_runtime.so` NOW|NOLOAD, then NOW.
  - **No new open site.**

## 3. The prediction table (`predictions.csv`)

| key | today (U10.1T8) | first cause | M5 | M6 | M5+M6 |
|---|---|---|---|---|---|
| fd-mobile | black | own "WebView outdated" dialog 636 (has its Surface, alive at t20 1139×1920) under the empty Activity window 637 | **dialog on top: own WebView-fallback page (high)**. Functional lit still needs M2. | 0 | as M5 |
| dddmodel2 | white | dialog 686 under 687 **and 686 has no Surface** (3/3 lookups empty) | **0 (high)**: the raised 686 is empty | 0 | 0 |
| fd-AppManager | white | KeyStoreActivity's close dropped; its BACKGROUND_NEW is swallowed by FGGUARD; windowless scene 661 stays on top | 0 | **white goes away (medium); own splash at t20 (medium-low)**, chain below | as M6 |
| termux | white | same dropped-close shape, nothing below | 0 | its scene goes; t20 = launcher (not lit) | as M6 |
| 13 dialog-first lit keys | lit | – | re-stacked, still own UI (section 4) | 0 | as M5 |
| 34 lit keys with a dropped close under their top (`closes.csv` under_dropped) | lit | – | 0 | covered splash scenes are cleaned up ~13 s after their BACKGROUND ack; top unchanged (watch) | as M6 |

With the optional M1 + M5 + M6 build:
- dddmodel2 **+1**: M1 gives 686 its Surface, and M5 puts it on top. Medium; the dialog content is unknown.
- The 13 keys: every dialog that is alive at t20 is on top with its content.

### Why M5 alone does not move dddmodel2 (correction of the outer's "M5 → dddmodel2")

`white-unexplained-4` already wrote the condition as "M1 + M5". `dialog_surfaces.py` (→ `dialog-surfaces.txt/.json`)
shows why per session.
- dddmodel2 creates the dialog (686) first and the Activity window (687) second.
- Every cross-copy lookup of 686 comes back empty: the single V1/R3 slot already points at 687.
- So the dialog never gets a producer to draw into.
- M5 raises an empty window. Only M1's per-session slot gives 686 its Surface.

### How M6 reaches AppManager's caller (static: deployed oh-adapter-framework `2257b835` + OH 6.1 LTS source on hw248)

1. KeyStoreActivity `finish()` → `ActivityClientControllerAdapter.finishActivity` → `OhTokenRegistry.markDestroying`
   → `TerminateAbility`. All three registry methods the patch calls exist in 2257b835: `findByOhToken(J)`,
   `isDestroying(IBinder)` and `markDestroying(IBinder)`.
2. OH drops the close while FOREGROUND is pending (`pending state dropped CLOSE`), later dispatches BACKGROUND_NEW.
3. **M6:** that BACKGROUND_NEW is not vetoed (token is destroying). It goes to Java as STOPPED.
   `ActivityClientControllerAdapter.activityStopped` → `reportOhLifecycle(token, 10)` →
   `AbilityTransitionDone(BACKGROUND)` → AMS `CompleteBackground` → `Terminate` (INITIAL) for the ability on
   `terminateAbilityList_`.
4. **No Java path acknowledges INITIAL.** `reportOhLifecycle` has exactly three callers: paused (1), resumed (9),
   stopped (10).
   - So AMS finishes the terminate itself: `Terminate(task)` with the terminate timeout,
     `TERMINATE_TIMEOUT_MULTIPLE` 10 × `timeout_unit_time` 1000 ms.
   - Then `DelayCompleteTerminate` waits `KILL_TIMEOUT_MULTIPLE` 3 × 1000 ms, then `CompleteTerminate`.
   - Source: `ui_ability_lifecycle_manager.cpp` (sha 678c5e00), `global_constant.h`, `ams_service_config.json`.
   - That is ≈ 13 s after the BACKGROUND acknowledgement. In the U10.1T8 signing run, KeyStoreActivity's BACKGROUND
     was dispatched at 16:52:53.877 (board clock), so the scene would go at ≈ 16:53:06.9.
   - The t20 screenshot was taken at 16:53:12.1 (host clock, `record.json`): a ≈ 5 s margin, if the two clocks agree.
5. **What then shows is not settled statically.** SplashActivity's own BACKGROUND_NEW is still vetoed: it is not
   finishing, and it falls inside the grace window. So in Java it is still resumed, while SceneBoard has backgrounded
   its scene.
   - If SceneBoard re-activates the caller when the top scene goes: own splash (lit).
   - If not: the launcher (not lit).
   - Hence "medium-low".

## 4. The 13 dialog-first lit keys under M5 (`watchlist-m5.csv`; extends cc-wiki's master 84fe19ab4d list)

cc-wiki's list assumes M1 + M5. Without M1, what M5 raises depends on whether each dialog session got its Surface.
`dialog_surfaces.py` replays every lookup in the signed run and reads each window's existence and rect from that run's
`windows-t20.txt`:

| group | keys | dialog Surface without M1 | expected t20 with M5 / M5+M6 |
|---|---|---|---|
| **A** (7) | newpipe, opencamera, fd-netguard, fd-stk, rpn, diaspora, listmaker | all lookups rescued; dialog alive at t20 (1139×1920; diaspora 1200×1920) | **own dialog on top of the Activity** (own UI, lit) |
| **C** (2) | beecount (615 empty, 616 ok), timetable (899 empty, 900 ok) | earlier dialog empty, later one has its Surface; both alive | **own dialog (616 / 900) on top**; the empty earlier one is raised too but stays under it (same zLevel, creation order) |
| **B** (3) | privacyfriendly memory (603, 1139×1118), pin (590, 1139×478), ruler (606, 1139×831) | **all lookups empty**: the dialog never drew | the raised dialog window is **empty**. Expected: Activity UI still visible. If the board shows a blank dialog-sized rect over the Activity, it is this window: still own UI, still lit. With M1 it becomes the app's first-launch dialog. |
| **D** (1) | trickytripper | dialog 579 has its Surface | the run's t20 dump has no app window rows, so whether the dialog is still up at t20 is unknown: own dialog on top, or unchanged |

**Every one of the 13 is expected to stay lit (own UI) under M5, M5+M6 and M1+M5+M6.** M6 alone leaves their t20
as it is.

The sign-off rule does not change: a regression is a white or black t20, or a non-app surface. A different own-UI layer
on top is not a regression.

**Statically unsettled for group B: how does an empty window raised above content render?** The population has no
case of it. The only runs whose top live window had no Surface are the M1-white noice and fd-uhabits (`top-empty.txt`).
In both, the empty window was the app's only window, so it says nothing about an empty sub-window over content. The
first M5 board run settles it from the screenshots of memory, pin and ruler.

**Recommendation.** Ship M5 together with M1 (the optional `438bc948`), not alone. M1 is what gives the B/C dialogs
and dddmodel2's dialog their Surface. M1's own static proof (`2026-10-02-m1-session-slots`, 367 lookups, 0 violations)
already lists exactly these sessions as "empty → rescued".

## Board watch lines

- **M5:** `createSession: Android TYPE_APPLICATION window -> sub-window zLevel 13000`, once per type-2 window; then the
  dialog's SceneBoard `UpdateZOrderInner` zOrder is above its Activity's.
- **M6:**
  - `[IPC] FGGUARD WARN pass-through BACKGROUND_NEW for finishing token=…` (HiLog, visible);
  - then AMS `CompleteBackground`, `close ability by scb timeout` / `delay complete terminate task`, and
    `CompleteTerminate` for the finishing ability before t20.
- Both log lines go through HiLog, so unlike the bridge's `__android_log_print` lines they reach hilog.

## What was wrong before

1. **"M5 → dddmodel2"** dropped `white-unexplained-4`'s "with M1" condition. Without M1, the dialog M5 raises has no
   Surface. Stated per key now, with the lookup replay as evidence.
2. **cc-wiki's M5 watchlist assumed every dialog has content.** 3 of its 13 dialogs (and 1 of the 2 dialogs of beecount
   and of timetable) never got a Surface without M1. Their post-M5 picture is "Activity, maybe with an empty rect", not
   "own dialog".
3. **On this Mac, bare `diff` is DevEco's `toolchains/diff` (earlier on PATH than `/usr/bin`). It exits 0 even when
   the files differ, and on unknown options.** A shell check like `diff a b && echo same` always passes. This round
   caught it and redid the NEEDED and open-site comparisons with `/usr/bin/diff` and Python. `scripts/lab` has no gate
   that uses bare `diff`.

## Rules this round sets

- **A stacking fix's prediction must check the raised window's Surface.** For every window M5-type fixes raise, check
  in the run's lookups that it actually has a producer (`dialog_surfaces.py`). A raised window with no Surface does not
  show the app's UI.
- **In shell checks on the Mac, call `/usr/bin/diff` (or compare in Python), never bare `diff`.**

## Files

- `build_m5m6.sh`: wraps `../2026-10-02-u14-bridge-r1r3/build_r1r3.sh`.
  - Default: the three variants, twice each.
  - `WITH_M1=1 [ONLY_M1=1]`: the optional fourth.
  - Generations `$WORKSPACES/westlake-inputs/generations/u14-m5m6-{m5,m6,m5m6,m1m5m6}-{a,b}`, each with its teed
    `logs/patches-*.log` and `logs/build-*.log`, plus `u14-m5m6-SHA256SUMS`.
  - Source: master `bms/src/adapter` tree `5a847d96`. Master advanced during the builds (`a16b674d` … `8f99da9c`), with
    the same tree at every commit. Window cohort oh61-v7 `f6a498d1`, fn03 `fn03-core-846-recon-v1`.
- `proof/equiv-{e34de8ab,84695d62}-vs-{m5,m6,m5m6,m1m5m6}.txt`.
- `diffs/`: `strings-*.txt`, `strings-summary.txt`, `imports-vs-e34de8ab.txt`, `open-sites.txt`.
- `dialog_surfaces.py` → `dialog-surfaces.{txt,json}`; `top_empty.py` → `top-empty.txt`; `strings_summary.py`.
- `predictions.csv`, `watchlist-m5.csv`, `results.json`.
