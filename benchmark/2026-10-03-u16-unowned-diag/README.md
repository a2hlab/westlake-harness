# U16 unowned-key diagnosis: fd-breezyweather, fd-saber, cv2-com-frequent-habits

#90, offline, static. The three unowned/undiagnosed keys of cc-t3's U16 wall-cluster table
(`benchmark/2026-10-03-u16-wall-clusters`, clusters Q/R/S). Per key: the first fatal verbatim + line number,
its cluster, the minimal fix, and the predicted first-fatal moves (0 means 0). Evidence per key in
`evidence/{fd-breezyweather,fd-saber,frequent-habits}.txt`.

## ① fd-breezyweather (cluster Q: dead, terminal "unknown") — an async-lifecycle ordering crash, OURS
**First fatal** (`hilog.txt:13181`, cause at `:13232`): `a96: lateinit property weatherView has not been
initialized` — a Kotlin `UninitializedPropertyAccessException`, uncaught on the **main thread**, thrown from
`org.breezyweather.ui.main.fragments.HomeFragment.v()` via a Handler callback (`b14.run:611` →
`Handler.handleCallback` → `Looper.loop` → `ActivityThread.main`); surfaced at `:13228` as
`AppSpawnXInit InvocationTargetException`, then `AMS onAbilityDied` → process dies.
**The CoroutineStart CNFE is confirmed non-fatal** (`:12961`, our own `primeCoroutineStart` prewarm) — cc-t3 right.
**Why it never reached the `weatherView` assignment:** `weatherView` is a `HomeFragment` lateinit set in
`onCreateView` (runs when the host advances to onStart/onResume via `executePendingTransactions`). `performCreate`
ran (34.809) but route-A's `OH_LifecycleAdapter` dispatches `FOREGROUND→RESUMED` as a **separate POSTED Looper
message** (`dispatchByActivityToken posted to main Looper: RESUMED`, 34.812). The app had posted a runnable
(`b14`) **during onCreate**, already queued ahead of the posted RESUMED, so it ran **first** — reading
`weatherView` before `onCreateView` assigned it. On stock Android `handleLaunchActivity` runs
onCreate→onStart→onResume **synchronously in one transaction**, so `onCreateView` executes before the Looper
processes `b14` → no crash.
- **Cluster:** not CoroutineStart. New "async-lifecycle-ordering" cluster: an onCreate-posted main-thread callback
  runs before the fragment `onCreateView` that initializes a lateinit view, because the adapter advances
  onStart/onResume via a posted message instead of synchronously in the launch transaction.
- **Minimal fix (ours — `OH_LifecycleAdapter`/`AppSchedulerBridge`):** drive onStart/onResume (→
  `executePendingTransactions` → `Fragment.onCreateView`) **synchronously within the create/launch dispatch**
  (as AOSP's `handleLaunchActivity`), or at least run pending fragment transactions before returning from the
  create dispatch, so fragment views exist before any onCreate-posted callback.
- **Predicted first-fatal moves: 1** (breezyweather past the lateinit → next wall; lit not guaranteed). Shared
  lever (other Fragment apps posting onCreate work that touches fragment views may also benefit — not counted).

## ② fd-saber (cluster R: alive-white, unclassified) — the verificationAllToken-terminate family (with x)
**First fatal:** none (alive, no crash). **Terminal mechanism** (verbatim, lines): `CloseUIAbility ...saber/MainActivity`
(`:19058`) + `callerRecordList is empty` (`:19059`) + `OH_ACCAdapter finishActivity: TerminateAbility rc=0`
(`:19062`) + `StartAbilityInner verificationAllToken failed` (`:19068`); the activity then sits
`mFinished=true, mWindowAdded=false, decorClass=null, mVisibleFromServer=false` (`:19523+`, T=0.5s→8s) — it
reaches RESUMED **already finished and never adds its window** → alive-white. Home-launched (category.HOME).
**Ruled out:** M1 single-slot Surface (0 Surface/M1-COPY/BBQ markers), Flutter raster SIGSEGV / any FATAL (none),
M3 GLSurfaceView IAE (none), dialog-under-window G (never added any window), M5.
- **Family (assigned):** the **verificationAllToken-terminate family** — same mechanism as **x** (cluster M),
  minus x's trampoline: x terminates a HOME trampoline while requesting a 2nd activity (lost hand-off); fd-saber
  is a **single activity** terminated before it adds its window. So fd-saber is the single-activity sub-case of
  x's family, **not a new family** (confirmed by `u13-white-selfterminate` + `category-home-token`: category-HOME
  is universal; the discriminator vs lit is `verificationAllToken failed`). Flutter `[B8-IMPELLER]=false`/GL-load
  are concurrent non-fatal, not the finisher.
- **Minimal fix (ours, NOT a small per-key fix):** the AMS/adapter caller-record path — give a home-launched
  ability a proper mission/caller record so `verificationAllToken` passes on the terminate/re-start path (OH AMS
  source not local; the `u13-white-selfterminate` "Fix (b)" lever).
- **Predicted first-fatal moves: 0** by any fd-saber-only fix (classification only; no small per-key fix). The
  shared AMS caller-record lever would move fd-saber **and** x together (x already owned as cluster M).

## ③ cv2-com-frequent-habits (cluster S: app_failed, desktop icon absent) — launcher icon not rasterized
**First fatal:** none — never launched; the runner finds no desktop tile to click (`record.json`: "exact desktop
icon absent across searched pages"). `aa start` lights it. **The bundle projection is correct** (`bundle.txt`):
`isLauncherAbility:true` (`:198`), skill entity `entity.system.home` (`:239`), `visible:true` (`:274`),
`mainAbility/mainElementName = com.example.MainActivity` (`:325`), label "Frequent Habits", icon path + iconId.
**But the tile is genuinely absent:** grep of the app (`Frequent Habits`/`frequent.habits`) over **all**
`icons*.json` launcher pages = **0** (other apps' tiles ARE present → the dump is valid).
**Root cause:** the Android launcher icon is **XML-only** — `aapt2 badging`: `application-icon-*: 'res/BW.xml'`;
`aapt2 xmltree res/BW.xml`: `<adaptive-icon>` (background/foreground/monochrome); `unzip -l`: no raster PNG in the
APK. The installer records `.../android/icon.png`/iconId but does not composite/rasterize the adaptive-icon layers
(the B3 DECLARED_XML_ONLY placeholder lets it install), so SceneBoard has no renderable icon → **no desktop tile**.
The ability is installed and launchable (hence `aa start` works).
- **Cluster:** launcher-side icon projection (adaptive/vector Android icon not rasterized at install; related to B3).
- **Minimal fix (installer icon projection — `apk_bundle_parser` / the android→OH icon path):** when the launcher
  icon is `<adaptive-icon>`/`<vector>` XML, composite its background+foreground layers (vector-aware) into a
  raster `icon.png` and populate iconId/iconPath, instead of the XML-only placeholder.
- **Predicted first-fatal moves: 1** — frequent-habits gets a tile → clickable/testable; `aa start` already runs
  it, so it is likely lit once reachable from the desktop. Other XML-icon corpus apps would also gain a tile (≥1).

## This round's rule
Diagnose an "unowned" key by *which layer* the stop is in, and verify the tempting label: breezyweather's death is
**ours** (our async lifecycle dispatch runs an onCreate-posted callback before the fragment view exists) not the
CoroutineStart CNFE; fd-saber's white is **not a new family** but the single-activity sub-case of x's
`verificationAllToken`-terminate; frequent-habits' "app_failed" is **not** a bind/launch failure but a missing
launcher tile because an `<adaptive-icon>` was never rasterized (the app runs fine via `aa start`). Two of three
have a clear minimal fix that each moves 1 key; fd-saber's lever is shared (0 standalone).

## Files
- `evidence/fd-breezyweather.txt`, `evidence/fd-saber.txt`, `evidence/frequent-habits.txt` — per-key first-fatal +
  line numbers, timeline, cluster, fix, predicted move.
- `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline; static (hilogs + bundle.txt + icons*.json + aapt2 on the APK); no board; no push; no fix applied. fd-saber
and breezyweather fixes are ours but in the adapter/lifecycle & OH-AMS layers (AMS source not local); the icon fix
is the installer owner's. Predicted moves are first-fatal-move predictions, to be confirmed on a future build.
Sources read read-only: the U13 stage-A run artifacts (`westlake-harness-u7-executor`), the cv2 APK
(`westlake-inputs/corpus-v2`), the U16 cluster table (`westlake-harness/benchmark/2026-10-03-u16-wall-clusters`).
