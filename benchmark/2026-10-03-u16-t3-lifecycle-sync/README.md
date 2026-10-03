# U16 t3: synchronous onStart in the launch transaction (fd-breezyweather async-lifecycle fix) + regression risk

#90, offline, no deploy. The t3 prototype for the fd-breezyweather async-lifecycle-ordering defect
(`benchmark/2026-10-03-u16-unowned-diag` ①): make `onStart` (and its `executePendingTransactions` →
`Fragment.onCreateView`) advance **synchronously within the launch transaction**, AOSP-style, so an app runnable
posted during `onCreate` can no longer run before the fragment views it depends on exist. Patch +
design note + a regression-risk scan of all U13 stage-A lit keys. (`patch/` = the one-line change;
`design/design-note.md` = the mechanism + AOSP order; `evidence/risk-set.txt` = the risk analysis.)

## The fix (one line, `patch/AppSchedulerBridge.onstart-sync.patch`)
After the launch `ClientTransaction`'s `addCallback(launchItem)`:
```java
transaction.setLifecycleStateRequest(
        android.app.servertransaction.StartActivityItem.obtain(/* activityOptions */ null));
```
`StartActivityItem.getTargetState() == ON_START`, so the launch transaction runs `onCreate → onStart`
synchronously (one main-thread transaction, AOSP `handleLaunchActivity` order) and `onCreateView` assigns the
fragment's lateinit views before control returns to the Looper. **onResume stays in phase-2** (the OH FOREGROUND
callback), so the AMS `FOREGROUNDING` handshake that G2.14m fixed (resume-at-launch raced AMS `INACTIVE` →
`rc=22`) is unchanged, and the decor is not `addView`-ed before the OH surface is ready.

## Why ON_START, not the full AOSP ON_RESUME
Our launch is deliberately two-phase (G2.14m): phase-1 `ScheduleLaunchAbility` = onCreate (stops at ON_CREATE);
phase-2 `FOREGROUND` = onStart+onResume (posted async by `LifecycleAdapter.dispatchByActivityToken`). Requesting
ON_RESUME at launch would (a) reintroduce the G2.14m AMS `rc=22` race and (b) `addView` the decor before the OH
window/surface is ready (the M-family empty-surface white). ON_START only **inflates** (CPU-side, surface-free),
which is exactly what `onCreateView` needs, with the minimum deviation from the working resume path. Phase-2 then
cycles ON_START → ON_RESUME (onResume only). (Full rationale + AOSP TransactionExecutor path: `design/design-note.md`.)

## Regression risk (`evidence/risk-set.txt`) — risk set = 4 (watch), 0 expected regressions
- **The exact "onCreate-posted callback before RESUMED" set is NOT log-separable.** A heuristic "main-thread app
  activity in the performCreate→RESUMED gap" flags **63/121** lit keys, but it **over-counts** (it also catches
  inline onCreate work, which is unaffected) and **misses the one confirmed case** (fd-breezyweather shows 0 by
  that metric — its posted callback surfaced only via the crash). So 63 is not a trustworthy count.
- **By stack (the behaviourally-relevant cut):** of the 122 lit keys — **0 surface-dependent** (flutter/unity/RN/
  webview-hybrid); **118 jvm** (onStart = surface-free content inflation → benign/beneficial); **4 native-engine**
  (fd-minetest, fd-mpv, fd-organicmaps, fd-stk; SurfaceView/GL) → the **risk set = 4**, to re-verify on board.
  Even these are expected benign: a SurfaceView's surface is created at window-add (onResume), not onStart, so
  onStart-at-launch does not change surface availability.
- **Safety argument:** the fix **restores stock AOSP ordering** (onCreate→onStart synchronous); route-A's async
  deferral is the deviation. Every app here lights on stock Android, so it tolerates synchronous onCreate→onStart;
  only reliance on the route-A-specific async gap (a latent bug) could change behaviour, and none is seen.
- **One protocol point to confirm on board (not a key):** OH maps `onStart ↔ onWindowStageCreate`; onStart now
  precedes OH's `onWindowStageCreate` callback — expected safe (onStart doesn't touch the OH window stage) but a
  board run must confirm.

## Predicted moves
- **fd-breezyweather: 1** (dead → past the lateinit `weatherView`, to its next wall; lit not guaranteed).
- **lit regressions: 0 expected** (0 surface-dependent; 4 native-engine benign-but-watch; 118 jvm benign;
  onResume + AMS handshake untouched; AOSP-order restored).

## This round's rule
Fix the ordering at the layer AOSP fixes it — advance to **ON_START inside the launch transaction** (restoring
the stock onCreate→onStart synchrony) rather than resuming at launch (which reintroduces the AMS `rc=22` race and
the empty-surface risk). Bound the regression risk by **mechanism + stack**, not by a log heuristic that can't
separate posted from inline work: here the behaviourally-relevant risk set is the 4 native-engine lit keys, and
the AOSP-restore argument predicts no lit regressions.

## Files
- `patch/AppSchedulerBridge.onstart-sync.patch` — the one-line `setLifecycleStateRequest(StartActivityItem)` change.
- `design/design-note.md` — defect, AOSP order, route-A two-phase, the fix, ON_START-vs-ON_RESUME, verification plan.
- `evidence/risk-set.txt` — the risk scan: the log-separability limit, the stack cut, the safety argument.
- `recipe/risk_scan.py` — the reproducible lit-key gap scan + stack classification.
- `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline; no deploy; no push; patch not built/run here (t3 prototype — on-board build + the 3-step verification
plan in the design note are the owner's). The "posted-before-RESUMED" set is not log-separable (stated, not
faked); the risk set is mechanism+stack-bounded. Sources read read-only: the runtime JAR source
(`westlake-harness/bms/.../AppSchedulerBridge.java`, `LifecycleAdapter.java`), AOSP android-14
(`westlake-inputs/aosp-14.0.0_r1-src` ActivityThread + servertransaction), the U13 stage-A hilogs + u13-reference
lit list (`westlake-harness-u7-executor`, `westlake-harness`), corpus100 stacks (`westlake-inputs`).
