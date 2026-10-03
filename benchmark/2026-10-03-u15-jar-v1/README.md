# U15 runtime JAR v1 = U14 v1 0349eb83 + trampoline finish order (x, 36 keys) + alias theme after the app-theme overwrite (fd-api) → `20e748e5`, built twice byte-identical

#90, JAR (runtime, not BCP), offline. Nothing was deployed to a board. The build ran on the Mac; the behaviour test
ran on hw248's host ART (android-14.0.0_r1) with both the current boards' BCP and the U15 bake's BCP.

## Release

`$WORKSPACES/westlake-inputs/generations/u15-jar-v1/oh-adapter-runtime-u15-v1.jar` =
**`20e748e57c6ee8bd0b97dcfff074c3a1c001dd727cbcee6a754f60a598642770`**.
- This is the single U15 runtime JAR. It replaces `oh-adapter-runtime.jar` (U14 v1 `0349eb83`). It is outside the BCP, so
  no FZ-005 bake is needed.
- The directory holds the recipe, the source, the teed build logs, the test jar and the host-ART logs. `SHA256SUMS`
  covers all of it.

## What was wrong before

**x (and 36 trampoline keys).** `2026-10-03-x-trampoline-handover` showed the sequence:
1. `startActivity(XLiteActivity)` is still an SCB pending session.
2. The trampoline's `finish()` → OH `TerminateAbility` reaches AMS first.
3. AppMgr `PrepareTerminate` finds the last ability (`[ARM938]`) → `SetTerminating`.
4. XLiteActivity is cold-started in a second process.

**fd-api: what the report assumed.** cc-wiki's patch (`2026-10-03-u15-fdapi-theme`, master 05ade34d78) assumed the alias
target theme is never written to `launch.theme`. It proposed a new manifest reader plus a needle in
`LaunchActivityAliasProjection.apply`.

**fd-api: what the U14 JAR actually does** (`evidence/fd-api-theme-order.txt`):
1. It already writes the target theme. `AliasTargetTheme.apply` (source line 1644) logs `[B8-ALIASTHEME] … 0x1030237 ->
   0x7f120252`, and `[G2.5-SLA-PRE] theme=0x7f120252` confirms it on the board.
2. **Line 1748 then overwrites it:** `if (sEnrichedTheme != 0) ai.theme = sEnrichedTheme`, where sEnrichedTheme is the
   `[WL-THEME-SYNC]` application theme `0x1030237`.
3. `J10dTheme.restore` (line 1750) restores the activity's own theme for every **non-alias** activity, but skips
   aliases on purpose (`[J10d-THEME] … skipped: alias target theme owned by AliasTargetTheme`).

**Net effect:** only alias launches end up with the application theme. The patch's needle sits at line 1644, before the
overwrite, so it would have been overwritten in the same way.

## The change (`build_v1.py`; four needles plus one new class)

**New class.** `src/adapter/activity/TrampolineFinishOrder.java`, five dex classes. It has two parts:
- **`install()`** (B8-AMB pattern) wraps `ActivityTaskManager.IActivityTaskManagerSingleton` with a start observer.
  - It marks a start when `startActivity`, `startActivityAsUser`, `startActivities` or `startActivityWithConfig` targets
    this app's own package, by explicit component or `setPackage`.
  - The rc must not be negative.
  - If a launch arrives while the start call itself is running, no mark is set.
- **`controller()`** wraps the `IActivityClientController` that LaunchActivityItem carries; it becomes
  ActivityClient's `mKnownInstance` in `preExecute`.
  - **Hold:** while a marked start has not reached this process, `finishActivity` is held, for at most 3 s. It returns
    true, which is the adapter's own answer.
  - **Release:** the next `ScheduleLaunchAbility` of this process, or the 3 s timeout, forwards the call unchanged on
    the main thread.
  - **Duplicates:** a second `finishActivity` for a token already forwarded or held is dropped. AOSP returns true for
    an activity that is already finishing; the board's second call only produced rc=22.
  - **Everything else:** every other method, and any exception inside the intercepts, goes straight to the delegate.

**Needles** (`gates/needle-*.diff`; only these insertions plus baksmali label renumbering):

| # | file | where | inserted |
|---|---|---|---|
| 1 | `B7BindFixes` | after `OwnProviderLocal.install()` (U12's needle, after `ActivityManagerBindProxy.install()`) | `TrampolineFinishOrder.install()` |
| 2 | `AppSchedulerBridge.nativeOnScheduleLaunchAbility` | the controller passed to `LaunchActivityItem.obtain` | `v39 = TrampolineFinishOrder.controller(ActivityClientControllerAdapter.getInstance())` |
| 3 | same method | first instruction | `TrampolineFinishOrder.onLaunchAbility(bundleName, abilityName)` |
| 4 | same method | right after line 1748's `sEnrichedTheme` overwrite, before `J10dTheme.restore` | `AliasTargetTheme.apply(ai)`: the existing, board-verified class, called again |

**Why needle 4 instead of cc-wiki's reader.**
- `AliasTargetTheme` → `ManifestJsonFallback.activityTheme` already returns `0x7f120252` for fd-api on the board.
- It is a no-op for non-aliases and for aliases whose target declares no theme.
- Calling it after the overwrite completes the existing design: J10d already leaves aliases to AliasTargetTheme. No new
  manifest reader is added, and no BinaryAndroidManifestOrientation method.

**Not included: the chessclock `ActivityManagerAdapter.nativeConsumeConnectionFailure(I)Z` declaration**
(`evidence/chessclock-nsme-scope.txt`).
- **Wrong layer.** `adapter.activity.ActivityManagerAdapter` is defined in the BCP `oh-adapter-framework.jar` 2257b835,
  not in the runtime JAR. A runtime-JAR class cannot add a method to a boot class: parent-first delegation means the boot
  definition always wins.
- **Cost and prediction.** The fix is a BCP edit plus an FZ-005 bake. Only chessclock hits the NSME, in 1 run, and its
  first fatal stays `InvalidDisplayException` (the window-session bridge). Predicted first-fatal move = 0, so per AGENTS
  it is not built.
- **Pointer, not investigated further.** In that pid, `[B34.1] JNI_OnLoad: oh_adapter_bridge entered` appears twice: on
  the main thread at 08.361, then via `MediaPlayer.<clinit>` loadLibrary at 09.133. The NSME comes from the second
  registration pass.

## Gates

| gate | result |
|---|---|
| two builds | **byte-identical** `20e748e5` (`logs/build-v1.log`) |
| smali vs base 0349eb83 | changed = exactly `AppSchedulerBridge`, `B7BindFixes` (the 4 insertions + label renumbering); added = the 5 `TrampolineFinishOrder*` classes; 0 dropped |
| `deployed_class_diff --deployed 0349eb83 --frozen` | 0 dropped, 0 reshaped, 0 added after allowing the 5 classes, **0 frozen classes broken** (`gates/class-diff-vs-0349eb83.txt`) |
| `deployed_class_diff --deployed bbc3f530 --frozen` (U13, on the boards) | the same with InProcessBindOrder ×3 (U14) also allowed (`gates/class-diff-vs-bbc3f530.txt`) |
| `check_frozen.py` | 8 entries, 0 violations |

## Behaviour on host ART (`test/`, `evidence/host-art-*.log`)

**Setup.**
- `TrampolineOrderTest` runs on hw248 `dalvikvm64 -Xint` with the nine BCP jars plus U14's test-only Log/SystemClock shim
  `58fc36ea`.
- It drives the real framework `ActivityTaskManager.getService()` singleton, `ActivityClient.setActivityClientController`
  / `getInstance().finishActivity`, `ActivityThread.currentPackageName` and `Handler` / `MessageQueue`.
- The OH-backed adapters, whose bodies are OH natives, are recording proxies of the same interfaces.

**Needle effects in the test.**
- Needle 2 is modelled as the controller handed to `setActivityClientController`.
- Needle 3 is modelled as the `onLaunchAbility` call.
- The U14 jar has neither, which is the negative control.

| case | U15 v1 `20e748e5` | U14 v1 `0349eb83` (control) |
|---|---|---|
| 1 x: own-package start, `finish()` ×2, the launch arrives 0.1 s later | **PASS**: TerminateAbility before the launch = 0, after = 1 | **FAIL**: before = 2 (the board's rc=0 + rc=22 pair, ahead of the launch = `[ARM938]`) |
| 2 the started ability never arrives | PASS: held, released once by the timeout at +3001 ms | (no hold; forwarded at +0 ms) |
| 3 start into another package | PASS: forwarded at once | PASS |
| 4 implicit start (no component or package) | PASS: forwarded at once | PASS |
| 5 failed own-package start (rc −1) | PASS: forwarded at once | PASS |
| 6 `finish()` twice, no start | **PASS**: 1 TerminateAbility | **FAIL**: 2 |
| 7 other controller calls (`isTopOfTask`) | PASS: pass through | PASS |
| total | **FAILURES 0, rc 0** on both the U15 bake BCP (framework 9e55e286, stubs 94a94905) and the boards' current BCP (3e106350 / 615b8bbe) | FAILURES 2, rc 1 on both |

**Harness fix during the run.** In the first run, case 1 drained the queue "before the launch" with the waiting drain,
which itself fired the 3 s timeout. The fixed harness runs only the messages already due at that point, which is what
the main thread does between two binder callbacks.

**fd-api on host.** `ManifestJsonFallback.activityTheme` reads the APK through AssetManager / XmlResourceParser (native
libandroidfw), and host ART lacks it. cc-wiki's T1 checks her reader, which is not used here; its assertion (alias
`0x1030237` → `0x7f120252`) is already met on the board by the existing reader (`[B8-ALIASTHEME]`). What U15 changes is
only the order. That is checked statically: the needle sits after `iput sEnrichedTheme` and before `J10dTheme.restore`
on the same ActivityInfo that `LaunchActivityItem` holds by reference; `scheduleTransaction` comes after line 1763. The
proof is T3 on the board.

## Prediction (first fatal) and board criteria

| key(s) | prediction |
|---|---|
| **x** | XLiteActivity is launched in the first process ~0.1 s after the start instead of a second cold start ~11 s later. **Lit: medium** (its own init walls are unknown). |
| the 35 other trampoline keys (`../2026-10-03-x-trampoline-handover/evidence/trampoline-keys.txt`, mostly lit) | first fatal 0; each saves the 1.7–2.7 s second cold start and the stranded first process |
| **fd-api** | moves past `need a Theme.AppCompat theme` (high). Next wall unknown; the background `LocalSocketImpl.bindLocal` ULE is non-fatal. |
| the 8 other aliases whose target theme ≠ app theme (U13 `[B8-ALIASTHEME] re-resolved`) | now launch with the target's theme (AOSP behaviour). wikipedia `0x7f13002a`, fd-notes / fd-gallery / fd-filemanager / fd-calendar / fd-musicplayer SplashActivity, fd-im-vector-app, fd-fennec_fdroid. **Regression watch**: wikipedia and the lit Fossify apps; vector/fennec die before launch, so they are unaffected. |
| aliases whose target theme = app theme or none (`theme unchanged`) | 0 |

**Board criteria (T3, deploy owner; screenshots are ground truth):**
1. **x:**
   - `[TFO] IActivityTaskManager start observer installed` and `[TFO] IActivityClientController finish order proxy`;
   - `[TFO] startActivity -> own-package com.twitter.x.lite.XLiteActivity`, then `[TFO] finishActivity held`, then
     `[TFO] com.twitter.x.lite.XLiteActivity launched in this process; releasing held finish`;
   - **no `[ARM938] ability is the last: com.twitter.android`**;
   - **no second `ensureBindApplication` pid / no second AttachApplication** for com.twitter.android;
   - `[B47-SLA] ScheduleLaunchAbility: ability=com.twitter.x.lite.XLiteActivity` in the **first** pid;
   - the t20 screenshot shows x's own UI.
2. **Trampoline keys (e.g. privacyfriendly*, binaryeye, gallery):** the same three `[TFO]` lines, no `[ARM938]`, one pid,
   lit state unchanged.
3. **fd-api:** no `IllegalStateException: You need to use a Theme.AppCompat theme`, and a t20 shot.
4. **Alias regression watch:** wikipedia and the Fossify splash keys still lit at t20.
5. **Everywhere:** no `[TFO] … failed` / `not installed` lines; no `[TFO] no launch within 3000 ms` on keys that do not
   start an own-package activity.

## Rules this round sets

- **Before adding a "write X" fix, trace every later write to X in the same path.** The target theme was already being
  written; a later unconditional write undid it, and a third step deliberately skipped repairing it.
- **A runtime-JAR fix cannot add members to a BCP class** (parent-first). Check which jar defines the class before
  promising a "small JAR fix".

## Files

- `build_v1.py`, `src/adapter/activity/TrampolineFinishOrder.java`, `compile-only/android/app/IActivityClientController.java`.
- `gates/`: needle diffs, class-diff vs 0349eb83 and vs bbc3f530.
- `test/`: `TrampolineOrderTest.java`, `build_test.py`, `run_trampoline.sh`.
- `evidence/`:
  - `host-art-run-{u15bcp,u14board}-{u15-v1,u14-v1}.log`, `hw248-inputs.txt`;
  - `fd-api-theme-order.txt`, `chessclock-nsme-scope.txt`.
- `logs/`: build logs. `results.json`.
