# U14 plan draft: hardened bridge baseline, then M1 / M5 / M6, one file each

Status: draft for the outer loop. Nothing here has run on a board. Everything was built offline. The facts behind each
step are in `README.md`.

## Rules for every U14 step

- Swap **only the bridge** (`liboh_adapter_bridge.so`). Runtime, JARs, ANL, host and installer stay at the U12/U13
  unified state.
- Each step is a **separate file** (patch or new source file) on top of the previous step. Each has its own build
  (`build_u14_bridge.sh`, log teed into the generation directory) and its own diff against 846 (`diffs.sh` + `fnsize.py`).
  Before any board use the diff must show **only** the step's intended functions.
- Every JNIEnv acquisition added in the window cohort uses plain `GetEnv`, attaching only on `JNI_EDETACHED`, like the
  846 ctor. **No `westlake::jni::ScopedJniAttachment` in `SessionStageAdapter` / `OHWindowManagerClient`** (DIGEST 557:
  that WLTG gate on the createSession thread killed every app in B1).
  - Static gate: `nm` call-set of every new or changed window-cohort function must not reference
    `ScopedJniAttachment` / `WLTG_*`.
- Build host: the Mac with the DevEco OH SDK (about 1 minute per build). a2hlab is not needed.

## Step 0: land the inputs so the repo builds the bridge alone (outer / cx-bms; `bms/src` is outside `land.py`)

- Copy `$WORKSPACES/westlake-inputs/sources/oh61-v7-b2133b5b-f6a498d1/framework/window/jni/` (window cohort tree hash
  7a60e05b5e9e72f6) into `bms/src/adapter/sources/oh61-v7-b2133b5b/framework/window/jni/`. Leave out
  `oh_anativewindow_shim.cpp.bak-unity`.
- Copy `fn03-core-846-recon-v1/` into `…/sources/oh61-v7-b2133b5b/framework/activity/core/`.
- These are the recipe's default paths, so `OH61_WINDOW_SOURCE_ROOT` / `OH61_ACTIVITY_CORE_ROOT` no longer need overrides.
- Acceptance: a build from the landed tree gives `9a03b272…` (v3).

## Step 1: new baseline bridge = v3 + restore pack (3 files)

| file | content | source | acceptance (offline) |
|---|---|---|---|
| `u14-r1-focus-bridge.patch` (`session_stage_adapter.{h,cpp}`) | members `focusBridgeClass_`, `focusBridgeObj_`, `inheritsParentFocus_`; `SetInheritsParentFocus`; `callFocusBridgeVoidMethod`; WindowCallbackBridge creation in the ctor and release in the dtor; `UpdateFocus` / `SetActive` routed to `onUpdateFocusStatus(Z)` | real-work `framework/window/jni/session_stage_adapter.{h,cpp}` 0765bc53 (bodies only; JNIEnv per the rule above) | `SessionStageAdapter` sizes = 846 (138 functions); construction-vtable drift gone; R1 rows of `difflist` gone |
| `u14-r2-root-blast.patch` (`session_stage_adapter.cpp`, `oh_window_manager_client.cpp`) | `EnableRootBlastForTopLevelContent`; in `createSession`'s top-level block: `SetInheritsParentFocus(true)`, refuse with `wsErr 1001` when root BLAST fails | 0765bc53 lines 139-225; real-work `oh_window_manager_client.cpp` 0b816fe6:495-500 | `EnableRootBlastForTopLevelContent` size = 846 (1372 B); R2 strings back |
| `u14-r3-rs-node-holder.patch` (`oh_window_manager_client.cpp`) | **rewrite**, 846-faithful single slot. `publishProcessWindowTarget(id, target, node)` also keeps a heap `shared_ptr<RSSurfaceNode>` in a process vector and sets `WESTLAKE_RS_SURFACE_NODE_HOLDER_PTR_V1`. `getRSSurfaceNode` falls back to that holder when the id matches `WESTLAKE_WINDOW_SESSION_ID_V1` (copies the `shared_ptr`, logs `acquired process-published cross-namespace surface …` / `no local or process-published RSSurfaceNode …`). `destroySession` unsets the three variables when the id matches. | in no local tree; written from 846's call graphs (`diff-v3/abi-diff`, disassembly in README) | `publishProcessWindowTarget` / `getRSSurfaceNode` / `destroySession` sizes close to 846 (452 / 728 / 772 B); exports and undefined lists = 846 apart from the a-paths |

**Expected baseline diff:** only the two inert a-paths (OH-DISPLAY-EVENT, APK-ORIENTATION + Capybara) and the
versioned `__android_log_*`. It is useful to also build a variant with the two a-paths compiled out, as a purity
check. If the board comparison regresses, that variant tells "a-path" from "build chain" in one window.

**Board, first U14 window (≤ 45 min batch, one board, only the bridge swapped):**
- full 166-key comparison against the U10.1T8/U12 unified-state facts of that board's shard, then the other shards;
- pass = t20 lit set not smaller, and for every regressed key the first fatal point is outside the bridge;
- watch-list:
  - the `bound … MainSession` / `acquired process-published` counts match the U10.1T8 numbers (131 / 131);
  - bridge ALOG lines still appear (symbol versioning);
  - `[OH-DISPLAY-EVENT] dispatchDisplayEvent(int) unavailable` appears once per process, and nothing else from it.

## Step 2: M1 bridge version (`u14-m1-session-slots.patch`)

- Base: `2026-10-02-m1-session-slots/bridge-m1.patch`, ported to the snapshot client.
  - 2 of 3 hunks apply as is (offset −14).
  - The `destroySession` hunk must be moved to the snapshot's `destroySession` (line 640): there it joins R3's unset block.
- **Extend it to the R3 holder.** Add `WESTLAKE_RS_SURFACE_NODE_HOLDER_PTR_V2_<id>` next to the window-pointer
  `…_V2_<id>`. The 11 U10.1T8 runs with `no local or process-published RSSurfaceNode` are exactly M1's population
  (`usage-b.csv`), so per-session window pointers alone would still leave those windows without an RSSurfaceNode.
- Prediction: `2026-10-02-m1-session-slots/predictions.csv` (white → lit: noice, fd-uhabits; lottery: wikipedia,
  fd-noice; plus the lit regression-watch list).

## Step 3: M5, dialog above its Activity (`u14-m5-dialog-zlevel.patch`)

- Site: snapshot `createSession`, top-level block (`isAndroidTopLevel` = Android types 1/2/3). Every top-level Android
  window is bound as an `APP_SUB_WINDOW` of the MainSession with zLevel 0, so SceneBoard stacks them by creation order.
- Change: give type-2 (`TYPE_APPLICATION`, dialogs) windows a higher sub-window zLevel than the type-1 base window
  (`WindowSessionProperty::SetSubWindowZLevel`, `window_session_property.h:255`).
- **Offline check first:** OH honours sub-window zLevel only when `SystemSessionConfig.supportZLevel_` is set
  (`window_session_property.h:936`). Read how OH 6.1 SceneBoard uses it (hw248 `/opt/build-trees/oh610_lts_source`)
  before writing the patch. If phones do not support it, the alternative is re-raising the dialog after the Activity
  window connects.
- Prediction (`2026-10-02-white-unexplained-4`): +1 dddmodel2 (with M1), +1 fd-mobile WebView-fallback page. Watch the
  13 lit keys that create a dialog before their Activity window.

## Step 4: M6, acknowledge BACKGROUND / INITIAL (`u14-m6-background-ack.patch`)

- Site: master `framework/activity/jni/ability_scheduler_adapter.cpp`, already 846-identical (84/85 functions; the 85th
  is APK-ORIENTATION).
- Change:
  - deliver `BACKGROUND_NEW` and `INITIAL` transactions to Java for a finishing Activity (no FGGUARD veto when the
    Activity is finishing);
  - make sure the app acknowledges them (`AbilityTransitionDone`), so that AMS `CompleteBackground` → `Terminate` →
    `CompleteTerminate` runs.
- First, find why U10.1T8 logs **0** `[BRIDGED] ScheduleAbilityTransaction` lines. Either the transactions do not reach
  this scheduler at all (registration / scheduler identity) or they reach the other bridge copy. That decides whether
  the patch goes into the scheduler or the registration.
- Prediction (`2026-10-02-white-m6-finish-return`): +1 fd-AppManager (medium). The 34 lit keys with leaked
  under-scenes get cleaned up (no t20 change expected).

## Order and windows

0 → 1 (+ board comparison) → 2 → 3 → 4. Steps 2–4 are merged into **one** U14 native candidate (one native version per
round). Each step's patch stays a separate file, so a regression can be bisected by dropping one patch.
