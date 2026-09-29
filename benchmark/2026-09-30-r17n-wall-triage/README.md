# r17n wall triage — v3c+r17j 5ea sweep (2026-09-30)

**One line:** The two directed r17n items — Wikipedia's EGL last wall (#1) and the tusky/newpipe
conscrypt "Sun provider not found" (①) — are **both proven boot/native, not fixable in
`oh-adapter-runtime.jar`**. This package is the evidence + precise routing to cx-t0, plus a
first-fatal-Java-wall taxonomy of the 25 completed apps in the v3c+r17j sweep.

## What we previously got wrong (and the rule this sets)

1. **"The EGL reverse-push loop can be neutered from the runtime JAR by poisoning the delegate's
   `mLastPushedSize` map."** — It cannot, and here is why, so nobody re-tries it:
   the board's `adapter.window.WindowSessionAdapter` (in `oh-adapter-framework.jar`, md5
   `5bfa99ba990a0a5adccb270d1f33d6e3` = live board jar, verified against
   `01.OH61AOSP16/.../device-jars/oh-adapter-framework.jar`) gates the reverse-push on a **size**:

   ```java
   long sizeKey = (((long) width) << 32) | (height & 0xffffffffL);
   Long lastPushed = mLastPushedSize.get(sessionId);          // Map<Integer,Long>, HashMap
   if (lastPushed == null || lastPushed.longValue() != sizeKey) {  // primitive long compare
       window.resized(...); mLastPushedSize.put(sessionId, sizeKey);
   }
   ```

   A pure-reflection "size-gate → once-per-window" is impossible: (a) the compare unboxes with
   `lastPushed.longValue()` so no `.equals`-sentinel is ever consulted; (b) `Long` is `final` so we
   cannot subclass it to force `longValue()`; (c) the delegate `check-cast`s the `get()` result to
   `Long`, so a non-`Long` poison throws `ClassCastException` *inside* `relayout`; (d) `sizeKey` is a
   relayout-internal local computed just before the push, and the push happens inside the delegate
   **before** our `WindowSessionProxy.invoke` post-processing runs — so we can neither read nor
   predict it. Confirmed independently by source (`WindowSessionAdapter.java:848`, see
   `evidence/egl-size-gate-source-line846.txt`) and by cc-wiki's smali read (`.line 839-840`).
   **Rule:** when a reverse-push loop lives inside a boot/framework-jar delegate method and gates on
   a method-local value, the runtime-JAR proxy has no clean lever — route it to the jar/native owner,
   do not ship a fragile field-poison or change `relayout` input semantics.

2. **"r17k's runtime-JAR `com.android.org.conscrypt.OpenSSLProvider` fixes the conscrypt CNF apps."**
   — Only the *app-side* case (`new com.android.org.conscrypt.OpenSSLProvider()` in app code, resolved
   by the app's PathClassLoader, e.g. vlc). The **boot-side** case is a different wall with the same
   class name: JAR signature verification during startup does

   ```
   JarVerifier.beginEntry -> ManifestEntryVerifier.setEntry
     -> ManifestEntryVerifier$SunProviderHolder.<clinit>
       -> sun.security.jca.Providers.getSunProvider(:128)  Class.forName("com.android.org.conscrypt.OpenSSLProvider")
         -> ClassNotFoundException -> RuntimeException(:135) "Sun provider not found"
   ```

   `Providers` is a BCP class, so its `Class.forName` uses `BootClassLoader`, which cannot see the
   runtime JAR. `com.amaze.filemanager.application.AppConfig.<clinit>` (amaze) and newpipe's `main`
   die on the cached `ExceptionInInitializerError`/`NoClassDefFoundError`. Evidence:
   `evidence/conscrypt-getSunProvider-amaze.txt`. **Rule:** conscrypt-by-name failures split into
   app-classloader (runtime-JAR fixable) vs boot `getSunProvider` (boot fixable) — read the stack to
   tell which before assigning an owner.

## Routing (hand to owners)

- **cx-t0 native** — EGL: libhwui single-swap `westlake-b11-egl-a578b949` (colorspace-retry +
  eglGetError), already built, cc-wiki validating on 5ea. Also: anki `librsdroid.so`, unciv
  `libgdx.so` + `MediaStore.scanFile`, termux-api `LocalSocketImpl.bindLocal`, opencamera
  `AudioProductStrategy`, ooniprobe JNA `libjnidispatch.so`.
- **cx-t0 boot** — conscrypt `getSunProvider`: patch `sun.security.jca.Providers.getSunProvider()`
  (core-oj.jar) to return the BouncyCastle provider instead of `Class.forName`-ing conscrypt, or ship
  `com.android.org.conscrypt.OpenSSLProvider` in a boot jar. Fixes amaze, newpipe, droidify, catima,
  antennapod, and tusky (androidx.startup path). `AppSpawnXInit.overrideJcaProvidersForOH` already
  handles the separate `Providers.<clinit>` provider-list assertion; this lazy JAR-verification path
  is additional.
- **cc-t3 (me), fd-calendar — root-caused and FIXED in source (r17n JAR).** The exact stack (local
  sweep hilog, not a board pull) is `MainActivity` start → `JobScheduler.cancel(int)` on null. The
  jobscheduler *fetcher* was already installed (`[ONLINE-CM] jobscheduler fetcher replaced
  (prev=null)`), yet the service was null 1.2 s later. `prev=null` is the tell: route-A never
  stock-registered "jobscheduler" at all, so `SYSTEM_SERVICE_NAMES` (the Class→name map) lacks
  `JobScheduler.class`. Fossify's typed `getSystemService(JobScheduler::class.java)` resolves the name
  to null and returns null **before** the by-name fetcher is ever consulted. AOSP `registerService`
  writes *both* maps; `OnlineConnectivityManager.replaceFetcher` only wrote `SYSTEM_SERVICE_FETCHERS`.
  Fix: `OnlineConnectivityManager.install()` now also calls
  `registerServiceName("android.app.job.JobScheduler","jobscheduler")` (mirrors Westlake
  `AppSpawnXInit` `nameMap.put(schedulerType,"jobscheduler")`). This is why alarm (consumed by the
  `ALARM_SERVICE` string) worked but jobscheduler (consumed by Class) did not. Build + on-board verify
  pending a free board (5ea busy until ~04:40).
- **cc-t3 (me), fd-etar — held.** `AllInOneActivity.dozeDisabled → PowerManager
  .isIgnoringBatteryOptimizations → mPowerExemptionManager.isAllowListed` NPE: the BCP `PowerManager`
  instance's private `mPowerExemptionManager` is null. Not a fetcher/name gap; needs `PowerManager`
  field injection (a deviceidle binder or a reflective `mPowerExemptionManager` stub). Deferred behind
  the jobscheduler fix.

## Files

- `results.json` — structured taxonomy + verdicts.
- `evidence/conscrypt-getSunProvider-amaze.txt` — amaze boot-side conscrypt stack.
- `evidence/egl-size-gate-source-line846.txt` — the decisive size-gate compare from the board jar's source.
