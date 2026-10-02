# M6: why the caller never comes back — the break is in the bridge's ability scheduler, not the JAR (→ U14)

#90, offline, no board. The question was: when a started Activity finishes at once without a window (fd-AppManager's
KeyStoreActivity), who should bring the caller back, and where does our chain break?

**Answer.** The close is not lost in the JAR. OH defers it: `CloseUIAbility` on an ability whose foreground is still
pending only sets a pending BACKGROUND. The ability then needs the app to acknowledge **BACKGROUND** and **INITIAL**
before AMS terminates it and SceneBoard drops its scene. Route A never acknowledges either:
- the app process never receives OH's background/terminate transactions at the Java layer;
- in U5/U7 the bridge's FGGUARD vetoes BACKGROUND_NEW;
- in U10.1T8 no scheduler transaction is logged at all.

So the windowless top scene stays, and the caller stays backgrounded.

**Fix layer:** bridge `AbilitySchedulerAdapter` (deployed `84695d62`, no reproducible source) → **U14**. No U13 JAR fix
is offered.

**Population (runtime, U10.1T8 signing runs):** the close of the **top** ability is dropped in white 2/16 (fd-AppManager,
termux) and lit 0/117. Dropped closes of a covered ability (harmless leaks) occur in 34 lit keys.

## What was wrong in the previous reading (`white-unexplained-4`)

That reading said "AMS had already moved Splash to background and nothing re-foregrounds it". Reading the raw lines
in order, with OH 6.1 LTS's `ui_ability_lifecycle_manager.cpp` (hw248
`/opt/build-trees/oh610_lts_source`, sha 678c5e00…) next to them, shows this instead:

- `AbilityTransitionDone, ability:…, state:5` is **the app's** report of the foreground it deferred to first frame.
- `BackgroundLifecycle …` is **AMS dispatching** "go to background" to the app, not a completed state.
- The close of KeyStoreActivity was **dropped**: `[UALM2093]pending state dropped CLOSE: 9`. Its scene
  `WindowScene_AppManager661` keeps being drawn every frame until t20, so it is never removed.

## The chain, line by line (fd-AppManager, window 5, 5cd)

| t (16:52:…) | where | event |
|---|---|---|
| 52.97x | AMS | SplashActivity foreground; it starts KeyStoreActivity; SCB `requestSceneSessionBackground` for Splash (scene 660); KeyStoreActivity foreground pending (scene 661) |
| 52.648 | AMS | `[UALM1363]pending state dropped MINIMIZE: 9`: SceneBoard's minimize of Splash is deferred the same way, because Splash's own FOREGROUND is still pending (our `activityResumed` defers the FOREGROUND report to first frame) |
| 52.978 | AMS | `CloseUIAbility call: …KeyStoreActivity` (our `finishActivity` → `TerminateAbility`, sent from `onCreate`) |
| 52.979 | AMS | **`pending state dropped CLOSE: 9`**: KeyStoreActivity's FOREGROUND (9) is still pending, so `CloseUIAbility` only sets pending BACKGROUND and returns. `PrepareCloseUIAbility` has already put it on `terminateAbilityList_` and sent the result to Splash. |
| 53.074 / 53.075 | app → AMS | the deferred `activityResumed (first-frame): AbilityTransitionDone(Splash, 9)` arrives (AMS logs `state:5`); AMS dispatches `BackgroundLifecycle Splash` (the pending background from step 1) |
| 53.876 / 53.877 | app → AMS | the deferred first-frame FOREGROUND for KeyStoreActivity arrives; AMS applies its pending BACKGROUND and dispatches `BackgroundLifecycle KeyStoreActivity` |
| 53.9 … 04.15 | – | **nothing**: no BACKGROUND acknowledgement for either ability, so no `CompleteBackground`, no `Terminate`, no `CompleteTerminate`. Scene 661 is redrawn every frame (46 watermark lines up to 16:53:00); Splash's window 662 is reported `visibleState 2` (totally occluded); at 58.69 WMS logs "Window attach state and session state mismatch … persistentId:661". |

## What OH expects (6.1 LTS source)

1. **`CloseUIAbility`.** If `GetPendingState() != INITIAL`, it does `SetPendingState(BACKGROUND)` and returns ERR_OK.
   The close waits for the foreground to finish.
2. **Foreground done.** The pending BACKGROUND is dispatched (`BackgroundLifecycle`). The app must answer
   `AbilityTransitionDone(BACKGROUND)` → `CompleteBackground`.
3. **`CompleteBackground`.** It terminates every BACKGROUND ability on `terminateAbilityList_` (`Terminate` dispatches
   INITIAL). The app must answer → `CompleteTerminate` → the session is destroyed and SceneBoard reveals the scene
   below.

   That is the OH equivalent of Android's "finish returns to the Activity below and it resumes". On Android, starting a
   translucent Activity does not stop the caller; on OH SceneBoard the caller's scene is backgrounded, and coming back
   relies on step 3 finishing.

## Where route A breaks: the app never acknowledges BACKGROUND / INITIAL

| | U5/U7 paired runs (8 runs) | U10.1T8 signing runs (133) |
|---|---|---|
| Java `OH callback (direct token)` | only `INITIAL->FOREGROUND` (16) | only `INITIAL->FOREGROUND` (182) |
| Java BACKGROUND callbacks | 0 | 0 |
| bridge `[BRIDGED] ScheduleAbilityTransaction` | 3 per run | **0** |
| bridge `[FGGUARD]` lines | 3 per run, incl. `VETO false init-phase BACKGROUND_NEW … not dispatching StopActivityItem` | 0 |
| AMS `BackgroundLifecycle` (dispatch) | – | in 46 runs |
| AMS `pending state dropped CLOSE` | – | in 36 runs |

**JAR side, ready if called.** `LifecycleAdapter.dispatchOhLifecycleByActivityToken` maps BACKGROUND_NEW to STOPPED;
the transaction path is `AbilitySchedulerAdapter::ScheduleAbilityTransaction` (bridge, native) →
`AbilitySchedulerBridge.onScheduleAbilityTransaction` → `LifecycleAdapter`.

**Bridge side, where it stops.** Background/terminate transactions either do not reach the bridge's scheduler (U10.1T8:
not even the `[BRIDGED]` entry log) or are vetoed there (U5/U7 FGGUARD). The bridge strings are present in the
deployed `84695d62`:
- `[BRIDGED] ScheduleAbilityTransaction: tokenAddr=0x%llx targetState=%d isNewWant=%d`;
- `[FGGUARD] VETO false init-phase BACKGROUND_NEW …`;
- `[FGGUARD] pass-through BACKGROUND_NEW …`.

Either way, nothing reaches the Java lifecycle that would produce the acknowledgement. That is the native
bridge/scheduler layer, not `ActivityClientControllerAdapter`.

**Amplifier on the JAR side, not the break.** The deployed `ActivityClientControllerAdapter.activityResumed` defers
the FOREGROUND report to the first drawn frame (`OnDrawListener attached, FG deferred to first frame`). For a while
every ability is "foreground pending", so OH defers both SceneBoard's MINIMIZE of the caller and the app's CLOSE of the
finishing Activity. Without the deferral, both would still wait for the BACKGROUND acknowledgement that never comes.

**Why not a JAR fix.** `ActivityClientControllerAdapter` is in `oh-adapter-framework.jar` (BCP, 2257b835), not in the
U13 runtime/stubs jars (0482c9b1 / 615b8bbe). Even there, reordering `finishActivity` (FOREGROUND done before
`TerminateAbility`) only turns the dropped close into `CloseUIAbilityInner` → `MoveToBackground`, which waits for the
same missing BACKGROUND acknowledgement.

A runtime-jar workaround is conceivable: on `onActivityDestroyed` of an Activity that never added a window, blindly
send `AbilityTransitionDone(BACKGROUND)` then `(INITIAL)` through the BCP native by reflection. It races AMS's state
checks (`CompleteBackground` requires BACKGROUNDING) and is unverified. If wanted, it needs a ≤ 30 min board
experiment first, not a build.

## Who else goes this way (`closes.py` → `closes.csv`, runtime, U10.1T8 signing runs)

| class | white (16) | lit (117) |
|---|---|---|
| **top_dropped**: the dropped close is the top (last requested) ability, nothing foregrounded after it | **2**: fd-AppManager (KeyStoreActivity), termux (TermuxActivity) | **0** |
| under_dropped: a dropped close of an ability that something later covered (leaked scene behind; e.g. antennapod Splash → Main) | 0 | 34 |
| no_dropped | 14 | 83 |

- The 34 lit keys leak a windowless scene behind their top Activity on every launch. It is harmless at t20, but the
  same U14 fix cleans it up.
- **termux:** `TermuxActivity.onCreate` returns right after `TermuxAppSharedPreferences.build(context, true)` returns
  null (dexdump: `0x0026` build → `if-nez` → `return-void`). It cannot get its own package context and finishes.
  Termux has no caller below, so with M6 fixed its top scene goes away and the launcher shows: **not lit**. Its own
  wall is the package-context lookup (separate).

**Predicted moves:**

| fix | moves |
|---|---|
| U13 | 0 |
| U14 bridge scheduler (deliver + acknowledge BACKGROUND / INITIAL, no FGGUARD veto for a finishing Activity) | **+1**: fd-AppManager back to its own splash (medium; it may then wait for the KeyStore result) |
| termux | 0 (separate wall) |

## Rule this round sets

- AMS `AbilityTransitionDone state:N` is the **app's** report and `BackgroundLifecycle` is AMS's **request**. Neither
  is a completed state.
- A "nothing came back" diagnosis must follow OH's terminate protocol (dropped close → pending BACKGROUND → app
  BACKGROUND ack → `CompleteBackground` → `Terminate` → app INITIAL ack) and name the first missing acknowledgement.

## Files

- `closes.py` → `closes.csv`: dropped-close classification for all 133 signing runs.
- `evidence.txt`: the fd-AppManager lines, the OH source excerpts, and the per-generation scheduler counts.
