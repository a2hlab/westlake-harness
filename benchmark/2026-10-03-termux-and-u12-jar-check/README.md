# termux finishes itself because route A delivers an in-process onServiceConnected before onStart; U12 JAR check: fd-client lit, x moved to telephony.registry, 4 of 6 keys never ran

#90, JAR/Java, offline. Nothing was deployed to a board. Two parts:
1. why termux leaves a white screen;
2. whether U12's JAR predictions moved the first fatal of its six keys in U12 windows 1–4.

## 1. termux

### What was wrong in my M6 reading

`2026-10-02-white-m6-finish-return` said TermuxActivity returns from `onCreate` because
`TermuxAppSharedPreferences.build(context, true)` returns null. **That is false.**
- `build()` is `createPackageContext("com.termux", CONTEXT_RESTRICTED)` on its own package. If it failed, it would log
  `PackageUtils` errors and show the "package context failed" dialog.
- The U10.1T8 run (5cd, window 5) has neither.
- `onCreate` ran past `build()` to `startService` + `bindService(TermuxService)`: `[B8-AMB] bindServiceInstance ->
  in-process in-app service … TermuxService` at 16:52:03.396, then `performCreate` at .398. That code comes after
  `build()` (dexdump `0x0026` build → `0x0093` startService → `0x0096` bindService).

### What actually finishes it (dexdump of termux.apk + the run's hilog)

`TermuxActivity.onServiceConnected` does this:
- if the service has no sessions, it checks `mIsVisible`;
- `mIsVisible` is set to true in `onStart`;
- if it is false, it calls `finishActivityIfNotFinishing()`.

On our route the connection is delivered **before `onStart`**:

| time (16:52:03.) | event |
|---|---|
| .396 | `onCreate` → `bindService` → `ActivityManagerBindProxy.postInProcessBind` **posts** the create+bind+onServiceConnected runnable to the main looper |
| .401 | OH FOREGROUND callback arrives: `INITIAL->FOREGROUND -> RESUMED` |
| .404 | `[B8-AMB] connected TermuxService`: the bind runnable runs first, because it was queued first. `mIsVisible == false` → finish |
| .404 | `ClientTransaction scheduled on main Looper (direct token): RESUMED`: onStart/onResume are queued only now |
| .406 | `finishActivity: OH TerminateAbility(token=0x7f35b5daa0)`: the M6 dropped close; the windowless scene stays → white |

**Why Android never does this.** On Android the launch transaction carries `LaunchActivityItem` **and** its
`ResumeActivityItem`, so `onCreate`/`onStart`/`onResume` run in one message, and a connection queued from `onCreate`
lands after `onResume`. On route A the create and the start/resume are separate main-looper messages: the RESUMED
transaction follows OH's FOREGROUND. Our in-process bind (`[B8-AMB]`) slips in between.

### Who else goes this way (`bind_order.py` → `bind-order.csv`, U10.1T8 signing runs)

| | runs with an in-process bind | bind queued before the RESUMED transaction |
|---|---|---|
| white (16) | 2 | **1**: termux, then finishes 2 ms later |
| lit (117) | 7 | 2: fd-droidify (SyncService), newpipe (PlayerService); harmless, neither checks visibility |

### Minimal fix (U14 JAR candidate, built, not merged)

New file `adapter.activity.InProcessBindOrder` plus one smali needle in
`ActivityManagerBindProxy.postInProcessBind`, right after the bind runnable is constructed:
`v1 = InProcessBindOrder.wrap(v1, connection)`. The existing `Handler.post` is unchanged.

The wrapper runs where the bind would have run:
- it takes the binding `Activity` from the connection (`LoadedApk$ServiceDispatcher$InnerConnection.mDispatcher` →
  `ServiceDispatcher.mContext`);
- it reads that Activity's `ActivityClientRecord.getLifecycleState()`. These field names were checked in the
  deployed `framework.jar`.
- **before ON_START:** it holds the bind until the Activity's own `onActivityPostStarted` (API 29 per-Activity
  callbacks), then posts it. It then lands after the `onResume` of the same RESUMED transaction, as on Android.
  If the Activity is destroyed first, the bind is dropped.
- **anything else**, including any failure to identify the Activity: it runs the bind immediately, as today.
- Marker: `[B8-AMB-ORDER]`.

**Artifact:** `oh-adapter-runtime-u14-bindorder.jar` `b5a731a7…` = U13 JAR `6790d500` + 3 classes.
- deterministic (built twice, same toolchain as U12/U13);
- `deployed_class_diff` vs `6790d500`: 0 dropped, 0 reshaped;
- persisted at `$WORKSPACES/westlake-inputs/generations/u14-jar-bindorder-v1/`.

**Prediction.**

| key | prediction |
|---|---|
| termux | **The self-finish goes away (high). It still will not light (high):** with `mIsVisible` true, `onServiceConnected` reaches `TermuxInstaller.setupBootstrapIfNeeded`. That first checks the hard-coded `/data/data/com.termux/files`; on route A the data dir is `/data/app/el2/100/base/com.termux` (`[B43-BIND] dataDir overridden`). The run already logs `Termux:SharedProperties: Not loading properties since file is null` for the same path. Expected next screen: termux's "files directory not accessible" error dialog → exit. Lighting termux needs a `/data/data/<pkg>` path wall, which is not a JAR fix. |
| fd-droidify, newpipe | stay lit; onServiceConnected now after onResume (watch) |
| everything else | 0 |

**Value:** low on its own (0 keys lit). It is an Android-ordering correctness fix; hold it for U14 or skip.

## 2. U12 JAR predictions vs U12 windows 1–4 (`u12_check.py` → `u12-check.json`, `u12-check-first-fatal.json`, `u12-check-clusters.json`)

`first_fatal.py` was run on every U12 run of the six keys and on their U10.1T8 window-5 source, then
`cluster_first_cause.py` over both. The U12 runs' `runtime-fingerprint.txt` shows runtime jar `0482c9b1` (U12 r2) on
all three boards.

| key | U10.1T8 first fatal | U12 (windows 1–4) | moved? |
|---|---|---|---|
| fd-client | NPE `Cursor.moveToFirst()` (own provider published as `@id`) | window 4, 5cd: **no termination**; 5 `[B8-PROV-AUTH]` rewrites (`FileContentProvider @2131951783 -> org.nextcloud` …); `run_facts`: shots 2/2, alive t5/t20; **t20 = Nextcloud onboarding screen (lit)** | **yes → lit** |
| x | ISE "application object graph is not defined" (bind died on `NoSuchMethodError getTelephonyServiceManager`) | window 4, 61b: graph error gone (0 lines); `[B8-FETCH] phone class->name registered`, `TelephonyManager allocated (non-null)`; new first fatal NPE `ITelephonyRegistry.listenWithEventList` (`TelephonyRegistryManager.listenFromListener` ← `TelephonyManager.listen` ← `com.twitter.util.telephony.a.run`), right after `getService("telephony.registry") → null`; t20 white | **yes, to the next wall** (telephony.registry: a no-op ITelephonyRegistry binder, same pattern as `WlTelephonyStub`) |
| notepad | NPE `Cursor.moveToFirst()` | not run in windows 1–4 | unknown |
| clipboardeditor | NPE `TelephonyManager.getSimCountryIso()` | not run | unknown |
| packlist | CNFE `com.android.internal.util.Predicate` | not run | unknown |
| moodcairns | AEADBadTag (GCM nonce) | not run | unknown |

**Coverage of the four U12 windows.**
- They ran lit/lit-cv2 rechecks, fitness and listmaker, 27 unlit-original keys, and only 3 unlit-cv2 keys (randomlydie,
  chessclock, yatoo).
- None of the four cv2 keys ran. Their predictions are still **untested, not confirmed and not refuted**.
- They need one pass in the U13 window (≈ 4 × 3 min, any board on the U13 JAR, which contains U12 r2).

## Rules this round sets

- **An app's own early-return is a hypothesis until the logs agree.** A dexdump `if-nez → return-void` after a call
  does not show that the call returned null. Check that the code after it did not run: here `bindService` logged right
  after.
- **Route A splits launch and resume into two main-looper messages.** Anything our runtime posts from `onCreate`
  (in-process binds, callbacks) runs before `onStart`. Check against Android's single launch-transaction order.
- **"Not run" is its own verdict.** A prediction check reports keys without a run as not run. Do not count them as
  unmoved or as confirmed.

## Files

- `bind_order.py` → `bind-order.csv`, `bind-order.txt`.
- `src/adapter/activity/InProcessBindOrder.java`, `build_bindorder.py`, `gates/class-diff-bindorder.txt`.
- `u12_check.py` → `u12-check.json`, `u12-check-first-fatal.json`, `u12-check-clusters.json`, `u12-check.txt`.
- `results.json`.
