# U14 bridge baseline candidate: R1/R2/R3 restore 846's code instruction for instruction; M1/M5/M6 as separate patches on top

#90, offline. Nothing was deployed to a board. Builds ran on the Mac with the DevEco OH SDK; a2hlab was not used.

The previous round (`2026-10-02-u14-bridge-baseline`) found three 846 features missing from the buildable cohort:
- **R1**, the focus bridge;
- **R2**, root BLAST;
- **R3**, the process-published cross-namespace RSSurfaceNode, used in 131 of 133 U10.1T8 runs.

This round writes them as patches, proves the result equivalent to the deployed bridge, and stacks M1, M5 and M6 as
separate patches.

**Result.**
- **The baseline candidate builds reproducibly.** v3 + R1 + R2 + R3 builds at 50/50 TUs with the strict link.
  `e34de8aba9f39d52…`, two fresh builds, same SHA.
- **It is instruction-equal to 84695d62** apart from the two inert master paths (`equivalence.md`). Of 846's 2696
  functions:
  - 2694 are instruction-equal: every address operand is resolved to its string, symbol, GOT target or callee before
    comparing.
  - The 2 that differ are exactly OH-DISPLAY-EVENT and APK-ORIENTATION.
  - With those two blocks compiled out (proof-only patch), **2696/2696** are equal.
  - Exports +3 (all a-path), 0 removed, 0 signature drift, 0 consumer breaks against runtime ac59dec0 and U13 18763dd4.
    Strings: 9 dropped / 23 added, all a-path or non-text layout bytes.
- **M1, M5 and M6 are each a separate patch.** Each applies and builds on the candidate alone, and all three apply
  together. Each changes only its intended functions (`proof/equiv-candidate-vs-*.txt`).

## What was wrong before, and what this round corrects

1. **The baseline v3 was not behaviour-equal to 846**, and porting from the nearest local source was not enough.
   - real-work's `session_stage_adapter.cpp` 0765bc53 has R1/R2, but with the WLTG-gated `ScopedJniAttachment` and
     different log strings.
   - 846's ctor logs `FindClass(adapter/window/WindowCallbackBridge) failed`, not real-work's `Failed to find
     WindowCallbackBridge class`. It uses plain `getJNIEnv` everywhere, and its R3 globals are named
     `g_processSurfaceHolderMutex` / `g_processSurfaceHolders`.
   - The patches follow **846's binary**: `calls.py` lists the ordered call/string fingerprint of each 846 function,
     and each mismatch from `equiv.py` was fixed. Four rounds:
     1. buffer declaration order;
     2. `emplace_back` vs `push_back`;
     3. `ExceptionCheck` before `ExceptionClear`;
     4. global names.
   - Each of these showed up as a register-allocation or template-instantiation difference until it matched.
2. **M6's "U10.1T8 logs no scheduler transaction at all" was a logging artefact, not evidence.**
   - In all 133 U10.1T8 signing runs, the bridge's `__android_log_print` lines never reach hilog: `SessionStageAdapter
     created` appears 0 times, while the HiLog-based `[IPC] ENTER SessionStage.SetActive` appears in 131 runs.
   - The `ScheduleAbilityTransaction` and `[FGGUARD]` lines are `__android_log_print`. Their absence says nothing about
     whether BACKGROUND arrived.
   - The likelier mechanism in both generations is the one U5/U7 showed: FGGUARD vetoes the deferred BACKGROUND_NEW
     because it arrives inside the 3 s init grace window. The M6 patch targets exactly that.

## The patches (`patches/`; window patches apply inside the oh61-v7 window cohort, adapter patches inside `bms/src/adapter`)

| patch | changes | from | check |
|---|---|---|---|
| `win-r1-focus-bridge.patch` (194 lines) | `focusBridgeClass_`, `focusBridgeObj_`, `inheritsParentFocus_`; WindowCallbackBridge in ctor/dtor; `SetInheritsParentFocus`; `SetActive`/`UpdateFocus` → `onUpdateFocusStatus(Z)V` through `callFocusBridgeVoidMethod`; `createSession` marks top-level content | 0765bc53 bodies, rewritten to 846's JNIEnv rule and strings | `SessionStageAdapter` 138/138 functions equal to 846; ctor 1420 B as 846 |
| `win-r2-root-blast.patch` (144) | `EnableRootBlastForTopLevelContent` (sets `ViewRootImpl.mUseBLASTAdapter`); `createSession` refuses with `wsErr 1001` when it fails | 0765bc53:139-225 with plain `getJNIEnv`; 0b816fe6:496-501 | equal to 846 (1372 B) |
| `win-r3-rs-node-holder.patch` | `publishProcessWindowTarget(id, window, node)` keeps a never-freed `shared_ptr` holder and sets `WESTLAKE_RS_SURFACE_NODE_HOLDER_PTR_V1` (order: window, holder, session id last). `getRSSurfaceNode`: local `sessions_` first, then the holder when the id matches V1; logs `acquired process-published cross-namespace surface sessionId=%d node=%p` (I) / `no local or process-published RSSurfaceNode for sessionId=%d` (E). `destroySession` unsets the three V1 variables when the id matches. | **rewritten**, no local source, from 846's call graph | `publishProcessWindowTarget`, `getRSSurfaceNode`, `destroySession`, `createSession`, static initialiser: instruction-equal to 846 |
| `win-m1-session-slots.patch` | per-session `WESTLAKE_NATIVE_WINDOW_PTR_V2_<id>` **and `WESTLAKE_RS_SURFACE_NODE_HOLDER_PTR_V2_<id>`** written next to V1, read first, unset on destroy; V1 unchanged as fallback | `2026-10-02-m1-session-slots/bridge-m1.patch` ported to the snapshot client and extended to the R3 holder | changes 4 functions (publish, `getRSSurfaceNode`, `destroySession`, `oh_wm_get_native_window`); host test below |
| `win-m5-dialog-zlevel.patch` | Android `TYPE_APPLICATION` (2) top-level window → `property->SetSubWindowZLevel(DIALOG_SUB_WINDOW_Z_LEVEL)` before `CreateAndConnectSpecificSession` | OH 6.1 client's own rule: `WindowSessionImpl::GetSubWindowZLevelByFlags` (dialog → `DIALOG_SUB_WINDOW_Z_LEVEL` = 13000), applied in `WindowSceneSessionImpl::Create` without a `supportZLevel_` check (that check guards only the public `SetSubWindowZLevel` API). `zLevel_` is marshalled in the full property (`window_session_property.cpp:1448`, hw248 oh610_lts_source). The board's `libwindow_scene_common.z.so` exports `SetSubWindowZLevel`. | changes `createSession` only |
| `adapter-m6-finishing-background.patch` | before FGGUARD may veto a BACKGROUND_NEW, ask Java `adapter.core.OhTokenRegistry.findByOhToken(J)` → `isDestroying(IBinder)`. `finishActivity` calls `markDestroying` before `TerminateAbility` (dexdump: framework 2257b835 `finishActivity` insn 0006). A finishing Activity's background is never vetoed; logs (HiLog, visible) `[IPC] FGGUARD WARN pass-through BACKGROUND_NEW for finishing token=…` | new | changes `ScheduleAbilityTransaction` only (+ the `CallStaticBooleanMethod` helper) |
| `adapter-proof-no-a-paths.patch` | **proof only, not for deployment**: removes the two a-path entries | – | gives 2696/2696 equal to 846 |

## Builds (`build_r1r3.sh`, logs teed to `$WORKSPACES/westlake-inputs/generations/u14-r1r3-*/logs/`)

| generation | patches | artifact |
|---|---|---|
| `u14-r1r3-v4` / `u14-r1r3-candidate-repeat` | R1 R2 R3 = **baseline candidate** | `e34de8aba9f39d52d5d916ae4246faf1c448b3230be1b21acb3ab9367359cbbd` (both) |
| `u14-r1r3-proof-v3` | + proof-no-a-paths | `aa596f26f3eb7fa3…` |
| `u14-r1r3-m1` | + M1 | `876035d1ec276175…` |
| `u14-r1r3-m5` | + M5 | `07fd530aa4c29a1f…` |
| `u14-r1r3-m6` | + M6 | `94cc67fad87598bf…` |
| `u14-r1r3-all` | + M1 M5 M6 | `438bc94831c9f367…` |

Earlier generations `u14-r1r3-v1`…`v3` were superseded fingerprint iterations; all built 50/50. One source build
round failed: `u14-r1r3-proof-v1`, where the proof patch removed `bundleName`, which is still used later. It was fixed
in the next round. Every build uses master `bms/src/adapter` (unchanged since b94afc59c8), fn03
`fn03-core-846-recon-v1`, compile script 8ca31697.

## Host test (`test/test_slots.py` → `test/test_slots.out`)

The R3/M1 slot code is cut verbatim from the patched sources and compiled on the host with a stand-in RSSurfaceNode.
It replays M1's case: session 702 published, then 703.

| | R3 (candidate, = 846) | R3 + M1 |
|---|---|---|
| single window | 702 → its node and window | same |
| two windows | 703 ok, **702 → none** | 702 and 703 both resolve to their own |
| destroy 702 | 703 kept | 703 kept |

## Predicted moves (bridge-only swap; U12/U13 otherwise unchanged)

| step | predicted | source |
|---|---|---|
| baseline candidate | **0 moves** vs U10.1T8. Instruction-equal to 846 except two inert paths. | `equivalence.md` |
| + M1 | white → lit: noice, fd-uhabits (high); lottery: wikipedia, fd-noice; dddmodel2 needs M5 too; lit regression-watch 9 keys whose background / re-lookup windows get their real Surface | `2026-10-02-m1-session-slots/predictions.csv`; R3 misses = the same 11 runs |
| + M5 | +1 dddmodel2 (with M1); +1 fd-mobile WebView-fallback page; watch the 13 lit keys that open a dialog before their Activity window (dialog now on top) | `2026-10-02-white-unexplained-4` |
| + M6 | +1 fd-AppManager (medium; it then waits for its KeyStore result); 34 lit keys stop leaking a covered scene (no t20 change) | `2026-10-02-white-m6-finish-return` |

## Board watch-list for the first bridge-only comparison (≤ 45 min, one board)

- `getRSSurfaceNode: acquired process-published cross-namespace surface` and `bound Android top-level content` counts
  per key equal U10.1T8 (131/133 keys).
- `[OH-DISPLAY-EVENT] dispatchDisplayEvent(int) unavailable` once per app process, and no other `[OH-DISPLAY-EVENT]`
  lines.
- Bridge `ALOG*` lines: the candidate binds `__android_log_print@LIBC` (`liblog.so`); 846's unversioned import can
  resolve to `libhwui.so`'s. If `SessionStageAdapter created` starts appearing in hilog, that is this binding, not a
  behaviour change.
- With M6: `[IPC] FGGUARD WARN pass-through BACKGROUND_NEW for finishing` for fd-AppManager KeyStoreActivity, then AMS
  `CompleteBackground` / `CompleteTerminate` for it.

## Rules this round sets

- **"Ported" means "equal to the deployed function".** Porting from the nearest source is not done until the deployed
  binary agrees. Take 846's per-function call/string fingerprint (`calls.py`) as the spec, iterate the patch until
  `equiv.py` reports the function equal, and keep a proof-only variant that removes the intended additions and reaches
  full equality.
- **No log line is not proof of no event.** Before concluding "event X never happened" from a missing log line, check
  that the line's logging path reaches hilog on that stack. U10.1T8 drops the bridge's `__android_log_print` output;
  HiLog-based `[IPC]` lines from the same object are present.

## Files

- `patches/`: the seven patches above.
- `build_r1r3.sh`: patch-stack build on top of `../2026-10-02-u14-bridge-baseline/build_u14_bridge.sh`.
- `calls.py`: ordered call/string fingerprint of named functions.
- `equiv.py`: resolved instruction-level equivalence.
- `equivalence.md`: every difference vs 846 explained.
- `proof/`: `equiv-846-vs-candidate.txt`, `equiv-846-vs-proof-no-a-paths.txt`, `equiv-candidate-vs-{m1,m5,m6,all}.txt`,
  `fnsize-846-vs-candidate.txt`.
- `diff-candidate/`, `diff-proof/`: `abi_diff`, NEEDED/undefined and strings vs 846.
- `test/`: host slot test and its output.
- `results.json`.
