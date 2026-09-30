# Route-A window-loss layer analysis: fd-AppManager (white) vs fd-binaryeye (back-to-desktop)

READ-ONLY forensics. No board was touched. Everything below is quoted from local `hilog.txt` with line numbers.

- **Run**: `runs/second-activity-32df-r17s-20260930T091516/5ea34a4500000000000000001123012c/` (5ea, fresh clean-install)
- **Runtime**: 32dfac83 (route-a; `facts.txt` fingerprint `8556976c1c39`) + JAR r17s `3b523289`
- **Baseline compared**: r17p (runtime 9e14bf20 + JAR r17p `a0ed5c4f`), `../../westlake-harness/benchmark/2026-09-30-r17p-5ea-sweep/runs/r17p-all-5ea/5ea34a4500000000000000001123012c/`
- **hilogs**: `fd-AppManager/hilog.txt` (47250 lines), `fd-binaryeye/hilog.txt` (48693 lines)

## TL;DR discriminator (LaunchActivityItem.execute → onCreate ran?)

For BOTH apps the second activity's `LaunchActivityItem` **is scheduled AND its onCreate runs**. So neither is an OH "never scheduled the launch" failure. The two then diverge:

| App | 2nd activity onCreate ran? | onResume ran? | Own window added? | Lost layer |
|---|---|---|---|---|
| fd-AppManager `KeyStoreActivity` | YES (`performCreate` L43340) | reached OH RESUMED (L42101), but activity is `mFinished=true` | **NO** (`mWindowAdded=false decorClass=null`, L44262) | activity finishes without adding a window → foreground scene 503 has `totalSurfaces:0` → white |
| fd-binaryeye `CameraActivity` | YES (`performCreate` L44029) | YES — and **threw** in onResume (L44029–44277) | NO (exited before layout) | app `System.exit(1)` from uncaught `IllegalStateException` (CameraX) → SCB tears down orphaned scene 508 |

The r17c walls note ("OH never schedules the target's LaunchActivityItem") is **stale** — see the baseline section; by r17p AND r17s the launch is scheduled and onCreate/onResume run. These are now *post-launch* walls, not ability-launch walls.

---

## App 1 — fd-AppManager: KeyStoreActivity renders WHITE

SplashActivity (`persistentId 502`) starts second activity `io.github.muntashirakon.AppManager.crypto.ks.KeyStoreActivity` (`persistentId 503`, child pid 16115). t20 self-read = blank white; app process alive; **0 System.exit**, **0 exit-with-code** (`grep -c "System.exit called"` = 0; `processes-t20.txt` still lists pid 16115).

### Pipeline trace (numbered)

1. **Start reaches OH** — `OH_ATMJNI nativeStartAbility` (L41443) + `OH_AbilityMgrClient StartAbility` (L41444), `StartAbility returned 0` (L41456).
2. **WMSLife activation + LaunchActivityItem scheduled + onCreate ran** —
   - `WMSLife PendingSessionActivation ... KeyStoreActivity ... requestId:148` (L41474); `RequestSceneSessionActivationInner [id: 503]` (L41820); `AMS StartUIAbility session:503` (L41833); `LoadLifecycle KeyStoreActivity` (L41845).
   - `[BRIDGED] ScheduleLaunchAbility(recordId=327) -> scheduleTransaction(LaunchActivityItem)` (L41908); `[B47-SLA] ENTRY ... KeyStoreActivity recordId=327` (L41965); `[B47-SLA] AFTER scheduleTransaction OK` (L42097).
   - `KeyStoreActivity performCreate 90ms` (L43340). **onCreate RAN.** OH drives it to RESUMED: `OH callback (direct token): state=INITIAL->FOREGROUND -> RESUMED activityToken=Binder@b7c6782` (L42101).
3. **relayout — NEVER RAN for KeyStore.** There is exactly ONE `addToDisplay` and ONE `[OH_WSA-relayout]` in the whole log, and both belong to **SplashActivity** (token `c8c47d3`):
   - `[OH_WSA] ENTRY addToDisplay attrs.token=Binder@c8c47d3` (L41870);
   - `[OH_WSA-relayout] session=504 requestedWH=0x0 sessionInfo[3,4]=1200x1920 -> useWH=1200x1920` (L42438), `outFrames ... Rect(0,0-1200,1920)` (L42467), `created persistent SurfaceControl session=504 surfaceNodeId=69213397975041` (L42472), `SURFACE_CHANGED (firstCreate=true)` (L42473). **This is Splash's relayout; it is valid 1200×1920.** No second relayout for KeyStore ever appears.
4. **BLAST buffer — created for Splash only.** `OH_SurfaceControl SC.create 'OH_Surface_504' 1200x1920` (L42471), `BBQ.create name=VRI[SplashActivity]` (L42507), `BBQ.getSurface ... sessionId=504` (L42517). The one app content surface `AdapterActivityContent` (node `69213397975043`) is parented **under the SplashActivity surface node** `69213397975041` (L42036), which is under `WindowScene_AppManager502` (L42635). KeyStore's own scene `WindowScene_AppManager503` is created (L42481) but composited with `subDraw ... totalSurfaces:0,totalNodes:1` (**L42770**) — **zero child surfaces, i.e. no app buffer**.
5. **Why KeyStore has no buffer — it finishes without a DecorView/window.** The adapter's periodic visibility probe contrasts the two activities directly:
   - Splash (`c8c47d3`): `mFinished=false mWindowAdded=true decorClass=DecorView decorSize=1200x1920 lifecycleState=3` at T=500ms…8000ms (L46610).
   - KeyStore (`b7c6782`): **`mFinished=true mWindowAdded=false hideForNow=false lifecycleState=1 decorClass=null decorSize=-1x-1`** at T=500ms (**L44262**) and still at T=8000ms (**L46642**). Also `setAppVisibility: viewRoot null (decor not attached) token=Binder@b7c6782` (L43348).
   - The transition then hides Splash: `SCBSceneContainer ... SplashActivity (persistentId: 502) enableShow change from true to false` (L44102), and Splash's scene/window are detached: `OnDetachFromFrameNode id: 502 ... AppManager` (L44126) / `id: 504 ... SplashActivity` (L44130). KeyStore's scene 503 is the focused window (`windows.txt`: `Focus window: 503`) but empty.
   - The adapter nonetheless emits a **false** first-frame: `activityResumed (first-frame): OH AbilityTransitionDone(token=0x7f292b64c0, state=9)` (L44311) even though `mWindowAdded=false`/`decorClass=null` — no frame was ever drawn for KeyStore.
   - Runtime also rewrote the theme: `[B8-ATHEME] KeyStoreActivity theme=0x7f130016 (was 0x7f13000b)` (L42081). KeyStore is a dialog/password activity (`displayInputKeyStoreAliasPassword`, `TextInputDialogBuilder.create()` L40260, `AlertDialog` L36944); on a fresh install with no keystore it evidently finishes without presenting/adding any window.

### Exact lost layer (AppManager)

**(d)-ish, not (a)/(b)/(c): the second activity ran onCreate and reached RESUMED but marked itself `mFinished=true` and never added a DecorView/window (`mWindowAdded=false`, `decorClass=null`).** Therefore relayout never ran for it, no SurfaceControl/BLAST buffer was ever created for its scene, and its foreground scene `WindowScene_AppManager503` has `totalSurfaces:0` → white. The one valid surface/BLAST buffer belongs to SplashActivity, whose scene is hidden behind. This is **NOT** a 0×0 relayout, **NOT** a BLAST sync-transaction failure, **NOT** a crash.

### Did the app child run the activity? YES — `LaunchActivityItem` scheduled (L41908) and `performCreate` (L43340). Discriminator = "ran but didn't add a window / finished", not "OH didn't schedule it".

### Minimal fix proposal (AppManager)

Honest verdict: the dominant cause is **app behavior** — KeyStore (a keystore-password dialog activity) finishes on a fresh, keystore-less, non-interactive launch without ever adding a window. That is not cleanly fixable in the runtime, and the white lingers because a finished, window-less activity's SCB scene is left focused rather than torn down / returned to caller (an **OH/SCB scene-lifecycle** aspect). The one clean runtime-side fix:

- **[JAR→cc-t3 r17t]** In `OH_ACCAdapter.activityResumed` / the first-frame gating (the code that logs `activityResumed (first-frame): AbilityTransitionDone state=9`), **gate the first-frame/foreground-done signal on an actually-added, drawn window** (`mWindowAdded==true && decorClass!=null && a real frame acquired`). When the resumed activity is `mFinished`/window-less, do **not** report `AbilityTransitionDone state=9` (L44311); report the transition as finished-without-window so OH/SCB can tear the empty scene down instead of keeping a white focused scene. Class/method: the adapter that owns `OH_ACCAdapter`/`OH_LifecycleAdapter` first-frame deferral (`activityResumed`, the OnDrawListener attach path at L42123/L43636).
- Secondary **[JAR→cc-t3 r17t]**: verify the `B8-ATHEME` theme remap `0x7f13000b→0x7f130016` is not itself substituting a translucent/dialog theme that suppresses the decor; if it is, correct the theme mapping. (Lower confidence; `mWindowAdded=false` dominates.)

**Unknowns / needs board capture (AppManager)**: (i) whether KeyStore.onCreate calls `finish()` by app logic vs. an `AlertDialog.show()`→addToDisplay that silently no-ops — decisive evidence would be the KeyStore `wantJson` extras + a `hidumper -s WindowManagerService -a -a` at t5 showing scene 503's state (finished/orphan) and z-order; (ii) whether OH would tear down scene 503 given more time (capture window is only ~11s of hilog).

---

## App 2 — fd-binaryeye: CameraActivity flashes then returns to desktop

SplashActivity (`persistentId 507`, first child pid 19895) starts `de.markusfisch.android.binaryeye.activity.CameraActivity` (`persistentId 508`, **new** child pid 19955). t20 self-read = launcher/desktop.

### Pipeline trace (numbered)

1. **Start reaches OH** — `OH_ATMJNI nativeStartAbility ... CameraActivity, callerOhToken=0x7f29c9be20` (L28504). SplashActivity then finishes itself: `finishActivity: OH TerminateAbility(token=0x7f29c9be20, code=0) rc=0` (L28531); Splash had drawn a real frame first (`activityResumed (first-frame) token=0x7f29c9be20` L30580).
2. **New process + LaunchActivityItem + onCreate ran** — pid 19955 spawns (`WindowSessionAdapter` natives registered L32380); `[BRIDGED] ScheduleLaunchAbility(recordId=331) -> scheduleTransaction(LaunchActivityItem)` (L33114); `[B47-SLA] ENTRY ... CameraActivity recordId=331` (L33132); `CameraActivity performCreate 97ms` (**L44029**). **onCreate RAN.**
3. **relayout — never reached** (process died during onResume, before layout). No `addToDisplay`/`[OH_WSA-relayout]`/`SC.create`/`BBQ.create` exist for pid 19955.
4. **BLAST buffer — never created** for CameraActivity (see 3).
5. **Teardown trigger = app `System.exit(1)` from an uncaught exception in onResume** —
   - `CameraActivity handleStartActivity` (L44102), then in onResume: `CameraX: Failed to retrieve default CameraXConfig.Provider from meta-data` followed by `android.content.pm.PackageManager$NameNotFoundException: ComponentInfo{de.markusfisch.android.binaryeye/androidx.camera.core.impl.MetadataHolderService}` at `ApplicationPackageManager.getServiceInfo` (**L44259–44277**), thrown from `CameraActivity.onResume` → `performResume` → `ResumeActivityItem.execute`.
   - Result: `[CHILD_CK] J_invokeStaticMain_main_threw: java.lang.RuntimeException: Unable to resume activity {...CameraActivity}: java.lang.IllegalStateException: CameraX is not configured properly. The most likely cause is you did not include a default implementation ... 'camera-camera2'` (**L44281**) → **`System.exit called, status: 1`** (**L44333**) → `de.markusfisch.android.binaryeye with pid 19955 exit with code:1` (**L44339**).
   - THEN the window teardown: `AMS TerminateAbility CameraActivity` (L44370), `terminateAbility app unexist` (L44419), `SCBScenePanelViewModel onTerminateScene ... (persistentId: 508) ... isSessionException=true` (L44425), `onTerminateScene, back to desktop` (L44431), `requestSceneContainerDestructionWithTransition` (L44440). So `enableShow→false`/destruction is a **downstream consequence of the process exit**, NOT an SCB-side decision, NOT a 0-size relayout, NOT a buffer timeout, NOT app `finish()`.

Note the `MetadataHolderService` class IS present in-process (`class_linker VTLEN klass=androidx.camera.core.impl.MetadataHolderService` L44189) and the self-projection proxy IS installed (`[SELF-UID] installed for de.markusfisch.android.binaryeye ... over adapter.packagemanager.PackageManagerAdapter` L34711) — but `getServiceInfo` for the app's OWN `<service>` still returns `NameNotFound`.

### Exact lost layer (binaryeye)

**(d) app-side exit before first frame — root-caused by a runtime PackageManager self-component gap.** CameraX bootstraps by calling `PackageManager.getServiceInfo(<self>/MetadataHolderService)` to read the default `CameraXConfig.Provider` from that service's `<meta-data>`. The runtime's PackageManager path answers **NameNotFound for the app's own service**, so CameraX stays unconfigured, onResume throws `IllegalStateException`, and the uncaught exception makes the child call `System.exit(1)`. SCB then tears the orphaned scene 508 down to desktop.

### Did the app child run the activity? YES — `LaunchActivityItem` scheduled (L33114) and `performCreate` (L44029), and onResume ran far enough to throw. Discriminator = "ran, then app-exited in onResume", not "OH didn't schedule it".

### Minimal fix proposal (binaryeye)

- **[JAR→cc-t3 r17t]** Extend the runtime self-component projection to answer `getServiceInfo` for the app's OWN declared services. In `adapter.packagemanager.PackageManagerAdapter` (and the `adapter.activity.SelfUidPackages` `InvocationHandler` that already wraps it, L22738/L34711), intercept `IPackageManager.getServiceInfo(ComponentName, flags, userId)` — and the companions `queryIntentServices` / `resolveService` (slots 116/171/184, L34607/34662/34675) — for the self-package and return a `ServiceInfo` built from the already-parsed `AndroidManifest.xml` **including `<meta-data>`** (CameraX reads the provider class name from the service's meta-data). This is the exact same self-projection family as commit `a08270c0` (SelfUidPackages `getPackagesForUid`/`getNameForUid`) and the `[B43-BIND]` self-provider work (`SelfComponentFallback.load` already reads the manifest, `providers populated: 2` L35057) — this just adds `<service>`-with-meta-data. JAR-layer, architecture-independent, no boot-image change.
- **Not native/cx-t0**: the failing call resolves to the JAR `$Proxy18`→`PackageManagerAdapter` occupant (L34607), and the fix is answerable entirely from the in-process parsed manifest; no `liboh_*` native change is required.

**Unknowns / needs board capture (binaryeye)**: whether other CameraX/self-`<service>` consumers need `queryIntentServices`/`resolveService` (not just `getServiceInfo`) — confirm by re-running after the JAR fix and grepping for residual `NameNotFoundException` on self components. The camera hardware/permission path is untested (blocked upstream by this crash).

---

## Baseline comparison (r17p) — proves both are stable post-launch walls, not this-runtime regressions

In the r17p sweep, the SAME two second activities already launched and ran onCreate:
- AppManager: `scheduleTransaction(LaunchActivityItem)` (L42139) + `KeyStoreActivity performCreate 13ms` (L42670).
- binaryeye: `scheduleTransaction(LaunchActivityItem)` (L32837) + `CameraActivity performCreate 91ms` (L43647) + the **identical** `CameraX ... NameNotFoundException: {.../MetadataHolderService}` at `getServiceInfo` in onResume (L43863–43874).

So 32df/r17s did **not** change these two outcomes (no fix, no regression), and the older "OH never schedules the target's LaunchActivityItem" characterization no longer holds for these apps.

## Rule set by this analysis

1. For "second-activity white / back-to-desktop" walls, the FIRST discriminator is `LaunchActivityItem` scheduled + `performCreate` present (onCreate ran) — if yes, it is a *post-launch* wall (window/surface, app exit, or self-component), never an ability-launch wall. Grep `scheduleTransaction(LaunchActivityItem)` and AndroidEventLog `performCreate`, not just the screenshot.
2. "White" ≠ "0×0 relayout". Distinguish with the adapter VIS probe (`mWindowAdded`/`decorClass`/`mFinished`) and the scene's RS `subDraw ... totalSurfaces:N`. `totalSurfaces:0` on the focused scene = no app buffer = white; check whether a window was even added before blaming relayout/BLAST.
3. A `requestSceneContainerDestructionWithTransition` / `enableShow→false` after an `exit with code:1` is an EFFECT of the app process exiting (`isSessionException=true`), not an SCB teardown decision — always locate the `System.exit`/uncaught-exception line first.
