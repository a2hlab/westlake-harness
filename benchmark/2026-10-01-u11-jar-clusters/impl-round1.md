# U11 JAR clusters — implementation round 1 (cc-t3)

Follows `clusters.{md,csv}`. This round: **implemented cluster 3 (ssl-engine)**; the three "investigate-first"
clusters (2/5/6) were investigated and their fix approach **corrected**; clusters 4 and 7 turned out to need one
more targeted investigation each and are **designed, not shipped blind** (shipping a wrong crypto/theme fix
would fail the ≥2 freeze and waste a window).

## Implemented this round

| cluster | key | fix | jar |
|---|---|---|---|
| 1 phone | x | `TelephonyFetcher` (earlier) | U11b |
| **3 ssl-engine** | fd-client | **`WlSSLEngine`** — `createSSLEngine()` returns a non-null stub engine (both overloads, via needle) | **U11b `d75e90c0…`** |

**U11b = U10 + cluster 1 + cluster 3**, one version, deterministic, 195 classes (+9 vs U10), no frozen file
touched. See `../2026-10-01-u11-jar/build-receipt-u11b.json`.

## Investigations (corrected the cluster table)

### Cluster 2 — null-service-notnull (privacybrowser / breezyweather / wifianalyzer): **NOT a gap service**

dexdump of `wifianalyzer` `CountryPreference.<init>` (the crash method): the `getClass()`-on-null is a Kotlin
`checkNotNull` on a method arg / on the result of a Locale-source chain (`Lgv;.g():Lp70; -> Lp70;.d():Locale`),
**not** a `getSystemService` of a gap service. This agrees with the outer's scan ("these 3 request no gap
service"). **Correction:** the cluster-table fix "provide the null service via a fetcher" is **wrong** for these
— the null is not a missing service. Pinning the exact null needs the app's R8 mapping (obfuscated frames:
`MainWebViewActivity.onCreate:1361`, `zt.<init>:77`, `CountryPreference.<init>:101`) or a runtime probe. **Do
not add a fetcher.** Defer until the null source is identified; likely app-config/resource, not JAR-fixable
generically. (All three also carry a `kotlinx.coroutines.CoroutineStart` CNFE deeper in the chain — rule in/out
as a separate common factor when the R8 map is available.)

### Cluster 5 — content-query-null (notepad): **the app's OWN provider, not a system service**

dexdump: notepad queries `content://com.nononsenseapps.notepad.MyContentAuthority/...` (lists/notes/gtasks…) —
its **own** `ContentProvider`. The null `Cursor` means that provider was **not instantiated** on route-A, so
`ContentResolver.query(ownAuthority)` resolves to no provider → null. **Correction:** the fix is **not** "return
an empty Cursor" — it is **install the app's declared `ContentProvider`s at app init** (so `query(ownAuthority)`
reaches a live provider). This is a real generic wall (any app querying its own provider at startup). JAR fix:
ensure `ActivityThread.installContentProviders` runs for the app's manifest providers in our init path
(`AppSpawnXInit` / the bind-application path). Evidence app: notepad. Needs: confirm whether our bind path skips
app `ContentProvider` installation (likely yes) and add it.

### Cluster 6 — pkg-self (yahtzeedicer): **`getInstallSourceInfo(self)`, and double-load is present**

Hilog: the crash is `ApplicationPackageManager.getInstallSourceInfo` → `NameNotFoundException` for the app's own
package (not `getPackageInfo`). **And** two `PackageManagerAdapter` instances are installed as
`ActivityThread.sPackageManager` (`@7af90e0` the "real getInstance singleton", plus `@98becde`) — **double-load
is real** (17 related lines). **Correction:** the immediate wall is `getInstallSourceInfo(self)` → synthesize an
`InstallSourceInfo` for the app's own package in `PackageManagerAdapter` (JAR). The double-load (two adapter
instances) is a **separate** issue — hand the double-install to cx-bms / the n11 lane; it may or may not be the
cause, but the `getInstallSourceInfo` synthesis addresses the wall directly. Evidence app: yahtzeedicer.

## Designed, pending one targeted check (not shipped blind)

### Cluster 4 — keystore-encryptedprefs (moodcairns)

Root chain (hilog): `KeyStoreException: the master key android-keystore://_androidx_security_master_key_ exists
but is unusable` → `AEADBadTagException: mac check in GCM failed`. androidx.security's `MasterKey` runs an
encrypt-then-decrypt self-test on the AES key held by our `SoftwareAndroidKeyStore` (software AndroidKeyStore
provider); the GCM round-trip **fails**, so the key is "unusable". **Design:** the fix is in
`adapter/activity/SoftwareAndroidKeyStore` — its AES key (from `engineGetKey`) must round-trip through the
default `AES/GCM/NoPadding` Cipher. **Pending check before coding:** write a tiny JVM harness that (a) generates
an AES-256 key via our provider's `KeyGenerator("AES","AndroidKeyStore")` with androidx's
`KeyGenParameterSpec` (PURPOSE_ENCRYPT|DECRYPT, GCM, NoPadding, 256), (b) encrypts+decrypts a probe with
`AES/GCM/NoPadding`, (c) sees whether it round-trips. If it fails, the defect is the KeyGenParameterSpec→key
mapping (likely the key isn't a usable 256-bit AES `SecretKeySpec`, or GCM tag/IV handling); fix there. Shipping
without this round-trip confirmed risks a non-fix. Evidence app: moodcairns.

### Cluster 7 — appcompat-theme (fd-api / termux.api)

`AliasTargetTheme` **already** re-resolves the alias target's theme via `ManifestJsonFallback.activityTheme`,
which **already** falls back to the application theme (`activityTheme` returns `t != 0 ? t : appTheme`, and
"activity not found → appTheme beats 0"). So the generic app-theme fallback is **present** and fd-api still
dies "not a Theme.AppCompat theme" → the theme it resolves (target's own or the app theme) is **itself not an
AppCompat descendant**, or `activityTheme` returns 0 for `TermuxAPIMainActivity`. **Pending check:** read
termux:API's manifest JSON (`ManifestJsonFallback` input) for `TermuxAPIMainActivity`'s `android:theme` and the
`<application>` theme, and the fd-api hilog `[B8-ALIASTHEME]` line (did `activityTheme` return 0 or a non-
AppCompat id?). There is **no generic way to force an AppCompat theme** (AppCompat themes are app resources, no
framework id), so the fix must resolve the app's **own** AppCompat theme id — if the manifest has one and we're
not reading it, that's the fix; if the app genuinely declares a non-AppCompat theme, fd-api is app-specific and
not a generic JAR cluster. Do not force a wrong theme id.

## Expected first-wall move (shipped clusters)

| key | U9 | U11b expected | judge |
|---|---|---|---|
| `x` | `getSystemService("phone")` null → cast NPE | phone non-null → cast OK, wall moves | t20 + `[B8-FETCH] phone … allocated` |
| `fd-client` | `createSSLEngine()` null → `getEnabledProtocols` NPE → DI graph unbuilt → accountManager null | createSSLEngine non-null → getEnabledProtocols non-null → **both walls clear from one root fix** → light candidate | t20 + hilog (SSLEngine NPE gone, MainApp creates) |

## Next

- Round 2: cluster 5 (install app ContentProviders), cluster 6 (getInstallSourceInfo synthesis) — both crisp
  after the investigation; merge into the one U11 JAR version.
- Cluster 4: run the GCM round-trip harness, then fix `SoftwareAndroidKeyStore` if confirmed.
- Cluster 7: read termux manifest theme; fix only if the app's own AppCompat theme id is recoverable.
- Cluster 2: needs R8 mapping / runtime probe before any fix (not a fetcher).
