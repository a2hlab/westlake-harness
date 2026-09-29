# r17: TLS Java chain, in-app service/uid/receiver repairs, and the anki launcher-selection fix

**Date:** 2026-09-30 · **Lane:** cc-t3 (5cd) · **Runtime JAR:** `oh-adapter-runtime.jar` sha256 `8f4774e16cf798ae…` (baseline `b5` = `250958dc`, build tag `r17`, `benchmark/2026-09-29-bms-link-entry-walls/build-result-r17.json`). JAR copy: `vm-copies/r17-runtime-jar/`.

r17 is r16 (`6a5d7fca`) plus six evidence-backed repairs. Five are in the runtime JAR (my lane + verified teammate fixes); one is in the BMS installer (the anki desktop-icon root cause). Every JAR change keeps `changed_existing_classes` at the same two smali files as r16 (`AppSchedulerBridge`, `PackageManagerProjectionProxy`) — nothing else in the sealed generation is touched.

## What was wrong, and the rule each fix sets

### 1. HTTPS/TLS was absent from route-A v3a (#93, my lane)
Westlake ships **no Conscrypt and no libjavacrypto.so**; Java HTTPS runs on a self-built chain: the board's OpenSSL 3.x behind a JNI boundary, plus JCA registrations restored onto the trimmed Bouncy Castle. v3a carries **none** of it (cx-t0 copylist: zero `OhTrustBridge`/`WestlakeSSL`/`WestlakeSecureRandom` in any payload jar). On Westlake this is installed inline in `AppSpawnXInit`'s child security block; the parent process must never call `Security.getProviders()` first (it pins a permanent JCA `AssertionError` on the class — `AppSpawnXInit` L296-303).

- **Verbatim** from `vm-copies/westlake-current/framework/appspawn-x/java/`: `adapter.security.{OhTrustBridge, OhTrustManagerFactorySpi, OhSystemTrustManager, OhPeerCertificates}` + `adapter.compat.WestlakeSecureRandomSpi` (sha-matched to source).
- **Rewritten to the 7 JNI signatures** (`AndroidRuntime.cpp` L3285 `wl_register_tls_natives`): `adapter.compat.WestlakeSSLSocket` declares `nativeHandshake (ILjava/lang/String;I)J`, `nativeRead/Write (JI[BIII)I`, `nativePeerCert/PeerChain (J)[B`, `nativeInfo (JI)Ljava/lang/String;`, `nativeClose (J)V` — exact names + descriptors so cx-t0's native `RegisterNatives` binds instead of printing "NOT FOUND — TLS off"; plus a functional `SSLSocket`/`SSLSession` wrapper over the handle.
- **New** `adapter.security.WestlakeTlsInstall` replicates the child security prerequisites (BC `MessageDigest` MD5/SHA-*, AES, `CertificateFactory.X.509`) then calls `OhTrustBridge.install()`, all idempotent `provider.put` overwrites, once per process. Invoked reflectively from `B7BindFixes.apply` at bind — in the forked child, clear of the parent clinit trap.

**Rule:** compile the TLS classes against `android.jar` as *bootclasspath* (separate build pass), not `--release 8`, or the JDK's `SSLSocket`/`SSLSession` abstract set mismatches the platform and the class fails to load. The Java side is useful on its own (restores `TrustManagerFactory.PKIX`, `Signature.SHA256withRSA`, `SecureRandom`) even before the native `.so` lands. `WestlakeSSLSocketFactory` (JSSE wiring) has no source in the tree — WestlakeSSLSocket is dormant until a factory routes to it. Honest limit.

### 2. Proxy exceptions were double-wrapped, defeating the receiver guard (cc-wiki)
r16 already contained cc-wiki's `OnlineConnectivityManager.installReceiverGuard` (verified in the `6a5d7fca` dex), but termux/keepass still died on `nativeSubscribeCommonEvent` `UnsatisfiedLinkError`. Root cause was in **my** `ActivityManagerBindProxy`: `return method.invoke(delegate, args)` let the delegate's checked `InvocationTargetException` propagate, and the Proxy runtime re-wrapped it into `UndeclaredThrowableException` — so the receiver guard stacked outside us (`catch(ITE){cause instanceof ULE}`) never saw the `ULE`.

**Fix / rule:** an `InvocationHandler` that delegates must be exception-transparent — `catch (InvocationTargetException e) throw e.getCause()`. The `ULE` (an `Error`) then crosses unwrapped and the guard answers `registerReceiver` as a no-op.

### 3. In-process Services crashed on `startForeground` (fd-droidify)
The in-app `bindService` bridge (r15) let fd-droidify's `SyncService` actually run; `Service.startForeground` → `IActivityManager.setServiceForeground` on the `null` we passed as `Service.attach`'s 6th arg (`mActivityManager`).

**Fix / rule:** never hand a running in-process Service a null activity manager. `attachService` now passes a non-null `IActivityManager` proxy that no-ops the service-lifecycle callbacks (`setServiceForeground`, `serviceDoneExecuting`, `stopServiceToken`, …) with type-correct harmless defaults and delegates everything else to the real adapter.

### 4. Empty own-uid package list emptied the storage volumes (amaze, cc-wiki `SelfUidPackages`)
route-A's package projection returns nothing for `getPackagesForUid(myUid)`, so `StorageManager.getVolumeList` logged "Missing package names" and returned an empty `StorageVolume[]` without asking the (installed) child-local mount binder; amaze's `AppConfig` `<clinit>` then indexed `[0]` of the empty array. Verbatim `adapter.activity.SelfUidPackages` (own-uid `getPackagesForUid`/`getNameForUid` fallback), installed from `B7BindFixes.apply`. cc-wiki verified on 5ea: "Missing package names" 1→0, `getVolumeList count=1`.

### 5. The anki desktop icon launched LeakCanary (#anki, BMS installer)
**Ground truth:** anki's BMS bundle set `entry.mainAbility = leakcanary.internal.activity.LeakLauncherActivity`; sceneboard rendered exactly one anki icon (`AppIconCommonView_com.ichi2.anki.leakcanary…LeakLauncherActivity`, label "Leaks"), so tapping it opened LeakCanary. AnkiDroid merges LeakCanary, which contributes a second `MAIN`+`LAUNCHER` activity. The installer (`oh_adapter_install_apk_c_entry.cpp`) took the first launcher for the plan and marked **every** launcher `isMainAbility`, so `base_bundle_installer` (mainAbility ← last `isMainAbility`) registered the diagnostic UI as the icon. bms_batch cannot fix this — there is only the one (wrong) icon.

**Fix / rule:** `launcher_activity.h` gains `SelectLauncherActivity(manifest)` — **prefer a launcher declared in the app's own package namespace**, falling back to the first launcher of any package (single-launcher apps and foreign-package-launcher apps unchanged). Used in both installer selection sites (plan `launcherActivity` and the abilities `isMainAbility` flag) so exactly one activity is the desktop mainAbility. Host test `test_select_launcher.cpp`: own-package launcher chosen over a leakcanary-first *and* leakcanary-last manifest; foreign-only falls back; no-launcher → nullptr — **ALL PASS**. Needs the installer `.so` rebuild + reinstall to prove on-board (cx-t0's install build).

## Evidence
- `build-result-r17.json` — baseline/output sha, added classes (10 TLS + `SelfUidPackages` + inner classes), changed = the same 2 as r16.
- anki ground truth: `benchmark/2026-09-29-westlake-port/runs/r15cfull-20260929T183604/5cd…/anki/{bundle.txt,icons--1-*.json,record.json}` (mainAbility, single "Leaks" icon, 34 registered abilities incl. the real `IntroductionActivity`/`DeckPicker`).
- fd-droidify: `benchmark/2026-09-30-r16-sweep/runs/r16full-A-5cd/5cd…/fd-droidify/hilog.txt` (setServiceForeground on null).

## Not in r17
CommonEvent JNI (native, cx-t0), provider read/writePermission projection (BCP PackageManagerAdapter), coroutines CNFE / JobScheduler-stub / battery-service / appClassName (oc-t4 r17-java-copylist, next wave) — tracked separately.
