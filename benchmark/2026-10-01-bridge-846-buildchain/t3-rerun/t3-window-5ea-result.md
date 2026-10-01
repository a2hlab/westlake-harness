# #96 t3 window (5ea, 2026-10-01): rebuilt bridge 7cf8ebcc FAILS — window-add `InvalidDisplayException`

**Verdict: Gate FAIL — do NOT freeze 7cf8ebcc as a 846 replacement.** The board_run single-variable A/B
(U8 baseline, only `liboh_adapter_bridge.so` 846→7cf8ebcc via `sweep_bind_deploy` + appspawn-x restart) ran: the
rebuilt bridge **deploys and fully initializes**, but **every app — including the HW/ZZ controls — dies at its first
window `addView` with `android.view.WindowManager$InvalidDisplayException: … the specified display can not be
found` → `System.exit(1)`**. So "even the controls don't come up" is real, but the cause is a **window-session /
display ABI behavioral regression**, NOT a missing-export dlsym and NOT a load failure.

Window: LOCK 5ea 14:27:28 → after_lock sweep bind (DEPLOY OK, appspawn-x up) → smoke FAIL → before_unlock →
(my `--out` bug, see §4) outer recovered + UNLOCK 14:33. Board restored to U8+846, fp e953c0921536/4db882a81732.

## 1. What the smoke saw
`smoke-result.json`: `boot_fp` ok; **controls HelloWorld + ZigZag `alive_t20=no`**; **probe child count 0**. So
Gate 0 (bridge child-view sha) could not even be read — there was no live child. facts: `TOTAL keys=2
screenshots_captured=4/4 alive_t5=0 alive_t20=0` (4 shots all desktop).

## 2. Why the children die — traced in the child hilog (HelloWorld pid 31518, ZigZag pid 639, identical)
The rebuilt bridge is NOT a load/symbol failure. The child progressed all the way through startup:
```
OH_RegHook: … lib=/system/android/lib64/liboh_adapter_bridge.so   # rebuilt bridge loaded, natives hooked
OH_EnvJNI: register_OHEnvironment: OK 6 methods
OH_EnvJNI: nativeInitialize() / nativeConnectToOHServices() / nativeAttachApplication: pid=31518 …
OH_AppMgrClient: AttachApplication completed …                    # attach OK (IPC sent)
OH_AppSchedulerAdapter: ScheduleLaunchAbility … com.example.helloworld.MainActivity ; AttachAbilityThread rc=0
OH_DisplayMgrAdapter: getDisplayInfo(0) -> 1200x1920@60Hz dpi=360  # display query succeeds
```
then, in `handleResumeActivity` → `WindowManagerImpl.addView` → `ViewRootImpl.setView`:
```
AppSpawnXInit: initChild failed
java.lang.reflect.InvocationTargetException
 Caused by: android.view.WindowManager$InvalidDisplayException: Unable to add window
   android.view.ViewRootImpl$W@… -- the specified display can not be found
   at android.view.ViewRootImpl.setView(ViewRootImpl.java:1423)
   at android.view.WindowManagerGlobal.addView(WindowManagerGlobal.java:445)
   at android.app.ActivityThread.handleResumeActivity(ActivityThread.java:5065)
appspawn-x: [OpenjdkJvm.cc:344] System.exit called, status: 1
APPSPAWN: com.example.helloworld with pid 31518 exit with code:1   (kill reason=OnRemoteDied)
```
- **No cppcrash / tombstone** — it is a clean `System.exit(1)` from an uncaught Java `InvalidDisplayException`, not a
  native SIGSEGV/SIGABRT.
- **Both controls, identical** (`InvalidDisplayException` ×3 + `System.exit status 1` ×1 in each hilog). HelloWorld
  pid 31518 and ZigZag pid 639.
- The app **read the display fine** (`getDisplayInfo(0) -> 1200x1920@60Hz`) but the **window-session add** reports
  the display "can not be found" — the failure is in the window/session creation path that `addView` drives.

## 3. Root: a window-session/display ABI regression — the signature-evolved `createSession`, not the absent exports
The dispatch asked to check whether the runtime `dlsym`s one of the 14 "no-consumer" deltas by name (a blind spot
of the UND-only t3-pre scan). Checked and **cleared**:
- **No dlsym-by-name of the 7 genuinely-absent symbols.** `strings` of the deployed-equivalent
  `liboh_android_runtime.so` and the sealed-child spawner `libwestlake_android_child.z.so` contain **none** of
  `oh_anw_notify_presented`, `oh_anw_wrap_for_activity`, `SessionStageAdapter`/`WindowCallbackAdapter`
  `detachIfNeeded`/`getJNIEnv` as string literals. (Only the bare word `createSession` ×2 appears in the runtime —
  and that function *exists* in the rebuild under a new mangling, so it is not an absence.) *(Caveat: the runtime
  copy scanned is a local proxy; the behavioral evidence below is authoritative and copy-independent.)*
- **The bridge loaded and fully initialized** (register_OHEnvironment OK, nativeInitialize/Connect/Attach, launch,
  AttachAbilityThread rc=0). An unresolved/absent symbol would have failed loud at load or first use with
  `cannot locate symbol` (none seen for the bridge). So the absent exports are **not** the cause — consistent with
  the t3-pre "0 consumers" finding for them.

The failure is a **silent ABI/behavioral mismatch at a normal native call** on the window-session path. The leading
suspect among the 14 deltas is **`OHWindowManagerClient::createSession`** — 846 `(…iiiim)` → rebuild `(…iiiiim)`,
**+1 int**. The deployed U8 runtime/`WindowSessionProxy` calls `createSession` with the **846** argument layout; the
rebuild reads its arguments one slot over, so the session is created against the wrong/invalid display → `addView`
→ `ViewRootImpl.setView` → **`InvalidDisplayException: the specified display can not be found`**. An evolved
signature fails *silently* (the call still binds and runs) — unlike an absent symbol — which is exactly this
symptom. *(Not yet proven that the +1 int IS the displayId; see §5 to confirm.)*

## 4. My plan bug (owned): before_unlock `--out` mismatch
`before_unlock` used `--out …/rollback`, but `after_lock`'s `deploy-receipt.json` is at `…/deploy`;
`sweep_bind_deploy --rollback-only` reads the receipt from `--out`, so it failed (rc=2) and left the bridge bind
mounted + the lock held. The outer ring recovered (re-ran `--rollback-only --out …/deploy`, verified
e953c0921536/4db882a81732, UNLOCK 14:33) and relaxed the tool (master 0f9e4d427). Fixed in the plan
(`before_unlock --out` → `…/deploy`). I had dry-run only the `after_lock` path, not the rollback path.

## 5. Next step (offline-first, then one board re-run)
1. **Decode `createSession`'s evolved argument** (offline): disassemble 846 vs rebuild `OHWindowManagerClient::
   createSession`, identify the inserted int and whether it is a `displayId`/flags slot; and check how the deployed
   U8 `WindowSessionProxy`/`WindowManagerAdapter` native binding passes the display — confirm an off-by-one-slot.
2. If confirmed, the rebuild is a genuine ABI break on the window path → stays NOT a 846 drop-in; the freeze
   requires re-emitting `createSession` with the **846** signature (alias/overload) so the deployed runtime's call
   lands correctly. This is the compat-export fallback already named in the t2-D exception proposal.
3. **Harness note (orthogonal):** board_run launches the smoke immediately after `sweep --no-run` restarts
   appspawn-x; the EPIPE (`APPSPAWN_CLIENT Failed to write message … errno 32`) on some spawns suggests a settle
   gap is *also* in play. A readiness wait after the appspawn-x restart would de-noise future windows — but it is
   NOT the root here (the children that DID spawn died at `addView`, not at spawn).

## 6. Status
- t3 verdict: **FAIL** — rebuilt bridge 7cf8ebcc breaks window creation (`InvalidDisplayException` at `addView`) for
  every app incl. controls; do not freeze-replace 846.
- Root: **window-session/display ABI regression**, most likely the `createSession` +1-int signature evolution;
  **not** the absent exports, **not** dlsym-by-name, **not** a load failure. Board restored to U8+846.
