# U14 JAR v1 = U13 JAR v3 + InProcessBindOrder (termux): reproduced on host ART with the boards' BCP, with v3 as the negative control

#90, JAR, offline. Nothing was deployed to a board, and a2hlab was not used: the build ran on the Mac and the tests on
hw248's host ART.

## The wall (`2026-10-03-termux-and-u12-jar-check`, fac7afbacd)

- TermuxActivity's `onCreate` binds TermuxService. On route A that becomes `ActivityManagerBindProxy.postInProcessBind`,
  which posts the create+bind+`onServiceConnected` runnable to the main looper.
- OH's FOREGROUND callback schedules the RESUMED transaction (onStart/onResume) only afterwards, so the connection
  runs first.
- `TermuxActivity.onServiceConnected` then sees `mIsVisible == false`. That flag is set in `onStart`. It finishes
  itself: white.
- On Android, the launch transaction carries its ResumeActivityItem, so a connection queued from `onCreate` lands after
  `onResume`.

U10.1T8 hilog (5cd, window 5), verbatim:
```
16:52:03.396 20680 [stderr] [B8-AMB] bindServiceInstance -> in-process in-app service ComponentInfo{com.termux/com.termux.app.TermuxService}
16:52:03.398 20680 AndroidEventLog [tag=30057] arr=[59493313,"com.termux.app.TermuxActivity","performCreate",86L]
16:52:03.401 20678 OH_LifecycleAdapter: OH callback (direct token): state=INITIAL->FOREGROUND -> RESUMED activityToken=android.os.Binder@38bcbc1
16:52:03.404 20680 [stderr] [B8-AMB] created in-process service com.termux.app.TermuxService
16:52:03.404 20680 [stderr] [B8-AMB] connected com.termux.app.TermuxService binder=com.termux.app.TermuxService$LocalBinder@b6d07a8
16:52:03.404 20680 OH_LifecycleAdapter: ClientTransaction scheduled on main Looper (direct token): RESUMED
16:52:03.405  1545 AMS: [UALM2093]pending state dropped CLOSE: 9, independentRecovery: 0
16:52:03.406 20680 OH_ACCAdapter: finishActivity: OH TerminateAbility(token=0x7f35b5daa0, code=0) rc=0
```

## The fix (fac7afbacd's class, unchanged; `src/` is byte-identical)

- **New class `adapter.activity.InProcessBindOrder`**, which compiles to three classes: base, `$1` (the wrapping
  Runnable) and `$2` (the per-Activity lifecycle callbacks).
- **One smali needle** in `ActivityManagerBindProxy.postInProcessBind`, right after the bind runnable is built:
  `v1 = InProcessBindOrder.wrap(v1, connection)` (`gates/needle-ActivityManagerBindProxy.diff`). The `Handler.post` is
  unchanged.
- **What the wrapper does.** When it runs, it finds the binding Activity:
  `InnerConnection.mDispatcher` → `ServiceDispatcher.mContext`, then `ActivityThread.mActivities[mToken]
  .getLifecycleState()`.
  - **Before ON_START:** it holds the bind until that Activity's `onActivityPostStarted`, then posts it, so it lands
    after the same transaction's `onResume`.
  - **Activity destroyed first:** it drops the bind.
  - **Anything else, including any failure to identify the Activity:** it runs the bind at once, as today.

## Artifact and gates

| | |
|---|---|
| jar | `oh-adapter-runtime-u14-v1.jar` = **`0349eb834e66bc1bf142fd31f08aa0c8a0536534e3ec6b01b5dcc1d930b0a0d4`** |
| build | `build_v1.py`: base `bbc3f530` (U13 JAR v3), pinned toolchain of build_u12 / build_v3. The output is disassembled again: **every smali file except `ActivityManagerBindProxy.smali` is byte-identical to the base**, and the only additions are the 3 InProcessBindOrder classes (asserted). Built twice: byte-identical. |
| `deployed_class_diff --deployed 5ae3dd29` (the boards' runtime) | 0 dropped, 0 reshaped, 0 added after the allow list. The list is the 19 classes already in v3 plus the 3 new ones (`gates/class-diff-vs-5ae3dd29.txt`). |
| `deployed_class_diff --deployed bbc3f530` | 0 dropped, 0 reshaped; added = exactly `InProcessBindOrder`, `$1`, `$2` (`gates/class-diff-vs-bbc3f530.txt`) |
| changed class | `ActivityManagerBindProxy`: body only, +3 smali lines in `postInProcessBind`. The same diff against bbc3f530 and against 5ae3dd29. |
| deploy | runtime PathClassLoader jar: a single-file replacement, no boot-image rebake |
| persisted | `$WORKSPACES/westlake-inputs/generations/u14-jar-v1/` (jar, `SHA256SUMS`, `logs/build-*.log` teed while it ran) |

## Host ART on the boards' boot class path, with v3 as the negative control (`test/`, `evidence/`)

**Can the termux order be reproduced on host ART?** Yes, the ordering part.
- `postInProcessBind` does only two things: `new Handler(Looper.getMainLooper())` and `post(new $1(...))`.
- The U10.1T8 failure is purely the order of two main-looper messages: the bind runnable, then the RESUMED transaction
  that OH's FOREGROUND callback posts 5 ms later.

**What a full TermuxActivity launch would need, and why it is not run.** It needs ActivityThread's TransactionExecutor,
a system_server, termux's own classes and libandroid_runtime's natives (Looper/MessageQueue,
`SystemClock.uptimeMillis`, Binder). Host ART has none of those natives.

**Setup.** Host ART = hw248 android-14.0.0_r1 `dalvikvm64 -Xint`, imageless.
- The boot class path is the boards' 9 BCP jars in board order (hashes in `evidence/hw248-inputs.txt`).
- `host-shim-v1.jar` goes before `framework.jar`. It is test-only: `android.util.Log` (as in the v3 test) plus
  `android.os.SystemClock`, without the natives.

| real code under test | stand-in |
|---|---|
| runtime jar: `ActivityManagerBindProxy.postInProcessBind` (with or without the needle), `InProcessBindOrder`, the real bind runnable `ActivityManagerBindProxy$1` (it runs to the framework's `LoadedApk$ServiceDispatcher.doConnected`) | main `Looper` / `MessageQueue` allocated without constructors (no `nativeInit`); the queue is drained FIFO by hand instead of `Looper.loop` (`nativePollOnce`) |
| framework.jar: `Handler.post` → `MessageQueue.enqueueMessage`, `Activity.registerActivityLifecycleCallbacks` / `dispatchActivityPostStarted` / `dispatchActivityDestroyed`, `ActivityThread$ActivityClientRecord` state, `ActivityLifecycleItem` constants (read: ON_CREATE=1, ON_START=2, ON_RESUME=3) | `ActivityThread.sCurrentActivityThread` = an allocated ActivityThread whose `mActivities` holds the test Activity's record |
| – | **the RESUMED transaction**: one message that sets ON_START, sets `mIsVisible` (TermuxActivity.onStart), calls the real `dispatchActivityPostStarted`, then sets ON_RESUME |
| – | **TermuxService**: a `RecordingService` pre-registered in `ActivityManagerBindProxy.sServices`, so `$1` takes its "already created" branch and calls `onBind`. `onBind` records the Activity's state and `mIsVisible`, which is what `onServiceConnected` checks right after. |

**Results** (`test/run_bindorder.sh <runtime jar>`; logs `evidence/hostart-run-*.log`):

| case | v1 `0349eb83` | v3 `bbc3f530` (negative control) |
|---|---|---|
| 1 termux: bind from `onCreate` (ON_CREATE), RESUMED queued after it | **PASS**: delivered at `state=3 mIsVisible=true`. Log: `[B8-AMB-ORDER] holding … (state=1)` → `started; delivering … after this transaction` | **FAIL**: delivered at `state=1 mIsVisible=false` → `onServiceConnected` would finish. **This is U10.1T8's order.** |
| 2 bind from an already-resumed Activity | PASS: delivered at once, ahead of later messages | PASS |
| 3 connection not attributable to an Activity | PASS: runs first, exactly as before | PASS |
| 4 Activity destroyed before onStart | **PASS**: `[B8-AMB-ORDER] … destroyed before start; in-process bind dropped` | **FAIL**: delivered to the dying Activity |
| total | FAILURES 0, rc 0 | FAILURES 2, rc 1 |

**Two expected harness artifacts in the logs:**
- After the recording point, `$1` continues into the real `LoadedApk$ServiceDispatcher.doConnected` and throws an NPE
  on the harness-allocated dispatcher, which has no `mActiveConnections`. `$1` catches it and logs `[B8-AMB] in-process
  bind failed …`.
- In case 3, the plain-Object connection has no `connected` method.

Neither affects the ordering that is measured. Both appear identically for v1 and v3.

## Board judge (when this jar is deployed)

Taken from the U10.1T8 lines above.

**Fixed** means all of these:
- termux logs `[B8-AMB-ORDER] holding in-process bind until com.termux.app.TermuxActivity is started (state=1)`;
- then `… started; delivering in-process bind after this transaction`;
- `[B8-AMB] connected com.termux.app.TermuxService` comes **after** `ClientTransaction scheduled on main Looper (direct
  token): RESUMED`;
- there is no `finishActivity: OH TerminateAbility` for TermuxActivity around it.

**Not fixed:** the U10.1T8 order above.

## Prediction by first fatal (`predictions.csv`)

| key | today | with U14 JAR v1 |
|---|---|---|
| **termux** | self-finish (above) → white | **The first fatal moves (high) to TermuxInstaller's bootstrap check** (dexdump of the installed APK `e6265a57`). Chain below. Expected t20: **termux's own error dialog over the terminal Activity, process alive (medium)**. That is own UI, not functional: a working termux needs a `/data/data/<pkg>` path wall, and that is not a JAR fix. |
| fd-droidify, newpipe (lit; their bind was also queued before RESUMED) | lit | lit. Their service connection now lands after `onResume` (Android's order). Neither checks visibility. Watch: a `[B8-AMB-ORDER] holding` line. |
| 5 other lit keys with an in-process bind, and white noice | as today | unchanged. Their bind is posted after the Activity reached ON_START, so the wrapper runs it at once. |
| everything else | as today | unchanged (no in-process bind) |

**termux: the chain to the predicted first fatal.**
1. `setupBootstrapIfNeeded` → `TermuxFileUtils.isTermuxFilesDirectoryAccessible(ctx, true, true)`.
   - It calls `getFilesDir()`, then checks the hard-coded `/data/data/com.termux/files`. That returns
     `ERRNO_FILE_NOT_FOUND_AT_PATH`: route A's dataDir is `/data/app/el2/100/base/com.termux` (`[B43-BIND] dataDir
     overridden`).
   - The same run already logs `Termux:SharedProperties: Not loading properties since file is null` for that tree.
2. `isCurrentUserThePrimaryUser` → `UserManager.getSerialNumberForUser`.
   - The route-A user binder (`UserManagerProjectionProxy$UserBinder`) answers only `isUserUnlockingOrUnlocked`.
   - Every other code falls through to `Binder.onTransact` → false. The in-process proxy then reads an empty reply:
     no exception, serial 0. So it counts as the primary user.
3. Primary user + files dir not accessible:
   - `Logger.logError` (`Termux:TermuxInstaller`, with `TERMUX_FILES_DIR: /data/data/com.termux/files`);
   - `sendBootstrapCrashReportNotification` (the notification service is answered in process, `[B8-SVC]
     notification`);
   - `MessageDialogUtils.showMessage`, the error dialog.

   If the serial were not 0, the other branch logs `isFilesDirectoryAccessible: false` and calls
   `exitAppWithErrorMessage`, which also shows a dialog first.

## What was wrong before

- fac7afbacd built the fix on `6790d500`, and its check was a dexdump reading plus field names. Nothing executed the
  ordering.
- This round rebases the fix on v3 and executes the real `postInProcessBind`, wrapper and Activity callback dispatch on
  the boards' framework.jar. v3 reproduces U10.1T8's order there (`state=1 mIsVisible=false`); v1 does not.

## Rules this round sets

- **Reproduce a main-looper ordering wall on host ART by allocating the Looper/MessageQueue without constructors and
  draining by hand.** Natives are only needed for `nativeInit` / `nativePollOnce` / `SystemClock`. Everything else runs
  as the board runs it (`test/BindOrderAndroidTest.java`).
- **To observe an in-process service bind without running the app, pre-register a recording service in the proxy's
  service map.** The real runnable then takes its "already created" branch and calls `onBind` at the exact moment it
  would deliver.

## Files

- `src/adapter/activity/InProcessBindOrder.java`, `build_v1.py`.
- `gates/`: class diffs vs 5ae3dd29 / bbc3f530; `needle-ActivityManagerBindProxy.diff`.
- `test/`: `BindOrderAndroidTest.java`; `hostshim/` (test-only Log, SystemClock); `build_test.py`; `run_bindorder.sh`.
- `evidence/`: `hostart-run-v1.log`, `hostart-run-v3-negative-control.log`, `hw248-inputs.txt`.
- `predictions.csv`, `results.json`.
- `erratum-u14-bridge-m5-m6.md`: correction to f1f7cb5851.
