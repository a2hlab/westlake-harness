# U14 baseline candidate e34de8ab vs deployed 84695d62: every difference, item by item

Candidate = master `bms/src/adapter` + the oh61-v7 window cohort + the 846 fn03 reconstruction + `win-r1` + `win-r2`
+ `win-r3`. It was built twice from fresh generation directories (`u14-r1r3-v4`, `u14-r1r3-candidate-repeat`); both
builds produce `e34de8aba9f39d52…`.

## 1. Code: instruction-level (`equiv.py` → `proof/equiv-846-vs-candidate.txt`)

**How the tool compares.**
- Both binaries are disassembled once.
- Every address operand is replaced by what it points at:
  - the C string;
  - the sized symbol;
  - the GOT/relocated slot's target;
  - the callee name;
  - a function-relative branch offset.
- Link layout cancels out this way; registers, constants and instruction order still count.

| | count |
|---|---|
| functions in 846 | 2696 |
| instruction-equal | 2691 |
| equal after residual resolution (see below) | 3 |
| **differ** | **2**: `Java_adapter_window_DisplayManagerAdapter_nativeGetDefaultDisplayWidth`, `AbilitySchedulerAdapter::ScheduleAbilityTransaction` |
| only in 846 | 0 |
| only in candidate | 12, all from the two a-paths (below) |

**The 3 residual functions.** Each one differs in a single `[reg, #off]` operand. Its page register was restored in
one epilogue and is still live on a cold path laid out after that epilogue, so the linear tracker loses it. The tool
then resolves the operand through the same `adrp` (same instruction index) in both binaries. Both sides give the same
named object:

| function | resolved operand |
|---|---|
| `nativeOpenForegroundTransition` | `Fn03ProcessEpoch()::epoch` |
| `QueryApplicationInfoRuntimeJsonV1` | `application_info::runtimeStore` |
| `nativeRegisterInputChannel_impl` | that function's own static |

**Proof that the 2 differing functions are only the a-paths.** `adapter-proof-no-a-paths.patch` removes exactly two
things:
- the `ensureDisplayEventBridge(env)` call;
- the APK-ORIENTATION block (with `bundleName` declared at its 846 position, next to its one use).

Built with that patch (`u14-r1r3-proof-v3`, `aa596f26…`), the result is (`proof/equiv-846-vs-proof-no-a-paths.txt`):
- **2696/2696 functions equal** (2692 + 4 residual);
- only in the rebuild: `_GLOBAL__sub_I_display_manager_adapter_jni.cpp` and `sptr<IDisplayListener>::~sptr()`. These
  are the static initialiser of the now-unused `gDisplayListener` global.

So the R1/R2/R3 rewrite reproduces 846's code exactly. What remains are the two master paths that 846 did not have.

`fnsize.py` (per-symbol size, `proof/fnsize-846-vs-candidate.txt`):
- 2507 named functions in 846, all present in the candidate;
- 2505 have the same size;
- the 2 with different sizes are the same two a-path functions.
- `fn03` is 139/139, `SessionStageAdapter` 138/138, `OHWindowManagerClient` 17/17, `AbilitySchedulerAdapter` 84/85.

## 2. Exports / imports / call sets (`diff-candidate/`, `abi_diff.py` + consumers ac59dec0 and U13 18763dd4)

| item | 846 → candidate | explanation |
|---|---|---|
| exports | 2357 → 2360, removed 0, **signature drift 0**, consumer breaks 0 | +3, all a-path: `iface_cast<ISession>` (APK-ORIENTATION), `CallStaticIntMethod` (APK-ORIENTATION), `sptr<IDisplayListener>::~sptr()` (OH-DISPLAY-EVENT). The baseline v3 had a construction-vtable drift and 5 removed exports; R1/R2/R3 close both. |
| call-set diffs | 2 functions | the two a-path functions only |
| NEEDED | identical | |
| undefined | `+RegisterDisplayListener` (OH-DISPLAY-EVENT); `+WindowSessionProperty::SetPersistentId`, `+SetRequestedOrientation` (APK-ORIENTATION); `__android_log_print`, `__android_log_set_logger` → `@LIBC` | The versioned binding comes from linking against a `liblog.so` that defines `__android_log_print@@LIBC`; the deployed payload's `liblog.so` defines the same version. 846's unversioned reference can bind to either `liblog.so` or `libhwui.so` (which also exports it, unversioned). Effect: only where the bridge's `ALOG*` lines go. See the watch item in README. |

## 3. Strings (`deployed_strings_diff.py` → `diff-candidate/strings-846-vs-u14.txt`)

**Dropped: 9.** All non-text bytes or readelf offset labels (jump tables, eh_frame, PNG tail): layout.

**Added: 23.**

| added strings | source |
|---|---|
| 12 = 9 `[OH-DISPLAY-EVENT] …` log formats + `OH_DisplayEvent`, `dispatchDisplayEvent`, `adapter.activity.DisplayManagerProjectionProxy` | a-path, inert |
| 6 = 3 `[APK-ORIENTATION] …` log formats + `adapter.activity.ManifestOrientationProjection`, `resolveOhOrientation`, `com.Revenko.org.CapybaraAdventure` | a-path, inert |
| 5 non-text | layout |

All 846-only strings of the baseline v3 are present again:
- `EnableRootBlast: …`;
- `callFocusBridgeVoidMethod…`;
- `FindClass(adapter/window/WindowCallbackBridge) failed`;
- `WESTLAKE_RS_SURFACE_NODE_HOLDER_PTR_V1`;
- `getRSSurfaceNode: acquired process-published cross-namespace surface …`;
- `… no local or process-published RSSurfaceNode …`;
- `createSession: failed to enable root BLAST …`.

The proof build without the a-paths: 4 dropped / 4 added, **all non-text layout bytes**.

## 4. Why the two a-paths are inert on the U13 stack

**OH-DISPLAY-EVENT.**
- The first `nativeGetDefaultDisplayWidth` per process (skipped for uid 0, the appspawn-x parent) loads
  `adapter.activity.DisplayManagerProjectionProxy`.
- It then asks for static `dispatchDisplayEvent(I)V`. Runtime 0482c9b1 has the class but no such method (dexdump: only
  `<init>`, `createUnavailableStatus`, `install`), and the class has no `<clinit>`.
- So `GetStaticMethodID` fails. The `NoSuchMethodError` is described and cleared, `[OH-DISPLAY-EVENT]
  dispatchDisplayEvent(int) unavailable` is logged once, and the function returns **before `RegisterDisplayListener`**.
- The attempted flag makes this once per process. Afterwards the function returns the display width as 846 does.

**APK-ORIENTATION.**
- `adapter.activity.ManifestOrientationProjection` is in neither the runtime jar 0482c9b1 nor the framework jar 2257b835.
- `adapter_bridge_load_class` returns null and the pending exception is cleared (one log line). `requestedOrientation`
  stays −1, so the `[VERTICAL, END]` range check fails and no `UpdateSessionPropertyByAction` is sent.
- Per transaction, the only cost is one `ScopedJniAttach` scope plus the failed class load. The Capybara branch needs
  bundle `com.Revenko.org.CapybaraAdventure`, which is not among the 166 keys.

## 5. Single-session behaviour of R3 (host test, `test/test_slots.py` → `test/test_slots.out`)

The anonymous-namespace slot code is cut verbatim from the patched source and compiled on the host:

| case | R3 (candidate) | R3 + M1 |
|---|---|---|
| one window | 702 → its node and window, as 846 | same |
| two windows (702 then 703) | 703 resolves; **702 → none**. This is 846's defect, seen as `no local or process-published RSSurfaceNode` in 11 U10.1T8 runs (the M1 population). | both resolve to their own node and window |
| destroy 702 | 702 none, 703 kept | 702 none, 703 kept |

So on single-session apps the candidate returns exactly what 846 returns: same lookup order (local `sessions_`, then
the process-published holder), same strings, same log levels (I/E).
