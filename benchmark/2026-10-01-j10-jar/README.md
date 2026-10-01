# J10 runtime JAR — repair the two J9 no-ops (activation-logged, offline gate)

**Lane:** cc-t3 · **Date:** 2026-10-01 · baseline **J9 `87fd463d`** → **J10 `ea24291a`** (deterministic,
built twice). Source: feat/bms-walls `96528a021`. Staged jar:
`westlake-generation-j10-staging/oh-adapter-runtime-j10.jar`.

The U8 uhabits/noice regression analysis found both of J9's new fixes were no-ops at runtime. J10
repairs them and gives each a one-line **activation log** the activation smoke gate reads.

## Fix 1 — AppCompatNoTitleFix install timing → `[J10-NOTITLE] installed`
J9 called `install()` from `B7BindFixes.apply`, before the app's Application existed, so
`ActivityThread.currentApplication()` was null → `[J9-NOTITLE] no current Application; not installed`,
the `ActivityLifecycleCallbacks` never registered, `Theme_NoTitleBar` never overlaid. J10 adds an
idempotent `install(Application)` and registers it from
`AppSchedulerBridge.nativeOnScheduleLaunchAbility` right after `ActivityThread.currentApplication()` —
the app is live there, still before the first activity's `onActivityPreCreated` (app acquisition
precedes `performLaunchActivity`). Prints `[J10-NOTITLE] installed` on the registration that takes
effect. Benefits the appcompat-actionbar cluster (deadhash/knot/diaspora/memory/yahtzeedicer/
advancedpassgen/itsdicey/textpad).

## Fix 2 — SelfActivityInfoSynthesis reflection target → `[J10-ACTINFO] synthesized`
J9 reflected `adapter.activity.ManifestComponentProjection.projection(String)`, which does not exist
(`projection` lives in `SelfComponentFallback`) → `NoSuchMethodException` every call → synth no-op. J10
`synthFromManifest` calls `SelfComponentFallback.projectionFor(String)` + `boundInfo()` +
`ManifestComponentProjection.component(...)` directly (compile-checked, same package, cannot silently
break again). Prints `[J10-ACTINFO] synthesized` on success. Benefits getActivityInfo-self-null
(dicewarepasswordgenerator/photophase/timerdroid/woefe-shoppinglist).

## Proof it is called (offline)
`test_j10.py` (11/11 PASS, self-contained — reads the committed `smali-evidence/`, no build tools) asserts
on the J10 jar's baksmali:
- the new targets exist (`SelfComponentFallback.projectionFor/boundInfo`, `ManifestComponentProjection.component`)
  and the dead J9 target (`ManifestComponentProjection.projection(String)`) is absent;
- `SelfActivityInfoSynthesis` now invokes `projectionFor`/`component`, no longer `projection`;
- `AppSchedulerBridge` invokes `AppCompatNoTitleFix.install(Application)` right after `currentApplication()`;
- both activation markers are present.
The live invocation of `maybe()`/`install()` was already proven by the J9 U8 hilogs
(`[J9-ACTINFO]`/`[J9-NOTITLE]` appeared); this gate proves J10 reaches the correct targets.

## Not in J10
BOOT-layer libphonenumber (clipboardeditor) stays for **T7f** (`westlake-generation-t7f-inputs/libphonenumber/`).

## Files
`build-receipt-j10.json` (shas, determinism, class delta), `results.json`, `test_j10.py`, `smali-evidence/`.
On-board verification uses `activation_smoke.py` / `board_run.py` per the new process (not done here).
