# #81 segment 1: How the Activity theme gets set in Westlake (vs route-A)

Source of truth: `~/a2hlab/westlake-current` (verified implementation, read on VM, 2026-09-29).
All line numbers are first-hand from that tree. route-A = `bms/src/adapter/framework/**` + r8b JAR.

## The chain in Westlake (5 steps)

1. **Native manifest parse** — `framework/package-manager/jni/apk_manifest_parser.cpp`
   - `<application android:theme>` → `outData.appTheme` (**L368**, with a `[THEME-DBG]` attribute-dump block above it from the 2026-06-02 debugging of "theme decodes to 0")
   - `<activity android:theme>` → `currentActivity.theme` (**L467**) — per-activity theme IS parsed

2. **JSON serialization** — `framework/package-manager/jni/apk_manifest_jni.cpp`
   - The per-activity JSON entries (**L134–141**) carry only `name / visible / launchMode / screenOrientation` — the parsed per-activity theme is **not serialized** into the activity entries
   - Only `ai["theme"] = m.appTheme` (**L345**) — i.e. the manifest JSON exposes the APPLICATION theme as `applicationInfo.theme`

3. **Bind-time enrichment** — `framework/activity/java/AppSchedulerBridge.java` `[FIX-AII]`
   - `m.optInt("appTheme") → ai.theme` (**L1574**), plus className/largeHeap/factory etc.

4. **buildActivityInfoFromAbility** — same file (**L988–1075**)
   - `ActivityInfo.theme` first from the OH abilityJson `"theme"` field: numeric string parsed, `$theme:0x…` hex parsed, `@style/Name` **cannot be resolved** (no resource table) → left 0
   - fallback: `if (ai.theme == 0 && appInfo != null) ai.theme = appInfo.theme` (**L1075**)

5. **SLA-side keep/zero switch** — same file (**L1817–1860**, `[B47-SLA]`)
   - **Default: BOTH `activityInfo.theme` and `aiApp.theme` are zeroed** (deliberate: a zero theme = DEFAULT framework theme, whose decor path inflates `screen_toolbar` → `ActionBarContextView`, which this port cannot inflate — "Material Catalog died there")
   - `ASX_KEEP_THEME=1` keeps them, AND defaults activity theme to app theme when activity theme is 0 (**L1843–1844**, "= like stock Android does")
   - The successful Westlake Wikipedia run from #76 used `export ASX_KEEP_THEME=1` (in the staged run.sh)

## Why route-A's Wikipedia dies at `Attribute not found; ID=2130969834`

- route-A's **ScheduleLaunchAbility arrives BEFORE bindApplication enrichment** (observed in #73/#76 logs: `[B47-SLA]` at bind+1ms, `[FIX-AII]` enrichment later)
- abilityJson carries only the OH AbilityInfo.theme (an Android app has no OH theme → 0)
- → `ActivityInfo.theme` is 0 → the activity runs on the DEFAULT framework theme instead of the app's real theme → the app's theme attributes (e.g. `0x7f04032a` = ID 2130969834) are unresolvable → crash/inflate failure

## Confirmation of cc-t3's r13 fix direction (static)

r13's `ManifestJsonFallback.resolveActivityTheme(ai)` (fill `ActivityInfo.theme` in `buildActivityInfoFromAbility` from the APK manifest's per-activity `android:theme`, falling back to the application theme) closes exactly this gap and finally *uses* the per-activity theme that Westlake parses (L467) but does not serialize (jni L134-141). Semantically it matches Westlake's KEEP_THEME + app-theme-fallback behavior (**L1843–1844**).

## Caveat for #80

- Westlake's per-activity theme never reaches ActivityInfo through the manifest JSON (step 2 drops it); r13 reads it directly from the APK — equivalent input, different plumbing. When porting, keep r13's approach; do not try to "fix" Westlake's JSON to carry activity themes.
- `@style/Name` theme strings remain unresolvable without a resource table (Westlake limitation at L1059–1063); r13's numeric resource-ID path is the reliable one.
