# J10b runtime JAR — activate the NoTitle fix by pre-creating the Application (design 3')

**Lane:** cc-t3 · **Date:** 2026-10-01 · baseline **J10 `ea24291a`** → **J10b `cb392c96`** (deterministic).
Source: feat/bms-walls `6b0d05ee6`. Staged: `westlake-generation-j10b-staging/oh-adapter-runtime-j10b.jar`.

## Why J9/J10 NoTitle never activated
route-A creates the app's Application lazily inside stock `performLaunchActivity` →
`LoadedApk.makeApplicationInner`, so `ActivityThread.currentApplication()` / `mInitialApplication` are
null at `nativeOnScheduleLaunchAbility`. `install()` hit `app == null` and never registered the
callbacks (no `[J10-NOTITLE]` in the knot hilog; `[J10-ACTINFO]` fired fine on the same channel). knot
and dice both die on the action-bar `IllegalStateException` under U8 **and** J10 (no regression).

## The fix (design 3')
New file `J10bAppBootstrap`. Injected at `nativeOnScheduleLaunchAbility` entry: `schedule()` posts to the
main looper, then `bootstrap()`:
`ActivityThread.getPackageInfoNoCheck(SelfComponentFallback.boundInfo()).makeApplicationInner(false,
getInstrumentation())` → sets `mInitialApplication` (if null) → registers the NoTitle callback. The stock
launch then returns the same cached Application and route-A's stock `performLaunchActivity` dispatches
`onActivityPreCreated` to the callback, which overlays `android.R.style.Theme_NoTitleBar` before
`generateLayout`. `makeApplicationInner` does not call `Application.onCreate` (route-A calls it once via
its own path), so pre-creating is transparent.
Activation logs: `[J10b-APP] mInitialApplication set from first Activity <pkg>`, `[J10b-NOTITLE]
installed`, `[J10b-NOTITLE] applied <activity> (pre: windowActionBar=.. windowNoTitle=..)`. If
`makeApplicationInner` is unreachable it logs the reason and no-ops (fall back to design-1).

## Offline gate
`test_j10b.py` 10/10 (self-contained smali-evidence): schedule() injected at the method entry; bootstrap
uses makeApplicationInner/getPackageInfoNoCheck/mInitialApplication/boundInfo + registers the callback;
the three `[J10b-*]` markers present.

## On-board window (waiting for outer-loop board scheduling)
Per the J10 flow: `knowledge/smoke/j10b.json` + `j10b-plan.json` + `j10b-expected-run.json` (jar
`cb392c96`), `after_lock` = sweep_bind_deploy --bind, `before_unlock` = --rollback-only to U8.
**Needs the J10b runtime_fp** (U8 `e953c0921536` with the jar swapped 87fd463d→cb392c96) — outer-loop
offline compute (as J10's `01e1ccf7bd8f`) or read from the board during the install window.
