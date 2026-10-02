# Test plan — fd-api AppCompat theme fix

## Oracle (confirmed statically)
`com.termux.api_1002.apk` manifest (apkanalyzer manifest print):
- `<application android:theme="@ref/0x1030237">` (android:Theme.DeviceDefault — non-AppCompat)
- `<activity android:name="com.termux.api.activities.TermuxAPIMainActivity" android:theme="@ref/0x7f120252">`
- `<activity-alias android:name="com.termux.api.activities.TermuxAPILauncherActivity"
   android:targetActivity="com.termux.api.activities.TermuxAPIMainActivity">` (NO android:theme)
So `readActivityTheme(apk, "com.termux.api", "com.termux.api.activities.TermuxAPIMainActivity")` must return **0x7f120252**.

## T1 — unit (pure Java; runs on host ART or a plain JVM; the real fix mechanism)
1. `BinaryAndroidManifestOrientation.readActivityTheme(termuxApiApk, "com.termux.api",
   "com.termux.api.activities.TermuxAPIMainActivity")` == 0x7f120252.   (reader reads the target activity's theme)
2. Build an ActivityInfo `launch` for the alias: name=TermuxAPILauncherActivity, targetActivity=TermuxAPIMainActivity,
   theme=0x1030237 (the DeviceDefault fallback), applicationInfo{packageName=com.termux.api, sourceDir=apk}.
   Call `AliasTargetThemeFix.apply(launch)`.
   ASSERT `launch.theme == 0x7f120252` (was 0x1030237).   (the fix lands the target theme on the launch ActivityInfo)
3. Negative: for a non-alias launch (targetActivity==null) apply() is a no-op (theme unchanged).
This verifies the fix's mechanism end-to-end at the ActivityInfo level — which is what drives the Activity's
ContextThemeWrapper (what AppCompatDelegate reads). This is the decisive test for HYPOTHESIS A.

## T2 — AppCompat createSubDecor (the full behavioral check) — boundary
AppCompatDelegateImpl.createSubDecor calls `context.obtainStyledAttributes(R.styleable.AppCompatTheme)` and checks
`AppCompatTheme_windowActionBar`. Reproducing it needs the app's resources (AssetManager.addAssetPath on the apk) +
androidx.appcompat's R.styleable + a Theme with 0x7f120252 applied. AssetManager/Resources are backed by native
libandroidfw/libandroid_runtime; on host x86 ART those arm64 board libs are absent (same boundary as the Bitmap and
mindustry host tests). So T2 is **not runnable on host ART**. If a host AssetManager is available in cc-t3's harness,
the check is: addAssetPath(termuxApiApk); Resources.Theme t = res.newTheme(); t.applyStyle(0x7f120252, true);
TypedArray a = t.obtainStyledAttributes(appcompat R.styleable.AppCompatTheme); assert a.hasValue(windowActionBar).
This also decides HYPOTHESIS A vs B: if applyStyle(0x7f120252) DOES expose windowActionBar, then the theme resolves fine
and the wall was purely the ActivityInfo carrying the wrong theme (A, fixed by T1's change); if it does NOT, the theme's
AppCompat parent is unresolved (B — a resources issue, a different fix).

## T3 — on-board confirm (deploy owner / U15 window)
Deploy the U15 JAR (with the fix) and launch fd-api on 5ea; criterion: no `IllegalStateException: You need to use a
Theme.AppCompat theme` at createSubDecor; fd-api moves past this wall (t20 shot per the signer). This is the final proof
(T2's native boundary means the host test is partial).
