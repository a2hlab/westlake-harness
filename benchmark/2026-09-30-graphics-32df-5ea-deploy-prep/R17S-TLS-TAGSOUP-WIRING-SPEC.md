# r17s wiring spec: real TLS for okhttp + activate tagsoup-free Html fallback (5ea Wikipedia, route-A, 32df)

**Read-only investigation. No board writes, no build.** Goal: stop the Wikipedia welcome page + feed
from crashing on 5ea (runtime `32dfac83`, JAR r17r `dd4f0eae`). Two independent fixes:
**A** = make okhttp use the real `WestlakeSSLSocket` chain instead of `TlsShimProvider$ShimSocketFactory`;
**B** = activate the already-shipped tagsoup-free `HtmlCompatFallback`.

> **Headline (differs from the task's hypothesis):** on 5ea r17r the TLS native self-test **passes** and
> `WestlakeTlsInstall` logs *"WestlakeSSLSocketFactory installed as default HTTPS (self-test OK)"* — yet
> okhttp still hits the shim. The factory chain is **complete and installed**; it just **doesn't win the
> JCA provider race** because `SSLContext.TLS` is registered on the boot BC provider **by class name**
> (boot-loader can't load the runtime-JAR SPI → CNFE → JCA falls through to `TlsShimProvider`). The tagsoup
> fallback is complete too; its native `.so` is simply **absent from the 5ea deploy**.

---

## 1. File inventory + completeness verdict

### A. Real-TLS Java chain (source of record: `westlake-harness-walls/bms/src/adapter/framework/activity/java/`)
All files below are byte-identical between the walls tree and the bms r17j evidence copy
(`westlake-harness-bms/benchmark/2026-09-30-v3c-r17j-prospective/evidence/`), and all are present in the
deployed r17r dex (`vm-copies/r17r-dd4f0eae/oh-adapter-runtime.jar`, sha256 `dd4f0eae…`; verified by dex
string scan — see §4). "walls" paths below are the authoritative source.

| File | Verdict |
|---|---|
| `WestlakeSSLSocket.java` | **COMPLETE.** Full `SSLSocket` over the 7 boundary natives (`nativeHandshake/Read/Write/PeerCert/PeerChain/Info/Close`) + `nativeTlsSelfTestOk` (8th). Lazy handshake on first stream/`startHandshake`, fd resolved via reflection, fail-closed `selfTestPassed()`. |
| `WestlakeSSLSocketFactory.java` | **COMPLETE.** All 5 `SSLSocketFactory.createSocket` overloads **including the layering `createSocket(Socket,host,port,autoClose)`** (line 41) that okhttp's `connectTlsEtc` calls; each returns a `WestlakeSSLSocket`. Cipher lists present. |
| `WestlakeSSLContextSpi.java` | **COMPLETE (client-only).** `engineGetSocketFactory()` returns `new WestlakeSSLSocketFactory()` (line 34); `engineInit` no-op (native owns trust); server/`SSLEngine` throw. |
| `WestlakeSSLSession.java` | **COMPLETE.** Read-only session over the handle; cipher/protocol from `nativeInfo`; peer certs via `OhPeerCertificates`. |
| `WestlakeTlsInstall.java` | **PRESENT but has the A-bug.** Restores BC JCA regs, publishes `AndroidOpenSSL`, calls `OhTrustBridge.install()`, then `installSocketFactoryIfSelfTestPasses()`. **`SSLContext.TLS` is registered with naive `bc.put(type,className)` (lines 141‑144), NOT the `putDirectService` direct-newInstance form used for SecureRandom/TrustManagerFactory (lines 88‑99/101‑118).** This is the A-gap (§2). |
| `OhTrustBridge.java` | **COMPLETE.** Restores RSA/EC signatures, EC KeyFactory, `TrustManagerFactory.OH-PKIX/PKIX/X509`, `SecureRandom.WestlakeKernel`; sets `ssl.TrustManagerFactory.algorithm=OH-PKIX`. Does **not** register any `SSLContext`. |
| `WestlakeAndroidOpenSsl.java` | **COMPLETE.** BC-low-level-backed `AndroidOpenSSL` provider (satisfies BC `AndroidDigestFactory` assertion). No `SSLContext`. |
| `OpenSSLProvider.java` (`com.android.org.conscrypt`) | **COMPLETE.** Resolvable Conscrypt-name shim extending `WestlakeAndroidOpenSsl`. No `SSLContext`. |
| `B7BindFixes.java` | **COMPLETE for wiring.** `apply()` reflectively calls `WestlakeTlsInstall.install`; `loadWestlakeNativeLibs()` (line 150) builds the runtime-CL native namespace (line 155/193, search+permit `/system/android/lib64:/system/lib64/platformsdk:/system/lib64/chipset-sdk:…`), loads gapfill → `liboh_tls_boundary.so` (line 162) → sets `WESTLAKE_HTML_COMPAT`+`_CLASS` (lines 167‑168) → loads `libwestlake_html_compat.so` (line 173). Loads are catch-and-log. |

Native dependency:
- `liboh_tls_boundary.so` **on the 5ea board = `39c2cfe9`** (BOARD-HANDOFF; sha `39c2cfe9cb830f08`, identical to `vm-copies/tls-boundary-39c2cfe9/` and the 32df 5ea payload). It **registers `WestlakeSSLSocket` natives AND `nativeTlsSelfTestOk`** (string scan: `nativeTlsSelfTestOk`, `WL_TLS_self_test` present — unlike `8ecf6250`, which lacks it). Loaded OK on r17r (`[B8-NATIVE] loaded …liboh_tls_boundary.so`).
- **Self-test is OFFLINE**: `WL_TLS_self_test` only dlopens board OpenSSL (`/system/lib64/{platformsdk,chipset-sdk,chipset-sdk-sp}/lib{ssl,crypto}_openssl.z.so`), checks `/etc/ssl/certs/cacert.pem` present + `SSL_new`/`X509_STORE` fn-table live. **No network.** It **passes on 5ea** (log: `WestlakeSSLSocketFactory installed as default HTTPS (self-test OK)`).

### B. tagsoup-free Html fallback
| File / artifact | Verdict |
|---|---|
| `HtmlCompatFallback.java` (walls; identical in bms r17j) | **COMPLETE and tagsoup-free.** Hand-rolled parser (b/strong→bold, i/em→italic, br/block→newline, entities decoded, other tags stripped). **Zero references to `org.ccil.cowan.tagsoup`** (grep-confirmed). Publishes both overloads: 4-arg `Spanned fromHtmlCompat(String,int,ImageGetter,TagHandler)` and 2-arg `String fromHtmlCompat(String,int)`. |
| `libwestlake_html_compat.so` (`26ac847b`, 18552 B) | **COMPLETE but NOT DEPLOYED on 5ea.** Registers native `html_from_html_native` with descriptor `(Ljava/lang/String;ILandroid/text/Html$ImageGetter;Landroid/text/Html$TagHandler;)Landroid/text/Spanned;` (the **4-arg Spanned** overload) and ArtMethod-patches `Html.fromHtml`; reads `WESTLAKE_HTML_COMPAT_CLASS`. Exists in `westlake-jni-gapfill-c5ed50d5/package-5ea/payload/android/lib64/` and the `westlake-b93-tls-html-{8ecf6250,9c0f8d38}-26ac847b/2-html/` payloads — but **NOT** in the 5ea 32df runtime payload nor the board's `39c2cfe9` TLS package. |

### Boot-image opponent (not in the JAR — `com.android.internal.os`, boot classpath)
`TlsShimProvider` + `$ShimSocketFactory/$TlsContextSpi/$TrustFactorySpi/$KeyFactorySpi` — smali under
`01.OH61AOSP16/real-work/.state/zigzag-*/smali/com/android/internal/os/`. `$ShimSocketFactory.fail()`
throws `UnsupportedOperationException: TLS shim: no real networking …` (`…$ShimSocketFactory.smali:27‑37`).
Registered by `AppSpawnXInit` (see §2).

---

## 2. A-gap — why okhttp hits the shim, and what makes Westlake win

### How the shim is registered
`com.android.internal.os.AppSpawnXInit` publishes it with **`Security.addProvider(new TlsShimProvider())`**
(`AppSpawnXInit.smali:770‑774`, and a second site `:5858‑5862`) — **append**, i.e. *lowest* priority, not
`insertProviderAt(…,1)`. `TlsShimProvider.<init>` puts `SSLContext.TLS = …$TlsContextSpi` plus aliases
`TLSv1/1.1/1.2/1.3/Default` (`TlsShimProvider.smali:32‑68`). It wins **only because it is the sole provider
offering `SSLContext.TLS`** (route-A has no Conscrypt).

### What r17r actually does at bind (5ea board evidence, `…/runs/r17r-32df-main-20260930T071015/…/wikipedia/hilog.txt`)
```
[B8-NATIVE] native namespace created for runtime CL (search=/system/android/lib64:/system/lib64/platformsdk:…)
[B8-NATIVE] loaded /system/android/lib64/liboh_tls_boundary.so
[B8-TLS]    Westlake HTTPS/TLS Java chain installed via BC
[B8-TLS]    WestlakeSSLSocketFactory installed as default HTTPS (self-test OK)   <-- self-test PASSED, factory INSTALLED
...
TlsShimProvider$ShimSocketFactory.createSocket(...)                              <-- okhttp STILL uses the shim
NoSuchMethodError: ... setProperty ... org.ccil.cowan.tagsoup.Parser  (x4)       <-- feed error card -> tagsoup -> exit(1)
```

### The precise gap
`WestlakeTlsInstall.installSocketFactoryIfSelfTestPasses` (walls `WestlakeTlsInstall.java:128‑153`) registers
the winning knob for okhttp as:
```java
bc.put("SSLContext.TLS", "adapter.compat.WestlakeSSLContextSpi");   // lines 141-144 (+TLSv1.2/1.3/Default)
```
BC is a **boot** provider, so when okhttp does `SSLContext.getInstance("TLS")` (OkHttp's default path via
`Platform` → `SSLContext.getInstance("TLS")` → `getSocketFactory()`; it uses **neither**
`HttpsURLConnection.getDefault` **nor** `SSLSocketFactory.getDefault`, so lines 146‑148 don't help), JCA
walks providers in order, reaches BC first, and calls `Provider.Service.newInstance` which does
`getImplClass()` = `Class.forName("adapter.compat.WestlakeSSLContextSpi")` **under BC's BootClassLoader** →
the runtime-JAR class is invisible → `ClassNotFoundException` → `NoSuchAlgorithmException` → JCA **falls
through to the next provider with `SSLContext.TLS` = `TlsShimProvider`** → `$ShimSocketFactory` → crash.

This is the **exact defect** the same file already documents and fixes for the other two runtime-JAR-class
services: `fixRuntimeClassServices` (lines 88‑99) registers `SecureRandom.WestlakeKernel` and
`TrustManagerFactory.OH-PKIX/PKIX/X509` via **`putDirectService`** (lines 101‑118) — a `Provider.Service`
whose overridden `newInstance()` does `new …Spi()` directly, avoiding the boot-loader lookup (there it
manifested as `System.exit(1)` for Wikipedia/Auxio/Noice; for `SSLContext.getInstance` it manifests as a
**silent fall-through** to the shim). `installSocketFactoryIfSelfTestPasses` was never converted to that form.

### The fix (A)
In `installSocketFactoryIfSelfTestPasses`, replace the four `bc.put("SSLContext.…", spi)` lines with
direct-newInstance registrations, reusing the existing `putDirectService` helper generalized to `SSLContext`:
```java
Spi ctx = new Spi() { public Object make() { return new adapter.compat.WestlakeSSLContextSpi(); } };
putDirectService(bc, "SSLContext", "TLS",     "adapter.compat.WestlakeSSLContextSpi", ctx);
putDirectService(bc, "SSLContext", "TLSv1.2", "adapter.compat.WestlakeSSLContextSpi", ctx);
putDirectService(bc, "SSLContext", "TLSv1.3", "adapter.compat.WestlakeSSLContextSpi", ctx);
putDirectService(bc, "SSLContext", "Default", "adapter.compat.WestlakeSSLContextSpi", ctx);
bc.put("Alg.Alias.SSLContext.SSL", "TLS");
// keep the existing HttpsURLConnection.setDefaultSSLSocketFactory + Security.setProperty lines (harmless)
```
Because BC precedes the appended `TlsShimProvider`, a *working* BC `SSLContext.TLS` now wins → okhttp gets
`WestlakeSSLContextSpi` → `WestlakeSSLSocketFactory` → `WestlakeSSLSocket` real handshake → feed loads → no
error card → tagsoup never reached.
**Belt-and-suspenders (recommended, order-independent):** additionally
`Security.insertProviderAt(westlakeJsseProvider, 1)` where `westlakeJsseProvider` is a small runtime-JAR
`Provider` subclass registering the same direct `SSLContext.TLS` service — guarantees the win even if the
child provider order ever puts a shim ahead of BC.

---

## 3. B-gap — why the Html fallback is inactive on r17r

Board evidence (same hilog):
```
[B8-NATIVE] WESTLAKE_HTML_COMPAT env set
[B8-NATIVE] System.load(/system/android/lib64/libwestlake_html_compat.so) failed:
            java.lang.UnsatisfiedLinkError: path is outside app domain: /system/android/lib64/libwestlake_html_compat.so
```
`liboh_tls_boundary.so` and `libwestlake_jni_gapfill.so` load fine from the **same directory** through the
**same** runtime-CL namespace, so the namespace is correct. The only variable is the file itself:
**`libwestlake_html_compat.so` is not on the 5ea board.** Proven locally:
- Not in the 5ea 32df runtime payload (`westlake-runtime-graphics-session-sync-32dfac83-5ea/payload/android/lib64/` has only `liboh_tls_boundary.so` + `libwestlake_jni_gapfill.so`).
- Not in the board's active `39c2cfe9` TLS package (`westlake-b93-tls-39c2cfe9-5ea/payload/android/lib64/` — no `libwestlake_html_compat.so`).
- 5ea `package.json` mentions `libwestlake_html_compat` **0** times.

With the load failing, the `Html.fromHtml` → `HtmlCompatFallback` ArtMethod rewrite never happens, so the
feed error card's `LanguageUtil.fromHtml` → `Html.fromHtml` hits the BCP tagsoup **stub** →
`NoSuchMethodError setProperty` → `System.exit(1)` (x4 in the log).

### The fix (B)
**Ship `libwestlake_html_compat.so` (`26ac847b`, 18552 B) to `/system/android/lib64` on 5ea.** No Java/JAR
change is needed — `HtmlCompatFallback` and `B7BindFixes.loadWestlakeNativeLibs` are already correct, the
`WESTLAKE_HTML_COMPAT` envs are already set (lines 167‑168), and the native's registered descriptor (4-arg
`Spanned`) matches `HtmlCompatFallback.fromHtmlCompat(String,int,ImageGetter,TagHandler)`.
Source copy: `westlake-jni-gapfill-c5ed50d5/package-5ea/payload/android/lib64/libwestlake_html_compat.so`
(or either `westlake-b93-tls-html-{8ecf6250,9c0f8d38}-26ac847b/2-html/…`). This is a **native single-file
add** to the generation payload (`/system/android/lib64`), not a JAR-overlay change.

> B alone makes the process **survive** (error card renders, welcome page stays up) even if A is unfixed.
> A makes the feed **load real content** (no error card at all). Do B for a stable welcome page; do A+B for
> a functional Wikipedia. They are independent.

---

## 4. Concrete r17s build recipe for cc-t3

> **Label collision:** cc-t3 already shipped a jar tagged **r17s** = `606dd2e3…` (the fd-meet `restrictions`
> fetcher, `westlake-harness-t3/benchmark/2026-09-30-r17s-verify-61b/`). This TLS+tagsoup jar is a *different*
> change — give it the next free tag (e.g. **r17t**) or rebase onto 606dd2e3; the filename here follows the
> task's requested name. Confirm the tag with cc-t3.

**Change vs r17r (`dd4f0eae`), minimal:**

1. **A — one class edited (runtime JAR):** `adapter.security.WestlakeTlsInstall`
   (`westlake-harness-walls/bms/src/adapter/framework/activity/java/WestlakeTlsInstall.java`).
   - In `installSocketFactoryIfSelfTestPasses` (lines 128‑153): replace the four `bc.put("SSLContext.*", spi)`
     (lines 141‑144) with `putDirectService(bc, "SSLContext", "TLS"/"TLSv1.2"/"TLSv1.3"/"Default", …, ctxSpi)`
     as in §2 (generalize the existing `putDirectService` at lines 101‑118 — it already handles any `type`).
     Keep the `HttpsURLConnection.setDefaultSSLSocketFactory` + `Security.setProperty` lines.
   - Optional robustness: add `adapter.compat.WestlakeJsseProvider extends Provider` (registers the direct
     `SSLContext.TLS` service) and `Security.insertProviderAt(new WestlakeJsseProvider(), 1)` in the same method.
   - No other class changes. Keeps the r17 "changed_existing_classes = 2 BCP smali" invariant (this edit is
     inside an *added* runtime class, not a BCP smali).
   - Rebuild `oh-adapter-runtime.jar` with the TLS classes compiled against `android.jar` as **bootclasspath**
     (the separate pass the r17 README §1 rule mandates — `SSLSocket`/`SSLSession`/`SSLContextSpi` abstract set),
     then deploy as the JAR bind-mount overlay (same mechanism as r17p→r17r layering) on the 5ea board.

2. **B — no class change; one native `.so` deployed:** push
   `libwestlake_html_compat.so` (`26ac847b`, from `westlake-jni-gapfill-c5ed50d5/package-5ea/payload/android/lib64/`)
   to **`/system/android/lib64/libwestlake_html_compat.so`** on 5ea (single-file native add via the generation
   deploy path, e.g. `deploy_generation.sh … --replace /system/android/lib64/libwestlake_html_compat.so`, or
   fold it into the runtime payload's lib64 before deploy). Record src SHA + on-board SHA in the receipt.

**Must be present + loaded on 5ea for the two fixes:**
- `liboh_tls_boundary.so` = `39c2cfe9` (already present + loaded; provides `nativeTlsSelfTestOk` + 7 natives). Keep.
- `/etc/ssl/certs/cacert.pem` present (self-test already passes, so it is) — and its CA set must include
  Wikipedia's roots for the *real* handshake (see unknowns).
- `libwestlake_html_compat.so` = `26ac847b` (the B add).

**Provider-install call site to change:** `adapter.security.WestlakeTlsInstall.installSocketFactoryIfSelfTestPasses`
(`WestlakeTlsInstall.java:128`, puts at `:141‑144`, helper `putDirectService` at `:101‑118`), reached from
`WestlakeTlsInstall.install` (`:65`), reached reflectively from `B7BindFixes.apply` (`B7BindFixes.java:133‑137`).
Native load site (unchanged, already correct): `B7BindFixes.loadWestlakeNativeLibs` (`:150`; tls `:162`, html env
`:167‑168`, html load `:173`). Shim opponent to beat: `AppSpawnXInit.smali:770‑774`/`:5858‑5862`
(`Security.addProvider(new TlsShimProvider())`), `TlsShimProvider.smali:32‑68`.

---

## 5. Unknowns / needs cc-t3 (can't settle from source alone)

1. **A provider order at okhttp time.** I infer BC precedes the appended `TlsShimProvider`, so a *working*
   BC `SSLContext.TLS` wins. Not 100% provable offline. Mitigation: the §2 `insertProviderAt(…,1)` belt makes
   it order-independent. Verify on-board by logging `SSLContext.getInstance("TLS").getProvider()` == BC/Westlake.
2. **Real end-to-end handshake.** The self-test is offline (dlopen + cacert-present + fn-table). It does **not**
   prove a live TLS handshake to `en.wikipedia.org`/`meta.wikimedia.org` succeeds: ANL `liboh_inet_permit`,
   DNS, SNI/`SSL_set1_host`, and chain validation against `/etc/ssl/certs/cacert.pem` must all work. Only a
   board run with A applied confirms the feed actually loads (vs a new handshake/IOException → error card again).
3. **cacert.pem CA coverage on 5ea.** Present (self-test passed) but its trust anchors must include Wikipedia's
   roots (ISRG/DigiCert). If not, the real handshake fails cert verification → IOException → error card.
4. **"path is outside app domain" wording (B).** Strong evidence says it's pure file-absence (tls+gapfill load
   from the identical path). Small residual risk that OH's native loader also needs a namespace-permit tweak for
   this soname even when present — confirm by shipping the `.so` and re-running; if it still errors, it's a
   `createNativeNamespace` permit issue, not a missing file.
5. **r17s label** — collides with cc-t3's `606dd2e3`; pick the tag (r17t / rebase) with cc-t3.
6. **JAR rebuild toolchain** (android-bootclasspath pass) is cc-t3's; not reproducible on this Mac (no framework
   classpath). Confirm the rebuilt jar keeps `changed_existing_classes` = the r16/r17 two-smali invariant.
