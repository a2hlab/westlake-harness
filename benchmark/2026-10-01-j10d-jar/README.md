# J10d — fix the appcompat-actionbar wall by restoring the activity's own manifest theme

**Rule this lays down:** on route-A, when a fix needs an activity to be themed by its *own*
`android:theme` (not the application theme), restore `ActivityInfo.theme` **after** every
AppSchedulerBridge mutation and **before** `scheduleTransaction` — because stock
`performLaunchActivity` reads `activityInfo.getThemeResource()` *at launch*, and that method
falls back to `applicationInfo.theme` the moment `activityInfo.theme == 0`.

## What was wrong before (proven, not assumed)

The appcompat-actionbar cluster (knot/deadhash/diaspora/… — AppCompat apps whose MainActivity
declares a `*.NoActionBar` theme) died with:

```
IllegalStateException: This Activity already has an action bar supplied by the window decor.
  Do not request Window.FEATURE_SUPPORT_ACTION_BAR and set windowActionBar to false ...
```

The J10/J10b/J10c windows walked the cause down to ground truth:

- **J10** proved `[J10-ACTINFO]` fires but `[J10-NOTITLE]` never did → the Application was null at
  `install()` time (route-A creates it lazily in `performLaunchActivity`).
- **J10b** pre-created the Application (design ③') so the NoTitle callback *did* run — and the
  platform `android:windowActionBar` was **already false**, yet the ISE still fired. So the platform
  theme was never the lever.
- **J10c** (diagnostic window on 5ea, 2026-10-01) read the decisive value: `AppCompatDelegateImpl`
  reads the app's **own** androidx `windowActionBar` (`0x7f030350`), and for knot it resolved
  **`true`** — i.e. the activity was themed by the **application** theme `Theme.Knot`
  (`windowActionBar=true`), **not** by its manifest `Theme.Knot.NoActionBar` (`0x7f11019e`,
  `windowActionBar=false`).

**Why the activity got the app theme:** `AppSchedulerBridge.nativeOnScheduleLaunchAbility`
overwrites/zeros `activityInfo.theme` just before `scheduleTransaction` (the force-zero block at
smali ~6307-6322, and the baseline enriched-theme path). `[B47-SLA]` logs the *correct*
`activityInfo.theme=0x7f11019e` earlier — before that overwrite. At launch,
`ActivityInfo.getThemeResource()` (AOSP 14 `ActivityThread.performLaunchActivity:3745` →
`ActivityInfo.getThemeResource:1585`, `theme != 0 ? theme : applicationInfo.theme`) then returns
the app theme.

## The fix (one freeze unit)

`adapter/activity/J10dTheme.restore(ActivityInfo)` — injected right after the `ActivityInfo.banner`
force-zero `iput` (reusing that instruction's object register `v4` = `activityInfo`), before
`scheduleTransaction`. It sets `activityInfo.theme` back to the activity's own manifest theme
(`ManifestJsonFallback.activityTheme(pkg, name)` — the same source
`SelfComponentFallback.correctSelfActivityTheme` uses) and logs:

```
[J10d-THEME] <activity> theme=0x7f11019e (manifest 0x7f11019e; was 0x0)
```

Then `performLaunchActivity.setTheme(0x7f11019e)` uses `Theme.Knot.NoActionBar` →
AppCompat sees its own `windowActionBar=false` → takes the `windowNoTitle` branch → no decor
action bar → no ISE.

## Build & provenance (evidence first, numbers given)

| field | value |
|---|---|
| baseline (J10) | `ea24291a898812ff1f13c11cd15e5747392fb975966a54b7c6e73e0d123517e1` |
| output (J10d) | `57d621837eee4d065a49929f0a7f981e811becc4beba988c18b0ab847e67058c` |
| deterministic | yes — built twice, identical (`smali assemble -j 1`, zip date_time fixed) |
| class delta | **+`adapter/activity/J10dTheme` only** (J10 ACTINFO retained; J10b/c Application pre-creation + overlay NOT carried — the overlay was the wrong lever) |
| source | `feat/bms-walls 1d691f67c` (`J10dTheme.java`, `AppSchedulerBridge.java` inject) |
| staged jar | `$WORKSPACES/westlake-generation-j10d-staging/oh-adapter-runtime-j10d.jar` |

## Offline gate

`python3 test_j10d.py` → **6/6** (self-contained: reads `smali-evidence/`, no jar/build tools,
so it runs unchanged in the land.py master gate). It proves the inject site (right after the
banner force-zero, same `activityInfo` register), that `J10dTheme` reads the manifest theme and
writes `ActivityInfo.theme`, the `[J10d-THEME]` marker, and the AOSP `getThemeResource` fallback
evidence.

## Window (pending outer-loop schedule)

`j10d-plan.json` — 5ea, `--detach`. Smoke reads `[J10d-THEME]` on knot + `[J10-ACTINFO]` on dice +
controls; `offline_precheck.expect` states what a confirm vs refute looks like on-board (per the
retro-18 requirement); `expect_copies {liboh_adapter_bridge.so:2, liboh_android_runtime.so:2}`;
`before_unlock` rolls back to U8 (`runtime_fp e953c0921536`, `boot_fp 4db882a81732`) and reuses the
`after_lock` `--out` overlay dir. `runtime_fp` of the J10d overlay is **not yet known** (jar
`57d62183` differs from every prior) — the outer loop computes/reads it before scheduling.
