# Task 78: prospective rerun on v3a + r8b

The previous assumption that historical Westlake lighting transfers to the BMS route is not supported by this run. All 13 requested APKs were reinstalled and launched on 5ea with the unchanged v3a native package and r8b Java overlay. The new rule is to bind predictions to the exact APK hash and distinguish fatal events from caught startup exceptions.

The master batch runner performed its 16 MiB hilog/privacy/clock/display preflight, used `--reinstall --hilog 20 --shots 5,20 --focus-check`, and produced the following facts verbatim. No screenshot passed capture/focus requirements; no lighting result can be signed from this run. AppManager and Droidify survived both samples, which is not a screen verdict.

```text
aegis                shots 0/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
antennapod           shots 0/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
fd-AppManager        shots 0/2  alive t5=yes t20=yes  child_hilog=23662  foreground_unconfirmed
fd-auxio             shots 0/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
fd-com-amaze-filemanager shots 0/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
fd-com-kunzisoft-keepass-libre shots 0/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
fd-droidify          shots 0/2  alive t5=yes t20=yes  child_hilog=30876  foreground_unconfirmed
fd-fitness           shots 0/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
fd-netguard          shots 0/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
fd-noice             shots 0/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
ooniprobe            shots 0/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
termux               shots 0/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
wikipedia            shots 0/2  alive t5=no t20=no  child_hilog=0  foreground_unconfirmed
TOTAL keys=13 screenshots_captured=0/26 alive_t5=2 alive_t20=2
```

## Frozen predictions

`predictions-before.json` was written and posted as PROGRESS(78) before the first launch. Only OONI had a matching APK prediction: physical CSV row 40, `service:jobscheduler`. Twelve requested APKs had no matching row and remain unknown, excluded from the hit denominator. `noice` and `fd-noice` share a package name but have different SHA-256 values; row 39 was not reused. The service prediction was made for v3+r8b and evaluated on v3a+r8b, whose old bridge is recorded as a profile difference.

OONI: the earlier provider failure names `nr2.a(...:10)`. The exact APK bytecode in `ooni-nr2-bytecode.txt` loads the literal `jobscheduler`, calls `Context.getSystemService`, and dereferences its returned object at source line 10. The subsequent uncaught WorkManager-not-initialized error follows that failure. This supports one hit out of one eligible prediction, with only 1/13 prediction coverage; it is not 13-app accuracy.

## First fatal events

The collector retains uncaught main-thread Java failures. Earlier caught `nativeParseManifestJson` failures are not promoted to fatal causes. NetGuard instead has a package-specific missing `__errno` relocation immediately followed by same-PID `System.exit(1)` and appspawn exit code 1. Its native loader line is reported, without inventing a Java exception.

### wikipedia

Prediction: unknown: no pre-run prediction for this APK

```text
09-29 16:40:04.631 18282 18282 I C00f00/AppSpawnXJava: [stderr] [CHILD_CK] J_invokeStaticMain_main_threw: java.lang.RuntimeException: Unable to start activity ComponentInfo{org.wikipedia/org.wikipedia.main.MainActivity}: java.lang.IllegalArgumentException: Attribute not found; ID=2130969834
```

### termux

Prediction: unknown: no pre-run prediction for this APK

```text
09-29 16:40:59.674 19654 19654 I C00f00/AppSpawnXJava: [stderr] [CHILD_CK] J_invokeStaticMain_main_threw: java.lang.RuntimeException: Unable to start activity ComponentInfo{com.termux/com.termux.app.TermuxActivity}: java.lang.RuntimeException: bindService() failed
```

### ooniprobe

Prediction: hit: nr2.a line10 dereferences getSystemService(jobscheduler), per pinned APK bytecode

```text
09-29 16:41:56.729 21105 21105 I C00f00/AppSpawnXJava: [stderr] [CHILD_CK] J_invokeStaticMain_main_threw: java.lang.IllegalStateException: WorkManager is not initialized properly.  You have explicitly disabled WorkManagerInitializer in your manifest, have not manually called WorkManager#initialize at this point, and your Application does not implement Configuration.Provider.
```

### antennapod

Prediction: unknown: no pre-run prediction for this APK

```text
09-29 16:42:46.225 22424 22424 I C00f00/AppSpawnXJava: [stderr] [W-ROOM-SURVIVE] UNCAUGHT in thread 'main' (id=2, main=true): java.lang.NullPointerException: Attempt to invoke interface method 'java.lang.String android.content.SharedPreferences.getString(java.lang.String, java.lang.String)' on a null object reference
```

### aegis

Prediction: unknown: no pre-run prediction for this APK

```text
09-29 16:43:37.497 23757 23757 I C00f00/AppSpawnXJava: [stderr] [CHILD_CK] J_invokeStaticMain_main_threw: android.view.WindowManager$InvalidDisplayException: Unable to add window android.view.ViewRootImpl$W@e22751f -- the specified window type 1 is not valid
```

### fd-AppManager

Prediction: unknown: no pre-run prediction for this APK

```text
Alive at t5 and t20; no uncaught fatal event captured.
```

### fd-auxio

Prediction: unknown: no pre-run prediction for this APK

```text
09-29 16:45:21.596 26461 26461 I C00f00/AppSpawnXJava: [stderr] [CHILD_CK] J_invokeStaticMain_main_threw: java.lang.UnsatisfiedLinkError: No implementation found for long android.view.VelocityTracker.nativeInitialize(int) (tried Java_android_view_VelocityTracker_nativeInitialize and Java_android_view_VelocityTracker_nativeInitialize__I) - is the library loaded, e.g. System.loadLibrary?
```

### fd-com-amaze-filemanager

Prediction: unknown: no pre-run prediction for this APK

```text
09-29 16:46:16.220 27824 27824 I C00f00/AppSpawnXJava: [stderr] [CHILD_CK] J_invokeStaticMain_main_threw: java.lang.NoClassDefFoundError: com.amaze.filemanager.application.AppConfig
```

### fd-com-kunzisoft-keepass-libre

Prediction: unknown: no pre-run prediction for this APK

```text
09-29 16:47:09.547 29169 29169 I C00f00/AppSpawnXJava: [stderr] [W-ROOM-SURVIVE] UNCAUGHT in thread 'main' (id=2, main=true): java.lang.RuntimeException: Cannot create an instance of class com.kunzisoft.keepass.viewmodels.DatabaseViewModel
```

### fd-droidify

Prediction: unknown: no pre-run prediction for this APK

```text
Alive at t5 and t20; no uncaught fatal event captured.
```

### fd-fitness

Prediction: unknown: no pre-run prediction for this APK

```text
09-29 16:48:51.470 31859 31859 I C00f00/AppSpawnXJava: [stderr] [CHILD_CK] J_invokeStaticMain_main_threw: java.lang.RuntimeException: Unable to start activity ComponentInfo{de.tadris.fitness/de.tadris.fitness.ui.MainActivity}: java.lang.IllegalStateException: You need to use a Theme.AppCompat theme (or descendant) with this activity.
```

### fd-netguard

Prediction: unknown: no pre-run prediction for this APK

```text
09-29 16:49:42.320  1252  1252 W C03f07/MUSL-LDSO: relocating failed: symbol not found. dso=/data/app/el1/bundle/public/eu.faircode.netguard/android/lib/arm64-v8a/libnetguard.so s=__errno use_vna_hash=1 van_hash=50d63
```

### fd-noice

Prediction: unknown: no pre-run prediction for this APK

```text
09-29 16:50:31.399  3111  3111 I C00f00/AppSpawnXJava: [stderr] [CHILD_CK] J_invokeStaticMain_main_threw: java.lang.RuntimeException: Unable to start activity ComponentInfo{com.github.ashutoshgngwr.noice/com.github.ashutoshgngwr.noice.activity.MainActivity}: android.view.InflateException: Binary XML file line #26 in com.github.ashutoshgngwr.noice:layout/main_activity: Binary XML file line #26 in com.github.ashutoshgngwr.noice:layout/main_activity: Error inflating class TextView
```

## Evidence and limits

`results.json` binds each excerpt to the raw hilog SHA and path; `evidence/<key>/` includes the original record and both process tables. Raw complete logs remain under the Mac path in `results.json.run`; no screenshots exist to submit. The master `facts.txt` is copied unchanged. `identity-before.txt` and `identity-after.txt` match: boot ID, host, bridge, SQLite runtime, r8b JAR and installer were unchanged.

B8 and B10 lifecycle outputs are retained as `lifecycle-b8.json` and `lifecycle-b10.json`: all six scenarios in each are **Skip**, because their selectors match zero tests in this lane. This is not a passing implementation lifecycle. Task 78 authorizes this evidence-only rerun on 5ea; it does not implement the other lanes' B8/B10 fixes or claim their completion.

R2: record/process counts, exact fatal text and pinned OONI callsite are verified; screen lighting is unverified. No runtime code or APK bytes were changed.
