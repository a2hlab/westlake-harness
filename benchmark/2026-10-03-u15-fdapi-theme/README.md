# fd-api AppCompat-theme fix: alias activity must inherit the target's theme (U15 runtime-JAR patch for cc-t3)

#90, offline, no board. The fd-api (`com.termux.api`) first-fatal is `IllegalStateException: You need to use a
Theme.AppCompat theme (or descendant)` at `AppCompatDelegateImpl.createSubDecor`. This produces the U15 runtime-JAR
patch (independent class + one needle, cc-t3 JAR style) + tests; **cc-t3 owns the single U15 JAR version and merges it**.
Patch files in `recipe/`; static confirmation in `evidence/static-confirmation.txt`; tests in `test/test-plan.md`.

## Static confirmation — which context, and where the theme is set
- **AppCompat reads the Activity's ContextThemeWrapper.** `createSubDecor` does `mContext.obtainStyledAttributes(
  R.styleable.AppCompatTheme)` and throws if `AppCompatTheme_windowActionBar` is absent; `mContext` is the Activity, whose
  base theme = `r.activityInfo.getThemeResource()` (ActivityInfo.theme, or applicationInfo.theme when 0). So the theme is
  the **launch ActivityInfo.theme**, not a separate application context.
- **Where it currently comes from (the gap).** `TermuxAPIMainActivity` (AppCompatActivity) is launched via the alias
  `TermuxAPILauncherActivity`, which declares **no** `android:theme`. On AOSP an `<activity-alias>` with no theme
  **inherits the target activity's theme**. On route-A, `AppSchedulerBridge.java:793`
  `if (ai.theme == 0 && appInfo != null) ai.theme = appInfo.theme;` falls the alias back to the **application** theme
  `0x1030237` (`android:Theme.DeviceDefault`, non-AppCompat), and `LaunchActivityAliasProjection` sets `targetActivity`
  but leaves theme "untouched" (line 50). So the aliased AppCompatActivity attaches with DeviceDefault → AppCompat throws.
- **Where `[B8-ALIASTHEME]` currently lands.** The deployed JAR's `[B8-ALIASTHEME]` logs "re-resolved 0x1030237 ->
  0x7f120252" and `[J10-ACTINFO] getActivityInfo` shows 0x7f120252, yet AppCompat still fails — so the resolved target
  theme is **not landing on the ClientRecord `launch.theme`** that drives the Activity's ContextThemeWrapper; it is on a
  different copy / the SLA / the log only. **Leading hypothesis (A):** the Activity's actual theme is the DeviceDefault
  application theme. (Alt **(B):** `launch.theme` is 0x7f120252 but its AppCompat parent is unresolved — less likely;
  the test decides.)
- **Manifest (oracle):** `<application theme=0x1030237>`; `<activity TermuxAPIMainActivity android:theme=0x7f120252>`;
  `<activity-alias TermuxAPILauncherActivity targetActivity=TermuxAPIMainActivity>` (no theme). So the target's AppCompat
  theme is `0x7f120252`.

## The patch (cc-t3 JAR style: independent class + one needle)
1. **`recipe/AliasTargetThemeFix.java`** (new independent class) — `apply(ActivityInfo launch)`: if `launch` is an alias
   (has `targetActivity`), read the **target** activity's `android:theme` from the installed APK's binary manifest and set
   `launch.theme = targetTheme` (AOSP alias-inherits-target). No-op for non-aliases; never fatal.
2. **`recipe/BinaryAndroidManifestOrientation.readActivityTheme.java`** — a `readActivityTheme(apk, pkg, activityName)`
   method to add to the existing binary-manifest reader, mirroring `readAliasTarget`/`parseAliasTarget` but returning the
   `<activity name=X>` element's `android:theme` reference value (a `refAttribute` helper reads the TYPE_REFERENCE data).
3. **`recipe/needle-LaunchActivityAliasProjection.diff`** — one line in `LaunchActivityAliasProjection.apply(...)` right
   after `launch.targetActivity = target;`: `AliasTargetThemeFix.apply(launch);`.

Net effect: the alias launch ActivityInfo (which becomes `r.activityInfo`) carries the target's AppCompat theme
`0x7f120252`, so the Activity's ContextThemeWrapper is AppCompat → `createSubDecor` passes.

### cc-t3 patch location (to merge into the single U15 runtime JAR)
- add class `adapter.activity.AliasTargetThemeFix` (from `recipe/AliasTargetThemeFix.java`);
- add `BinaryAndroidManifestOrientation.readActivityTheme` + `refAttribute` (from the sketch, slot into the real reader);
- needle in `adapter.activity.LaunchActivityAliasProjection.apply(ActivityInfo, int)` after `launch.targetActivity = target;`.
- **Ordering:** ensure `AliasTargetThemeFix.apply` (or wherever the target theme is written) runs **after** the generic
  `ai.theme` resolution (`AppSchedulerBridge:793` appInfo fallback / `:1279` appTheme) so it is not re-clobbered to the
  application theme. If the deployed JAR already re-resolves the target theme for `[B8-ALIASTHEME]`, the real fix is to
  make that write `launch.theme` (the ClientRecord ActivityInfo), not just the SLA/log copy.

## Tests (`test/test-plan.md`)
- **T1 unit (pure Java, decisive for A):** `readActivityTheme(termux-api.apk, com.termux.api, …TermuxAPIMainActivity)` ==
  `0x7f120252` (oracle confirmed from the manifest); `AliasTargetThemeFix.apply` sets an alias `launch.theme` from
  `0x1030237` → `0x7f120252`; non-alias is a no-op.
- **T2 AppCompat createSubDecor (boundary):** reproducing `obtainStyledAttributes(AppCompatTheme)` needs the app's
  resources via a native AssetManager (libandroidfw/libandroid_runtime), which **host x86 ART lacks** (same boundary as
  the Bitmap / mindustry host tests). If cc-t3's harness has a host AssetManager: `addAssetPath(apk)` → `Theme.applyStyle(
  0x7f120252)` → `obtainStyledAttributes(appcompat AppCompatTheme)` → assert `hasValue(windowActionBar)`. This also
  decides A vs B.
- **T3 on-board confirm (deploy owner):** deploy the U15 JAR, launch fd-api on 5ea; criterion: no AppCompat-theme
  `IllegalStateException`; fd-api moves past this wall.

## Prediction (first-fatal)
With the alias carrying the target's AppCompat theme, `createSubDecor` passes → fd-api's first-fatal **moves past** the
AppCompat-theme wall. Next wall unknown; the background `LocalSocketImpl.bindLocal` ULE is non-fatal (termux-api ↔ termux
local socket — degraded, not fatal). Lit likelihood after the fix: medium (simple AppCompat UI once the theme resolves).

## This round's rule
For an aliased AppCompatActivity, fix the theme at the layer AppCompat actually reads — the Activity's ActivityInfo.theme
(ContextThemeWrapper), not a logged/SLA copy. AOSP aliases inherit the target's theme; route-A's app-theme fallback breaks
that for alias launches, so set `launch.theme` from the target's `android:theme` before attach.

## Files
- `recipe/AliasTargetThemeFix.java`, `recipe/BinaryAndroidManifestOrientation.readActivityTheme.java`,
  `recipe/needle-LaunchActivityAliasProjection.diff` — the patch (class + reader + needle).
- `evidence/static-confirmation.txt` — which context AppCompat reads, the current theme flow, hypotheses A/B.
- `test/test-plan.md` — T1 unit (decisive), T2 AppCompat boundary, T3 on-board.
- `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline; no board; no push. The patch is for **cc-t3** to merge into the single U15 runtime JAR and build; I provide source
+ tests, not a built JAR. T2 (full AppCompat check) is native-bound on host ART; T1 + the on-board T3 cover it. Sources
read read-only: the U13 hilog (`westlake-harness-u7-executor`), the termux-api apk (`westlake-inputs/apks/fdroid100`), the
adapter activity-JAR source (`westlake-harness/bms/src/adapter/framework/activity/java`).
