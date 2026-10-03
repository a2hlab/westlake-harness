# U16 t3: synchronous onStart within the launch transaction — design

## The defect (from benchmark/2026-10-03-u16-unowned-diag, fd-breezyweather)
fd-breezyweather dies with `UninitializedPropertyAccessException: lateinit property weatherView` thrown from a
`Handler` callback the app posted during `onCreate`. Cause: on route-A, `onStart`/`onResume` are dispatched as a
**separate posted main-Looper transaction** (the OH FOREGROUND callback), so an app runnable queued during
`onCreate` runs **before** `onStart` — and `weatherView` is assigned in the fragment's `onCreateView`, which runs
during `onStart`. On stock Android `handleLaunchActivity` runs `onCreate -> onStart -> onResume` synchronously in
one transaction, so `onCreateView` precedes the posted runnable.

## AOSP 14 order (the reference)
`ActivityThread`: the launch `ClientTransaction` carries a `LaunchActivityItem` (callback) and a lifecycle
state request; `TransactionExecutor.execute()` runs `executeCallbacks()` (→ `performLaunchActivity` = onCreate,
then cycles toward the callback's post-execution state) then `executeLifecycleState()` (cycles to the requested
final state). In the normal cold launch the final state is `ON_RESUME`, so `onCreate -> onStart -> onResume` all
run in that one main-thread transaction (`handleLaunchActivity` → … → `handleResumeActivity`). The fragment's
`onCreateView` runs during `onStart` (FragmentController `dispatchActivityCreated` / `execPendingActions`), i.e.
before control returns to the Looper.

## Route-A today (the deviation — AppSchedulerBridge)
Two-phase OH protocol (G2.14m, 2026-05-01):
  1. `ScheduleLaunchAbility` → launch `ClientTransaction` = `LaunchActivityItem` with **no** lifecycle state
     request → stops at **ON_CREATE** (onCreate only).
  2. `ScheduleAbilityTransaction(FOREGROUND_NEW)` → `AbilitySchedulerBridge.onScheduleAbilityTransaction` builds a
     `ResumeActivityItem` (ON_RESUME), dispatched by `LifecycleAdapter.dispatchByActivityToken`, which
     `Handler(mainLooper).post(...)`s the whole transaction (so onStart+onResume run later, async).
G2.14m removed an earlier `setLifecycleStateRequest(ResumeActivityItem)` at launch because resuming immediately
raced the AMS state machine (AMS still `INACTIVE`, expects `FOREGROUNDING` before `AbilityTransitionDone(FG)`) →
`rc=22 ERR_INVALID_VALUE`. **That AMS race is the reason the fix must not simply resume at launch.**

## The fix (prototype) — advance to ON_START at launch, keep onResume in phase-2
One line in `AppSchedulerBridge` after `transaction.addCallback(launchItem)`:
```java
transaction.setLifecycleStateRequest(
        android.app.servertransaction.StartActivityItem.obtain(/* activityOptions */ null));
```
`StartActivityItem.getTargetState() == ON_START`. The launch transaction now runs `executeCallbacks` (onCreate)
then `executeLifecycleState` → `cycleToPath(ON_START)` → **onStart**, synchronously, in the one main-thread
transaction — so `onCreateView` (and the lateinit view assignments) run before the Looper processes any
onCreate-posted runnable. **onResume is NOT requested here**, so phase-2 (`FOREGROUND` callback → `ResumeActivityItem`
→ `cycleToPath(ON_RESUME)` from ON_START) still fires onResume after AMS `FOREGROUNDING`. The G2.14m AMS
handshake is therefore unchanged (the rc=22 race was onResume-vs-FOREGROUNDING; onStart sends no
`AbilityTransitionDone(FG)` — AOSP fires no IPC between onCreate/onStart and onResume, per LifecycleAdapter).

Why ON_START (not the full AOSP ON_RESUME): ON_RESUME at launch reintroduces the G2.14m rc=22 AMS race and also
`addView`s the decor before the OH window/surface is ready (the M-family empty-surface risk). ON_START only
**inflates** the content view + fragment views (CPU-side); it does not `addView` the decor or require an OH
surface. So it fixes the ordering defect with the minimum deviation from the current (working) resume path.

## Regression risk — see evidence/risk-set.txt
- The exact "onCreate-posted callback before RESUMED" set is **not log-separable** (a heuristic gap-activity
  metric over-counts to 63 lit keys incl. inline onCreate work and misses breezyweather's own posted callback).
- Behaviourally, onStart becoming synchronous changes nothing for the **118 jvm lit keys** (onStart = surface-free
  inflation) and there are **0 surface-dependent (flutter/unity/RN) lit keys**. The **4 native-engine lit keys**
  (fd-minetest/mpv/organicmaps/stk, SurfaceView/GL) are the only on-board watch items, and even they are expected
  benign (their surface is created at window-add = onResume, not onStart, so availability is unchanged).
- Safety argument: the fix **restores stock ordering**; every app here lights on stock Android, so it tolerates
  synchronous onCreate→onStart. Only reliance on the route-A-specific async gap (a latent bug) could change.
- One protocol point to confirm on board: OH maps onStart↔onWindowStageCreate; running onStart in the launch
  transaction precedes OH's onWindowStageCreate callback — safe in theory (onStart doesn't touch the OH window
  stage), but a board run must confirm.

## Verification plan (t3, on board — not run here)
1. Build the runtime JAR with the patch; launch fd-breezyweather → the lateinit crash is gone (first fatal moves).
2. Re-run the 4 native-engine lit keys + a sample of jvm lit keys → confirm t20 unchanged (no regression).
3. Confirm no new `rc=22`/AMS-transition errors (onResume path untouched) and no onWindowStageCreate desync.
Predicted: breezyweather +1 (past the lateinit); 0 lit regressions.
