# U11 JAR — cluster 1: apex-module service `phone` (+ `telephony_subscription_service`)

Implements the first U11 JAR cluster from the adopted design
(`benchmark/2026-10-01-u11-apex-services/design.md`, landed master 1db50e0c5). New feature in a **new file**
(`TelephonyFetcher.java`); **no frozen file edited**.

## Why (one line, evidence in the design)

route-A ships a **stock** `android.app.SystemServiceRegistry` — the apex `TelephonyFrameworkInitializer`
registration runs (`phone` → `new TelephonyManager(ctx)`, fetcher `SystemServiceRegistry$140`) — but on this OH
build that fetcher resolves to **null** (same null-producer class as `WIFI_SERVICE`, which we already backfill
via `WifiFetcher`). `wifi` was backfilled; **`phone` was the unfilled gap**, so `x`
(`getSystemService("phone") as TelephonyManager`) NPEs. x hilog: `[B8-FETCH] wifi fetcher replaced (prev=null)`
present, no `phone` line, no `No service published for: phone`, then
`NPE: null cannot be cast to non-null type android.telephony.TelephonyManager`.

## What this JAR adds

`adapter.activity.TelephonyFetcher` mirrors `WifiFetcher`: it reflectively replaces the `SYSTEM_SERVICE_FETCHERS`
entries for `phone` and `telephony_subscription_service` with fetchers that build a **non-null** manager by
allocating it **without its constructor** (`Unsafe.allocateInstance`, set `mContext`/`mSubId`), and seeds a
**present-but-off local binder** so method calls answer type-zero instead of NPEing.

- Registration follows **AOSP 14 `TelephonyFrameworkInitializer`** (`phone`→`TelephonyManager`,
  `telephony_subscription_service`→`SubscriptionManager`).
- Safe binder = `ITelephony`/`ISub` type-zero stub, published into `ServiceManager.sCache["phone"]` / `["isub"]`
  (reached by `getITelephony()` → `TelephonyServiceManager.ServiceRegisterer.get()` → `ServiceManager.getService`).
  Absent interface → skip (bare non-null manager still clears the cast wall), exactly like WifiFetcher's
  `IWifiManager`-absent path. `TelephonyServiceManager` is defaulted if the framework left it null.
- **present-but-off, nothing fabricated:** `getDeviceId()`/`getSimOperator()`/`getLine1Number()` → `null`
  (no fake IMEI/number/operator); `getSimState()`/`getPhoneType()`/`getCallState()`/`getDataState()` → `0`
  (UNKNOWN / PHONE_TYPE_NONE / IDLE / DISCONNECTED); `isNetworkRoaming()`/`hasIccCard()` → `false`. Honest
  "no telephony hardware", same floor as `account` (signed-in-nowhere) and `location` (present-but-off).

## New JAR SHA

| | sha256 | classes |
|---|---|---|
| base U10 | `37465d6d7f5e3d7be52929c2b43faf99315f86f0c23cc70e4aa858cb2ff98c59` | 186 |
| **U11** | **`277d46418604b30d61264c1d09f608866ebe0c3fdc683b2b6aae9b628be1206a`** | **193** |

Deterministic (built twice, identical). Staged: `$WORKSPACES/westlake-generation-u11-staging/oh-adapter-runtime-u11.jar`.

## New class list (U11 − U10 = exactly +7; U10 − U11 = empty)

```
adapter/activity/TelephonyFetcher
adapter/activity/TelephonyFetcher$1          (phone fetcher Builder)
adapter/activity/TelephonyFetcher$2          (subscription fetcher Builder)
adapter/activity/TelephonyFetcher$3          (seedSafeBinder Binder subclass)
adapter/activity/TelephonyFetcher$4          (replaceFetcher ServiceFetcher InvocationHandler)
adapter/activity/TelephonyFetcher$Builder
adapter/activity/TelephonyFetcher$ZeroHandler
```

Wiring = two build-time smali needles (no frozen source touched):
1. `B7BindFixes.smali`: `J10eWebView.install()` (carried from U9/U10);
2. `SystemServiceFetcherStubs.smali`: `TelephonyFetcher.install()` after `WifiFetcher.install()` — a
   method-body change, not a class add (so the class set only grows by the 7 above).

**Frozen-safe:** FZ-004 `JarVerificationProviderFix.java` (blob c7b15f75) and FZ-006 `VibratorFetcher.java`
(blob e502d039) unchanged; `oh-adapter-runtime.jar` is not a frozen artifact; `SystemServiceFetcherStubs.java`
/`WifiFetcher.java` are not frozen. `check_frozen` expected 0 violations.

## Expected first-wall move (per evidence app)

| app | U9 (now) | U11 expected | judge |
|---|---|---|---|
| `x` (com.twitter.util.telephony) | `getSystemService("phone")` → null → `NPE: null cannot be cast to TelephonyManager` | `phone` fetcher non-null → cast succeeds → **first wall moves past the telephony NPE**; next wall read from the window hilog | t20 + hilog (`[B8-FETCH] phone TelephonyManager allocated (non-null)`) |
| `toutiao` | 15 `phone` + 5 `wifi` call-sites; phone null | phone non-null + present-but-off `ITelephony` → the phone calls answer type-zero instead of NPE (wifi already provided). **Remains `dead` overall** (native libstdc++/libjnigraphics + other Java walls); this clears one Java wall | hilog (telephony null-service failure gone) |

Not claimed lit: this is **one** wall of several for both apps. Freeze gate (tiered): freeze the `phone`
binder once **≥2 different apps** pass the telephony wall (≥1 lit at t20; others by log — the
`TelephonyManager`-null failure gone, first fatal moved), with a non-regressing unified sweep.

## Reproduce

```
python3 benchmark/2026-10-01-u11-jar/build/build_u11.py      # prints sha256 + DETERMINISTIC + class delta
```

Next: the U11 window (jar `277d4641` + cx-bms U11 native) — `runtime_fp` self-computed at finalize; phone/wifi
on the beneficiary shards, x + toutiao read at t20.

## Cluster 3 added — ssl-engine (U11b)

U11b = U10 + cluster 1 (phone) + **cluster 3 (ssl-engine)**, one jar version.

- **New file:** `src/WlSSLEngine.java` (package `adapter.compat`) — a non-null stub `SSLEngine`: protocol /
  cipher / session / mode getters return sane non-null values; `wrap`/`unwrap` throw `SSLException` (metadata
  only, no real TLS). `WlSSLEngine.create()` is the factory.
- **Wiring (smali needle, no frozen file):** both `WestlakeSSLContextSpi.engineCreateSSLEngine()` overloads
  return `WlSSLEngine.create()` instead of `null` (verified x2). `WestlakeSSLContextSpi` is not frozen; the
  change is a method-body swap, so the class set only grows by `WlSSLEngine` (+ its inner).
- **New JAR SHA:** U11b `d75e90c023353e88bc5e66a29a3c9edeacd76c7c614f62e3749b311b4090fef8` (supersedes the
  phone-only U11 `277d4641`); 195 classes (U10 186 + 7 TelephonyFetcher + 2 WlSSLEngine); deterministic.
- **Expected first-wall move — `fd-client`:** `SSLContext.createSSLEngine()` → non-null → `getEnabledProtocols()`
  non-null → MainApp TLS setup completes → the Dagger object graph builds → `SessionMixin.accountManager` is no
  longer null. Both U9 walls (SSLEngine null **and** accountManager null, which was its consequence) clear from
  this one root fix — so fd-client is a **light candidate**, not merely a wall-move. Lazy-TLS apps (OkHttp) never
  call `createSSLEngine`, so null→non-null is strictly additive (no regression).
