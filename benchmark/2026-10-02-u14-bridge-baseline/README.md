# U14 bridge baseline: master builds a bridge that is 2490/2499 functions identical to the deployed 84695d62; the rest is three restorable 846 features and two inert master additions

#90, offline. Nothing was deployed to a board. The question: can the bridge be rebuilt from master's `bms/src` plus the oh61-v7
window snapshot, and how does that rebuild differ from the deployed `liboh_adapter_bridge.so` 84695d62, which has no
reproducible source? The three bridge-only fixes (M1 bridge version, M5, M6) need that baseline first.

**Answer.**
- **It builds, reproducibly.**
  - Inputs: master `bms/src/adapter` (cx-bms sources 4d5cac38ff, fail-loud scripts 9c14005a01), the persistent oh61-v7
    window snapshot, and a reconstructed fn03 core.
  - The hardened recipe compiles 50/50 TUs with the strict link.
  - The result is `9a03b272…` ("v3"). Two independent full builds, at master 31347d2d and 601b6945 (`bms/src/adapter`
    is unchanged between them), give the same SHA.
- **It is close to 846, and every difference is accounted for.**
  - Of the 2499 functions both binaries define, 2490 have the same size. All 139 fn03 functions match.
  - The remaining 9 size differences, 8 deployed-only and 11 rebuilt-only functions fall into five features (table below).
  - Exports: 2357 → 2356 (−5 / +4), 0 consumer breaks against runtime ac59dec0 and U13 18763dd4.
  - Attribution of all 92 diff items: a 29, b 41, c 1 (an app-specific package string), plus 21 layout noise.
- **The b class is not optional.** Two of the three missing 846 features are on the main path:
  - **R3**, the cross-copy RSSurfaceNode lookup, ran in **131 of 133** U10.1T8 signing runs: all 117 lit, 14 of 16 white.
  - **R2**, root BLAST, sits on every `createSession`.
  - So v3 itself is **not** the board baseline. The baseline is v3 plus the restore pack R1–R3 (see `u14-plan.md`).
- **The a class moves 0 keys** with the U13 jars. Both new master paths look for a Java peer that the jars do not
  have and return.

## The builds

| build | fn03 cohort | artifact | exports (846 = 2357) | same-size functions / common | diff items a / b / c / layout |
|---|---|---|---|---|---|
| v1 | oh61-v7 snapshot `dd57a00b` | `2f3bc923` | 2384 (−6 / +33) | 2472 / 2497 | 30 / 41 / **42** / 30 |
| v2 | bms-deploy `.work/b6-r155` `1f5986de` | `d693b2ae` | 2356 (−5 / +4) | 2489 / 2499 | 29 / 41 / **5** / 20 |
| **v3** | **reconstruction** `021e5bc0` = 1f5986de + 4 hunks | **`9a03b272`** | 2356 (−5 / +4) | **2490 / 2499** (fn03 139/139) | 29 / 41 / **1** / 21 |

Each build was repeated with a fresh `GEN` directory and gave the same SHA (v1, v2, v3). Build logs are teed while the
build runs, to `$WORKSPACES/westlake-inputs/generations/u14-bridge-v*/logs/`. In `u14-bridge-v1`, the first three logs
are environment failures (header mirror path, a shallow OH-root merge), fixed and not counted as build rounds.

**The 846 fn03 is neither known version.**
- 846 `.rodata` has `fn03-lifecycle-mapping-v2` and `UNSUPPORTED_OH_STAGE_STATE` (both only in dd57a00b).
- It also has `OH_CLEAN_REPLAY` (only in 1f5986de).
- It has **none** of the 16 reason codes found only in dd57a00b (`RETIRED_ACTIVITY_GENERATION`, `FIRST_FRAME_TRANSITION_*`, …).
- So it is 1f5986de plus the dd57 "kInactive is not an OH stage state" change and nothing else. That change is 4 hunks
  (`fn03-846-recon.patch`):
  - mapping version v2;
  - `DecideMapping` rejects `kInactive`;
  - A03 and the Resumed→Pause mapping keyed on `kForeground`.
- With those hunks, all 139 fn03 functions match 846 in size and the `DecideMapping` call-set difference disappears.
- This is a reconstruction checked against the binary, not a recovered file. It is stored at
  `$WORKSPACES/westlake-inputs/sources/fn03-core-846-recon-v1/`, with `.SHA256SUMS`, `.SOURCE.txt` and the patch.

## Persistent inputs (all outside the shared `.work` trees)

- **`westlake-inputs/sources/oh61-v7-b2133b5b-f6a498d1/`**
  - The window/fn03 snapshot: 14084 files, tree hash f6a498d193b1ca32.
  - Copied from real-work `src/adapter/sources/oh61-v7-b2133b5b`, which is identical to bms-deploy `.work/b87-native`.
  - Contains `local_oh_headers/oh_mirror`.
  - `f716a86d89` had reported it missing from `bms/src`.
- **`westlake-inputs/sources/fn03-core-b6r155-1f5986de/`** and **`fn03-core-846-recon-v1/`**.
- Link inputs, the generated header and the WLTG registry are copied into each generation directory and hashed in its
  log (`[u14] input …`). The libc used is the board's ld-musl (it defines `__cfi_slowpath`).
- Builds run **on the Mac** with the DevEco OH SDK (`FORCE_OH_SDK=1`, the route cc-wiki's B1 used), not on a2hlab. The
  a2hlab reboot at about 23:05 did not touch them: the last build used here ended at 22:58:32 and its repeat ran at
  23:13–23:14.

## The difference list (`difflist-v3.csv`, from `attribute.py` over `diff-v3/`)

`fnsize-846-vs-v3.txt` gives the same picture per function. Every size difference and every deployed-only or
rebuilt-only function belongs to one of these rows.

| feature | class | where it shows | 846 behaviour | v3 behaviour |
|---|---|---|---|---|
| **R1 focus bridge** | b, port | `SessionStageAdapter` ctor 1420→920 B, dtor, `SetActive`, `UpdateFocus`; `callFocusBridgeVoidMethod` and `SetInheritsParentFocus` only in 846; +24 B object layout (construction-vtable drift) | OH focus → `WindowCallbackBridge.onUpdateFocusStatus` → `dispatchWindowFocusChanged` (framework jar 2257b835) | focus → `SessionStageBridge.onUpdateFocus`, which in Java only logs "Android handles via ViewRootImpl.windowFocusChanged": **no window focus reaches the app** |
| **R2 root BLAST** | b, port | `EnableRootBlastForTopLevelContent` only in 846; `createSession` calls it and refuses a null-BBQ ViewRoot (`wsErr 1001`) | sets `ViewRootImpl.mUseBLASTAdapter` before the first relayout | never set. Per the source comment, `WindowSessionAdapter` cannot return `ADD_FLAG_USE_BLAST`, so no-buffer frame-commit callbacks see a null `mBlastBufferQueue` |
| **R3 process-published RSSurfaceNode** | b, **rewrite** | `publishProcessWindowTarget` (846 takes the node as a 3rd argument and stores a heap `shared_ptr` holder in a vector; setenv ×3); `getRSSurfaceNode` 728→332 B (846: `getenv`/`strtol`/`strtoull` fallback); `destroySession` 772→588 B (846: `unsetenv` ×3); string `WESTLAKE_RS_SURFACE_NODE_HOLDER_PTR_V1` | the bridge copy that did not create the session (compat shim, other namespace, M1) still gets the RSSurfaceNode | `getRSSurfaceNode: unknown sessionId` → that copy has no RSSurfaceNode |
| OH-DISPLAY-EVENT (display_manager framework copy) | a | `nativeGetDefaultDisplayWidth` 140→1068 B; `AndroidDisplayListener`, `dispatchDisplayEvent` only in v3 | – | once per process, loads `adapter.activity.DisplayManagerProjectionProxy` and looks up static `dispatchDisplayEvent(I)V`. Runtime 0482c9b1 has the class **without that method** (dexdump), so it logs `dispatchDisplayEvent(int) unavailable` and returns before `RegisterDisplayListener`: **inert** |
| APK-ORIENTATION + Capybara (master `ability_scheduler_adapter.cpp`) | a (+1 c string) | `ScheduleAbilityTransaction` 1208→2352 B; `WindowSessionProperty::SetPersistentId` / `SetRequestedOrientation`, `iface_cast<ISession>`, `CallStaticIntMethod` | – | per transaction: `ScopedJniAttach` and load of `adapter.activity.ManifestOrientationProjection`, which is in **neither** U13 jar → −1 → no property update: **inert**. Capybara branch: package not among the 166 keys |
| strict-link symbol versions | a | `__android_log_print@LIBC`, `__android_log_set_logger@LIBC` (846: unversioned) | – | bound to the board libc's versioned definition; check on board that bridge ALOG lines still appear |
| layout noise | – | jump-table / eh_frame bytes in `.rodata`, `RSSurfaceNode` holder-vector template instantiations (go away with R3) | | |

**Correction of my own earlier draft.** The `WindowSessionProperty` imports had been put in b as "the snapshot
`createSession` sets them". They come from master's APK-ORIENTATION block (`ability_scheduler_adapter.cpp:456-457`), so
they are class a. The rule is fixed in `attribute.py`.

## How much of the 166 keys runs each path (`usage_b.py` → `usage-b.csv`, U10.1T8 signing runs, 846-only log lines)

| path | runs with ≥ 1 line (lit 117 / white 16) | meaning for U14 |
|---|---|---|
| R2/R3 `createSession: bound Android top-level content to OH MainSession` (follows the EnableRootBlast check) | 117 / 14 | root BLAST ran and succeeded in every key that created a window. Only termux and toutiao create none. |
| R3 `getRSSurfaceNode: acquired process-published cross-namespace surface` | **117 / 14** | without R3, every one of these keys loses its RSSurfaceNode in the second bridge copy: **drop R3 = all keys at risk** |
| R3 `no local or process-published RSSurfaceNode` | 8 / 3 | wikipedia, noice, fd-uhabits, dddmodel2, timetable, studytracker, beecount, secuso memory/pin/ruler, fd-seal: **exactly M1's population** (`2026-10-02-m1-session-slots/predictions.csv`). The RS-node holder has the same single-slot defect as the window pointer. |
| R1 errors (`callFocusBridgeVoidMethod(…)`, `WindowCallbackBridge` ctor) | 0 / 0 | R1 logs only on failure: it ran silently, never failed |

## b: rewrite or drop

| item | recommendation | why |
|---|---|---|
| R1 focus bridge | **port**: `SetInheritsParentFocus`, `callFocusBridgeVoidMethod`, the focus-bridge part of ctor/dtor, `UpdateFocus`/`SetActive` routing, and the 3 members in the header, from real-work `framework/window/jni/session_stage_adapter.{h,cpp}` (0765bc53) | the source exists. But that file's ctor and `EnableRootBlast` use `westlake::jni::ScopedJniAttachment`, the WLTG-gated attach that killed every app in B1 (DIGEST 557). Take the function bodies onto v3's plain `getJNIEnv` (GetEnv, attach only on EDETACHED), the cc-wiki B2 `ctorfix` precedent. Without R1 no app gets `windowFocusChanged`. |
| R2 root BLAST + refusal | **port**: `EnableRootBlastForTopLevelContent` from 0765bc53, same JNIEnv rule; the 6 `createSession` lines (`SetInheritsParentFocus(true)`; refuse with 1001 if root BLAST fails) from real-work `oh_window_manager_client.cpp` 0b816fe6:495-500 | ran in 131/133 runs |
| R3 process-published RSSurfaceNode | **rewrite**, 846-faithful first: single slot, env `WESTLAKE_RS_SURFACE_NODE_HOLDER_PTR_V1`, holder = heap `shared_ptr<RSSurfaceNode>` kept in a process vector; the acquire copies the `shared_ptr`; `destroySession` clears the three variables when the id matches | in no local tree (bms-deploy `.work`, real-work, 00.Workspace, cc-wiki B1). 846's three functions are small (452 + 728 + 772 B) and their call graphs are known (`diff-v3/abi-diff`). Required for 131/133 runs. M1 then widens it per session. |

## a: predicted effect on the 166 keys (`impact-a.csv`, `impact-a.txt`)

| path | keys that reach it | predicted change with U13 jars | if the Java peer is added later |
|---|---|---|---|
| OH-DISPLAY-EVENT | every key that asks `DisplayManagerAdapter` for the display size (all that start) | **0**: no `dispatchDisplayEvent(I)V` → no listener; one cleared `NoSuchMethodError` + one log per process | OH display add/remove/change events would be forwarded to Java |
| APK-ORIENTATION | keys whose abilities get `ScheduleAbilityTransaction` (U10.1T8: 0 `[BRIDGED]` lines, M6) | **0**: peer class absent → `-1` → no `UpdateSessionPropertyByAction`; one extra WLTG attach scope and a cleared `ClassNotFoundException` per transaction | landscape MainSession for **fd-minetest, fd-stk** (sensorLandscape). Portrait/sensorPortrait (18 keys) would set what the board already shows. 144 unspecified + user/fullUser unchanged. |
| Capybara | none of the 166 | 0 | – |

## What the plan needs (full draft in `u14-plan.md`)

1. Land the window cohort and the fn03 reconstruction into `bms/src/adapter/sources/oh61-v7-b2133b5b/` (the recipe's
   default path). Then the bridge builds from the repo alone. This is a `bms/src` landing, so it is for the outer /
   cx-bms; `land.py` refuses it here.
2. The restore pack R1/R2/R3 as their own files on top. The board baseline is v3 + R1–R3, and it must match 846 at
   function level except for the two inert a-paths.
3. Then M1, M5 and M6 as separate patches.
   - **M1** (`bridge-m1.patch`) was written against master's older window client. 2 of 3 hunks apply to the snapshot
     client; the `destroySession` hunk needs moving. It must also cover the R3 holder.
   - **M6**'s site, `AbilitySchedulerAdapter`, is already 846-identical in master: 84/85 functions, the 85th being
     APK-ORIENTATION.

## Rules this round sets

- **Deployed code with no source: fingerprint each function, then reconstruct.** "No source" for a deployed component
  is not a reason to stop at a symbol diff. Compare per-function sizes between the deployed and rebuilt binaries
  (`fnsize.py`). Where version-specific strings place the deployed code between two known versions, reconstruct the
  smallest delta and accept it only when every function size matches (fn03: 139/139).
- **Judge a dropped feature by runtime use, not by the diff.** Before saying "drop", count how many keys executed the
  846-only path from its own log lines (`usage_b.py`). R3 looked like a niche cross-namespace fallback and runs in 131
  of 133 keys.
- **A peer-gated native path is inert until both halves exist.** A new native path that loads a Java peer by name is
  inert until the class **and** the exact method signature exist in the jar that runs. Check with dexdump, not with
  the class name alone: `DisplayManagerProjectionProxy` exists, `dispatchDisplayEvent(I)V` does not.

## Files

- `build_u14_bridge.sh`: the build. Persistent inputs, recipe verbatim, log teed. Env: `GEN`, `FN03_ROOT`, `WINDOW_ROOT`.
- `diffs.sh`: `abi_diff` (+ consumers ac59dec0 / 18763dd4, `--calls`), NEEDED/undefined, `deployed_strings_diff`
  → `diff-v{1,2,3}/`.
- `attribute.py` → `difflist-v{1,2,3}.csv`: per-item class, source file and action.
- `fnsize.py` → `fnsize-846-vs-v{1,2,3}.txt`.
- `usage_b.py` → `usage-b.csv`, `usage-b.txt`.
- `impact_a.py` → `impact-a.csv`, `impact-a.txt`.
- `fn03-846-recon.patch`: the 4 hunks.
- `u14-plan.md`: the U14 plan draft.
- `results.json`.
