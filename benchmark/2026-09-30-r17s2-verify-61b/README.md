# r17s rev2 (3b523289): real TLS for okhttp + RestrictionsManager + dlopen experiment — 61b verify (2026-09-30)

**One line:** a new r17s (`3b523289`, on r17r `dd4f0eae`) wires okhttp onto the real Westlake TLS chain
(cc-wiki's spec A), keeps the fd-meet RestrictionsManager stub, and probes the dlopen_ns app-path
question. On 61b the **TLS wiring works and regresses nothing** (tusky/amaze/etar/markor/antennapod all
lit); cc-wiki independently **accepted A on 5ea**. The dlopen probe **no-ops** (app classloader
unreachable at bind) and the four dlopen apps are unchanged → native, cx-t0.

## The three fixes and their verdicts

### A — real TLS for okhttp (cc-wiki spec, CONFIRMED)
`WestlakeTlsInstall.installSocketFactoryIfSelfTestPasses` used to register `SSLContext.TLS` on the boot
BC provider **by class name** (`bc.put("SSLContext.TLS", "adapter.compat.WestlakeSSLContextSpi")`). BC's
`Provider.Service.newInstance` then does `Class.forName(...)` under BC's **BootClassLoader**, which can't
see the runtime-JAR SPI → `ClassNotFoundException` → JCA falls through to the appended `TlsShimProvider`
(the only other `SSLContext.TLS` on route-A) → okhttp gets `ShimSocketFactory` →
`UnsupportedOperationException` on connect. r17s registers the SPI with a **direct-newInstance
`Provider.Service`** (`putDirectService`, the same fix already used for SecureRandom/TrustManagerFactory),
plus `SSLContext.setDefault(westlakeCtx)`, all inside the fail-closed `selfTestPassed()` gate.

Evidence (61b hilog, every bind):
```
[B8-TLS] SSLContext.TLS/TLSv1.2/TLSv1.3/Default re-registered with direct newInstance
[B8-TLS] SSLContext.TLS -> Westlake (direct newInstance) + setDefault; okhttp beats TlsShimProvider
[B8-TLS] WestlakeSSLSocketFactory installed as default HTTPS (self-test OK)   <-- self-test PASSED on 61b
```
- **No regression:** `fd-tusky` (a TLS-heavy Mastodon client) reaches its **login page** (`fd-tusky/t20.jpeg`);
  amaze/etar/markor/antennapod all stay lit. The provider swap broke nothing.
- **cc-wiki accepted A on 5ea (32df):** same markers; okhttp no longer hits `TlsShimProvider` (its 11
  `ShimSocketFactory` lines were `class_linker` link noise — 0 "no real networking" throws after) and now
  goes `WestlakeSSLSocketFactory → Android10Platform.configureTlsExtensions → ConnectPlan.connectTls →
  real TCP connect`.
- **Real handshake still unverified (open, not a JAR problem):** 61b clean-install apps have no
  credentials/feeds to fetch; 5ea's wikipedia is **DNS-poisoned / GFW-blocked** (TCP connect timeout to a
  fake IPv6 `2001::1:443`) so it never reaches `WestlakeSSLSocket.nativeHandshake`. The **wiring** is
  proven on two boards; the **native handshake** needs a reachable HTTPS endpoint (infra/network).

### B — RestrictionsManager stub (works; fd-meet still not lit)
`[B8-FETCH] restrictions RestrictionsManager built (empty-Bundle service)` — fd-meet advances **past** the
RestrictionsManager NPE, then hits a new `NPE: Collection.iterator() on null` →
`Unable to start activity org.jitsi.meet.MainActivity`. Honest progress, not lit (unchanged from 606dd2e3).

### C — dlopen_ns app-path experiment (NO-OP → reinforces native)
`B7BindFixes.extendAppNativeLibrarySearchPath()` tried to append `/system/lib64:/system/android/lib64` to
the app classloader's `DexPathList` native search path. hilog:
`[B8-DLEXP] app classloader unavailable (ctx=null); skipped` — `Thread.currentThread().getContextClassLoader()`
is **null** at `B7BindFixes.apply()` time in the OH child, so the app CL was never reached. The four
dlopen apps are unchanged (fd-app `libgdx→libstdc++.so`, mindustry `libarc→libOpenSLES.so`, fd-client
`libconscrypt_jni→liblog.so`, fd-im-vector `librealm-jni` UNSUPPORTED-SYMBOL). This **reinforces native
ownership**: the runtime JAR can't even reach the app namespace from the bind hook → **cx-t0**. (A proper
future attempt would fetch the app CL via `LoadedApk`/`ActivityThread` reflection, not `contextClassLoader`.)

> **Rule this sets:** at OH `handleBindApplication → B7BindFixes.apply()`, the thread context classloader
> is **null** (unlike stock AOSP). Any runtime-JAR hook that needs the *app* classloader must resolve it
> explicitly (LoadedApk/ActivityThread), not via `Thread.currentThread().getContextClassLoader()`.

## Regression batch (r17s, `--reinstall`, 11 keys) — facts.txt

```
antennapod   alive t5=yes t20=yes  fd-com-amaze-filemanager  yes/yes  fd-etar yes/yes
fd-tusky     yes/yes (login page)  markor yes/yes
fd-meet no/no (RestrictionsManager built; null-Collection)   fd-app/fd-client/fd-im-vector-app/mindustry no/no (dlopen, native)
wikipedia no/no (GFW-blocked feed)                            TOTAL alive_t5=5 alive_t20=5
```
Every previously-lit control stayed lit → **no regression** from the TLS+dlopen r17s.

## AntennaPod clean-install A/B (same board, single variable)

Same 61b, same boot `58aef9fc` (no reboot), same APK, same `--reinstall`; only variable = the JAR:
| JAR | verdict |
|---|---|
| r17s `3b523289` | **LIT** (child_hilog 32051; no FeedUpdateManager NPE / no FATAL) |
| r17r `dd4f0eae` | **LIT** (child_hilog 32263) |

Both lit → the 5ea r17r clean-install FeedUpdateManager NPE is a **board (5ea × 32df)** difference, not a
JAR regression — reconfirmed on 61b under the new r17s. (`compare_runs.py` predates the fingerprint files;
by-hand single-variable.)

## Boundary / handoffs
- **Real TLS handshake + wikipedia feed** → cc-wiki on 5ea (needs 32df + a reachable network; wikipedia is
  GFW-blocked on the lab net). r17s `3b523289` stays on 5ea as the unified JAR.
- **tagsoup fallback (B)** → NOT in this JAR; `libwestlake_html_compat.so`'s ArtMethod patch SIGSEGVs on
  32df ART (cc-wiki), so it's rolled off the board — stable wikipedia relies on A (real feed) instead.
- **dlopen_ns four apps** → native-loader-oh (cx-t0); the JAR can't reach the app namespace at bind.
- **HW/helloworld** not run (not a key in the default manifest); the five lit controls cover no-regression.

## Files
- `results.json` — per-fix verdicts, batch facts, the antennapod A/B, build/deploy trace.
- `runs/r17s2-61b/.../` — 11-key `--reinstall` batch (t5/t20 + facts.txt + hilog).
- `runs-reinstall/r17r-antennapod-ctrl/.../` — the r17r antennapod control.
- `deploy-receipt{,-r17r}/` — bind-mount deploy/rollback receipts.
