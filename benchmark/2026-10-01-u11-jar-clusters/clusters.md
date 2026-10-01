# U11 JAR cluster table — java-family non-lit keys

Triage of the **13 java-family non-lit U9 keys** the outer scoped (ACK(90) 22:11/22:20), reading each key's U9
fatal stack from the signed run (`run_index.py query --key K --runtime a8cb9a5a45a6 --where run~approved-j10g`),
classifying the failing platform API as **JAR / native / boot / app**, and — for the JAR-layer ones — a generic
fix + the already-verified source (rg'd in the adapter tree). Clustered by fix; each cluster carries its
evidence-app count (freeze needs ≥2). The phone cluster (cc-t3, already built) is cluster 1.

Already-attributed keys are excluded per the dispatch (packlist/fd-tutanota → U10 JAR; fd-meet/toutiao → U10
native; fd-plus → U11 libandroid lock; mindustry → U11 OpenSLES).

## U11 JAR clusters (runtime-jar fixable)

| # | cluster | keys | failing API → value | generic JAR fix | verified source | evidence |
|---|---|---|---|---|---|---|
| 1 | **phone-apex-telephony** | `x` (confirmed), `fd-wifianalyzer` (candidate) | `getSystemService("phone")` → null → not-null cast / country-code getter | **TelephonyFetcher (built)** — replace the phone fetcher with a non-null TelephonyManager + present-but-off ITelephony | `benchmark/2026-10-01-u11-jar/src/TelephonyFetcher.java` | 1 + 1 candidate |
| 2 | **null-service-notnull** | `cv2-...privacybrowser-standard`, `fd-breezyweather`, `fd-wifianalyzer` | `getSystemService(?)` → null → `.getClass()` not-null check (service identity obfuscated by R8) | identify the null service, provide it via the WifiFetcher/TelephonyFetcher fetcher-swap pattern | `adapter/activity/WifiFetcher.java`, `TelephonyFetcher.java` | 3 (service TBD) |
| 3 | **ssl-engine-null** | `fd-client` | `SSLContext.createSSLEngine()` → null → `SSLEngine.getEnabledProtocols()` NPE (MainApp). 2nd wall: `accountManager` null | `WestlakeSSLContextSpi.engineCreateSSLEngine` must return a non-null SSLEngine | `adapter/activity/WestlakeSSLContextSpi.java` | 1 |
| 4 | **keystore-encryptedprefs** | `cv2-...moodcairns` | androidx.security master key "exists but unusable" → AES-GCM `AEADBadTagException` (AndroidKeyStore unwrap) | `SoftwareAndroidKeyStore` master key must persist so the GCM unwrap succeeds on the same install | `adapter/core/SoftwareAndroidKeyStore.java` | 1 |
| 5 | **content-query-null** | `cv2-...nononsenseapps-notepad` | `ContentResolver.query` → null `Cursor` → `moveToFirst()` NPE | `ContentServiceAdapter` returns an empty Cursor (not null) for the queried provider | `adapter/contentprovider/java/ContentServiceAdapter.java` | 1 (caveat: may be the app's own provider → app issue; need the URI) |
| 6 | **pkg-self-notfound** | `cv2-...yahtzeedicer` | `PackageManager.getPackageInfo(self)` → `NameNotFoundException` (own package) | `PackageManagerAdapter` must synthesize the app's own package for `getPackageInfo` | `adapter/package-manager/java/PackageManagerAdapter.java` + `SelfActivityInfoSynthesis.java` | 1 (u8 tag: n11-double-load overlap — confirm it is not a double-load symptom) |
| 7 | **appcompat-theme** | `fd-api` (com.termux.api) | activity theme not a `Theme.AppCompat` descendant at runtime → `IllegalStateException` | J10d-style: resolve an AppCompat theme for the activity; **extend to the app theme** if activity-theme restore is insufficient | `adapter/activity/J10dTheme` | 1 (J10d already lit other appcompat keys; fd-api needs the extension) |

## Not U11-JAR (hand off)

| cluster | keys | why | owner |
|---|---|---|---|
| **native-soname** | `fd-im-vector-app` (`librealm-jni.so` → `libz.so` NEEDED fails), `cv2-...chessclock-android` ("system library absent from the adapter manifest") | a system `.so` is not resolvable in the app private namespace | cx-bms `native_bridge_policy.v1.json` (2 apps) |
| **boot-bcp** | `cv2-...clipboardeditor` (`com.android.i18n.phonenumbers.PhoneNumberUtil.getInstance()` absent), `fd-musicplayer` (`Bitmap.createBitmap` null ColorSpace) | the defect is in a boot-classpath class method; needs an image rebuild, not the runtime jar | image lane (2 apps) |
| **app-internal** | `mcdonalds` (Dagger `DataSourceModuleProvider.v()` → null) | obfuscated app DI null, downstream of an unknown platform null | needs app decompile to pin a platform API (1 app) |

## Freeze readiness (≥2 evidence apps)

- **Reachable now:** `null-service-notnull` (3 keys) and `phone-apex-telephony` (x + wifianalyzer candidate) —
  but all four getClass()-on-null keys hide the service identity behind R8. **Cheapest disambiguation = the U11
  phone/wifi window itself:** whichever of privacybrowser/breezyweather/wifianalyzer light when `phone`/`wifi`
  go non-null fold into cluster 1; the rest expose a specific other service to add. (Decompiling the four R8
  maps is the fallback.)
- **Single-app (need a 2nd before freezing):** ssl-engine-null, keystore-encryptedprefs, content-query-null,
  pkg-self-notfound, appcompat-theme. Each has exactly one java-family key here; a 2nd evidence app should be
  sought in the full corpus (or via the fix clearing a log-level failure on another key) before the tiered
  freeze.

## What this sets / caveats

- The U11 JAR is one version: clusters 1–7 are the candidate contents; 2–7 are **single-concern new files**
  (like TelephonyFetcher), wired by smali needle, no frozen file touched.
- Three keys (native-soname ×2, boot-bcp ×2, app-internal ×1 = 5 keys) are **not** U11-JAR — routing them here
  would be wrong-layer; they go to cx-bms native / the image lane / app-decompile respectively.
- Clusters 2 (and the wifianalyzer half of 1) are **provisional** until the service identity is confirmed; the
  table marks them `candidate`, not `confirmed`, so a miss there feeds the next scan rather than a false freeze.
