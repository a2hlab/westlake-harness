# Experiment — extended-capture window to settle slow-vs-stuck for toutiao (DEFAULT DISABLED)

**Status: DEFAULT DISABLED.** Do not run without explicit outer/user approval and an idle board. ≤30 min wall.
This is a *capture-window* change only — **no runtime/host/deploy change**, same U10.1T8 image. It cannot regress
the board; at finish it reverts to U10.1T8 like any window.

## Why
The two toutiao traces we have both end mid-`handleBindApplication`:
- window5 (clean) capture ended at **t+15.5s** (`maps-t5` only, no `maps-t20`) — still in `installContentProviders`,
  never reached `callApplicationOnCreate`.
- stageB (dirty, `batch_interrupted`) reached `ArticleApplication.onCreate` at ~t+15.2s, then a handled SIGSEGV cluster.

So neither trace observed the window-session phase, and **we never captured t20** for toutiao. A single longer CLEAN
capture answers the open questions the two short/dirty traces cannot.

## Procedure (one key, one board, idle)
1. Lock an idle experiment board (5ea34a45 / 5cd1e3dd / 61b06572), only-read check first, whitelist serial only.
2. Launch **toutiao alone** on U10.1T8 (no other key in the shard).
3. Extended capture: `maps` + hilog snapshots at **t5, t20, t30, t60, t90, t120**, and `snapshot_display`
   (screenshot = ground truth) at **t30, t60, t120**.
4. Kill + revert to U10.1T8. Count captures/alive from `facts.txt` (not from plan).

## Pass / fail — decides slow vs a deeper wall
- **PASS-progresses (slow, JIT is the lever):** by t120 the hilog main thread advances PAST
  `installContentProviders` into `callApplicationOnCreate` → `ArticleApplication.onCreate`, AND ideally into
  `handleLaunchActivity` / a window session (`WindowManagerGlobal.addView` / `ViewRootImpl` relayout / a real
  `IWindowSession`), with each t30/t60/t90/t120 snapshot showing a NEW phase vs the previous one (monotonic progress).
  Screenshot need not be lit — monotonic phase progress is the pass signal. → verdict: **pure slow**; the fix is the
  runtime JIT/AOT lever (see README), not a stuck-service fix.
- **FAIL-stuck (a real wall beyond slowness):** at t120 the main thread is STILL in the same `handleBindApplication` /
  `installContentProviders` churn as t20 with no new phase (no `callApplicationOnCreate` progress), OR it is parked on a
  single call with a multi-second silent gap on the Java-main tid (a lock/binder/network stall). → verdict: **waiting**;
  then capture WHAT it parks on (the last Java-main line before the gap) and which stubbed service/call it needs.
- **CRASH:** a `cppcrash`/tombstone/`FATAL EXCEPTION` or an unrecovered SIGSEGV terminates it before t120 → the stageB
  handled-SIGSEGV is a real native wall in onCreate, not benign probing → hand to a native-fault lane (Claude).

## What each outcome buys
- PASS-progresses + a t-to-onCreate/createSession number → confirms a t180/t240 "can it light at all" window is worth it,
  and scopes the JIT/AOT work.
- FAIL-stuck or CRASH → stops us from burning JIT effort on a wall that JIT would not move, and names the exact blocker.

## Cost bound
One key, ≤120s runtime + capture overhead, single board. Well under 30 min including lock/launch/revert.
