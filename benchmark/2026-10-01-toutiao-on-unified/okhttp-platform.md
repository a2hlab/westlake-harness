# Toutiao U10 wall: OkHttp3 "No platform found on Android"

Under U10 (libstdc++ cleared), toutiao's new prominent exception is `NullPointerException("No platform found
on Android")` at `okhttp3.internal.platform.Platform.findAndroidPlatform` (U9: 0 — new, not noise, because U9
died earlier at libstdc++). dexdump of toutiao's bundled (un-obfuscated) okhttp3 + route-A fact check below.

## What findAndroidPlatform requires (toutiao's okhttp, classes16.dex)

```
Platform.findPlatform:  if (isAndroid()) return findAndroidPlatform()   // route-A isAndroid()=true
Platform.findAndroidPlatform:
    p = Android10Platform.buildIfSupported()      // -> null
    if (p == null) p = AndroidPlatform.buildIfSupported()   // -> null
    if (p == null) throw NullPointerException("No platform found on Android")
```

Both `buildIfSupported` require `com.android.org.conscrypt.SSLParametersImpl`:

- **Android10Platform.buildIfSupported** (8a9230): `isAndroid()` ✓ → `getSdkInt()`; `if (SDK < 29) return null`
  (route-A SDK=34 ✓) → `ClassLoaderHelper.findClass("com.android.org.conscrypt.SSLParametersImpl")` →
  `new Android10Platform(cls)`. `catches: 2` — if findClass throws ClassNotFoundException, the method returns
  null. **So even the Android10 path is gated on the conscrypt class** (this is a ByteDance hardening; stock
  okhttp 4.x Android10Platform is gated on SDK≥29 only).
- **AndroidPlatform.buildIfSupported** (8a9764): `isAndroid()` ✓ →
  `findClass("com.android.org.conscrypt.SSLParametersImpl")` (+ `org.apache.harmony...SSLParametersImpl`) → then
  reflects `OptionalMethod` `setUseSessionTickets` / `setHostname` / ALPN on it. findClass throwing → null.

`ClassLoaderHelper.findClass` is ByteDance's `SplitCompatClassLoader` search; for a class absent from every
loader it ends in `ClassNotFoundException`.

## route-A fact check

| condition okhttp checks | route-A actual | pass? |
|---|---|---|
| `isAndroid()` (`java.vm.name == "Dalvik"`) | ART reports `Dalvik` | ✓ (so it takes the Android branch → the NPE path) |
| `Build.VERSION.SDK_INT >= 29` | 34 | ✓ |
| `android.net.ssl.SSLSockets` (Android10 runtime use) | present (FZ-008 BCP stub) | ✓ |
| **`com.android.org.conscrypt.SSLParametersImpl` loadable** | **ABSENT** — 0 hits across the whole route-A payload (framework.jar, oh-adapter-framework.jar, adapter-mainline-stubs.jar, no conscrypt apex/jar). oh-adapter-runtime ships only `com.android.org.conscrypt.OpenSSLProvider` (a shim), not SSLParametersImpl. | **✗ — this is the failing condition** |

So the only unmet condition is the conscrypt class: route-A has **no conscrypt apex** (no
`com.android.org.conscrypt.SSLParametersImpl`), so both `buildIfSupported` return null → NPE.

## Regression controls (lit apps with okhttp) — this is NOT a generic okhttp wall

| app | lit | okhttp Android10Platform | references SSLParametersImpl | why it works / doesn't |
|---|---|---|---|---|
| `fd-droidify` | lit | yes (2) | **0** | stock okhttp 4.x: Android10Platform.isSupported = SDK≥29 only, runtime uses `android.net.ssl.SSLSockets` (route-A has it) → builds, works |
| `newpipe` | lit | yes (1) | **0** | same — stock okhttp 4.x, no conscrypt dependency |
| `fd-tusky` | lit* | no (0) | 1 | older okhttp (AndroidPlatform path) that DOES need SSLParametersImpl; lit only because its login UI renders before any network call — not a clean "okhttp works" control |

**Conclusion:** stock okhttp 4.x (fd-droidify, newpipe) works on route-A without conscrypt. The wall hits okhttp
builds that **require `com.android.org.conscrypt.SSLParametersImpl`** — toutiao's ByteDance-hardened okhttp
(Android10 path gated on it) and older okhttp 3.x (fd-tusky). It is generic to that *class* of apps, but it is
not a "stock okhttp is broken" wall.

## Fix layer — conscrypt/BCP, NOT the U11 runtime JAR

The fix is to make `com.android.org.conscrypt.SSLParametersImpl` resolvable, i.e. provide the **conscrypt apex**
classes route-A is missing. That is a **boot-classpath change**: `com.android.org.conscrypt.*` is a BCP namespace
(the conscrypt apex / adapter-mainline-stubs are BCP), so adding it forces an **ART boot-image rebake** — same
bucket as cluster 6 (oh-adapter-framework) and the boot-bcp cluster (ColorSpace / PhoneNumberUtil), not the
Mac-built oh-adapter-runtime JAR.

A **runtime-JAR stub** of SSLParametersImpl is **not viable**: (1) classloader visibility — the app's
`Class.forName`/`ClassLoaderHelper` resolves `com.android.org.conscrypt.*` against the BCP, not the
DexClassLoader-loaded adapter runtime jar; (2) even if found, okhttp then reflects `setUseSessionTickets` /
`setHostname` / ALPN and uses **real conscrypt SSLSockets** for the handshake — a stub passes the presence check
but breaks at actual TLS (a later wall). A real conscrypt is required for correct TLS.

**Recommendation:** route to the conscrypt/BCP lane (provide the conscrypt apex on the boot classpath). This is
generic (helps every conscrypt-requiring okhttp app, toutiao included) and keeps toutiao an ordinary mainline
key (no toutiao-specific hack). It does **not** go into the U11 JAR. If a stopgap is wanted, it must be a real
conscrypt on the BCP, validated by a TLS handshake, not a presence-only stub. Regression controls for that work:
`fd-droidify` / `newpipe` must stay lit (they must not regress to the conscrypt path), and `fd-tusky`'s network
should start working.
