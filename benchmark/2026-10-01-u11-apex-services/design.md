# U11 JAR cluster — apex-module service registration (design)

**Dispatch (outer ACK(90), 2026-10-01):** register the client-constructable apex-module managers
(TelephonyManager etc.) with safe local binders, per AOSP 14. First answer: in route-A's `SystemServiceRegistry`,
is the apex module-initialization segment **deleted** or **throwing**? Evidence apps: `x` (null TelephonyManager),
`toutiao` (phone/wifi).

## 1. Answer to "deleted or threw": **neither — it is stock and present**

The deployed boot `framework.jar` is **sha256 `3e106350d882…`, byte-identical across every route-A generation**
(all `westlake-generation-*/payload/android/framework/framework.jar` and `westlake-n1-runtime-*`; only
`oh-adapter-runtime.jar` changes between generations). Disassembled (baksmali 2.5.2), its
`android.app.SystemServiceRegistry` is **stock AOSP 14**:

- `<clinit>` runs the apex initializers in a `try { … } finally { sInitializing = false }` block
  (`:try_start_6c9 … :try_end_711` → `:catchall_715` only resets `sInitializing` and **re-throws** — a `finally`,
  not a swallow). All of `ConnectivityFrameworkInitializer` … `VirtualizationFrameworkInitializer`
  `registerServiceWrappers()` are **present** (24 calls, lines 1538–1607). **Not deleted.**
- The apex initializer + manager classes are **bundled into this framework.jar** (`TelephonyManager`,
  `WifiManager`, `TelephonyFrameworkInitializer`, … are defined, not just referenced). So the calls do **not**
  `NoClassDefFoundError`. **Not throwing-fatally** — and it cannot be, because `getSystemService` for
  activity/window/input/etc. works, which proves the `<clinit>` completed.
- `TelephonyFrameworkInitializer.registerServiceWrappers()` is **not a no-op**: it registers `"phone"` →
  `TelephonyManager` via `SystemServiceRegistry.registerContextAwareService(name, cls, …WithoutBinder)`, whose
  producer lambda is `context -> new TelephonyManager(context)`. The resulting fetcher is `SystemServiceRegistry$140`
  (a `CachedServiceFetcher`); `getService` catches **only** `ServiceManager$ServiceNotFoundException`
  (→ `onServiceNotFound` logs `No service published for:`), everything else propagates.

So the stock registration is intact. The gap is **not** in the static block.

## 2. The real mechanism — route-A nulls specific apex services, and we already backfill some

From `x`'s U9 hilog (`$WORKSPACES/westlake-harness-u7-executor/benchmark/2026-10-01-u9-native/rollout/approved-j10g/boards/61b-r2/runner/remaining-original/20261001T192815-669fe3b4/61b…/x/hilog.txt`), during our in-process init:

| log line | meaning |
|---|---|
| `[ONLINE-CM] connectivity fetcher replaced (prev=android.app.SystemServiceRegistry$140)` | apex `connectivity` fetcher **was** registered (`$140`); we replace it with `ConnectivityManagerAdapter` |
| `[B8-FETCH] media_session fetcher replaced (prev=android.app.$Proxy21)` | `media_session` **was** registered |
| `[B8-FETCH] alarm/vibrator_manager/appwidget/restrictions fetcher replaced (prev=$7/$56/$83/$65)` | stock-registered; we replace |
| **`[B8-FETCH] wifi fetcher replaced (prev=null)`** | **`wifi` was absent** from the fetcher map on route-A — and **we already backfill it** |
| *(no `[B8-FETCH] phone …` line)* | **we do not install a `phone`/telephony fetcher** |
| `W SystemServiceRegistry: No service published for: game / dropbox / usagestats` only | **no `phone` line** — phone did **not** take the ServiceNotFound path |
| `NPE: null cannot be cast to non-null type android.telephony.TelephonyManager at com.twitter.util.telephony.a.run` | `x` did `getSystemService("phone") as TelephonyManager` → **null** |

**Conclusion.** On route-A some apex services land in `SYSTEM_SERVICE_FETCHERS` (connectivity `$140`,
media_session, bluetooth, nfc…) while **`wifi` and `phone` come out `null`/non-functional**. We have **already**
adopted the fix pattern — an in-process **fetcher install** in `B8BindExtras`/`AppSpawnXInit` that backfills
`wifi` (`prev=null`), plus `power_exemption`/`jobscheduler` (`prev=null`) and replaces the degenerate stock ones.
**The only missing apex service that `x` hard-requires is `phone`.** There is no `phone` install, so
`getSystemService("phone")` returns null and the Kotlin `as TelephonyManager` NPEs.

> The exact reason the *stock* `phone`/`wifi` `$140` producers come out null on route-A (class verification of
> the telephony/wifi dex under the OH ART image vs. the `$140` producer path) is **not on the critical path**:
> `wifi (prev=null)` is already handled by installing our own fetcher, so U11 extends the **same proven
> mechanism** to `phone`. A 5-minute on-board probe (reflect `SYSTEM_SERVICE_FETCHERS.get("phone")`, then
> `new TelephonyManager(ctx)`) can confirm whether the stock fetcher is absent or present-but-null; the fix is
> identical either way (we overwrite the entry).

## 3. Fix — install the apex managers in the proven B8-FETCH / fetcher-swap path (JAR layer, no boot rebuild)

Mechanism #3 from `provided-services.md` (reflective `SYSTEM_SERVICE_FETCHERS` swap), already used for
`jobscheduler` (`AppSpawnXInit.installJobSchedulerStub:2073`) and `wifi`. For each apex service we add:

1. a `SYSTEM_SERVICE_FETCHERS[name]` entry whose `createService(ctx)` returns the **client-constructable**
   manager (AOSP 14 producer, e.g. `new TelephonyManager(context)`), and the matching
   `SYSTEM_SERVICE_NAMES[ManagerClass] = name` so the `getSystemService(Class)` overload also resolves;
2. a **safe local binder** (same `LocalServiceBinders` pattern as `account`/`power`/`alarm`) published into
   `ServiceManager.sCache[binderName]` so the manager's lazy per-call binder lookups return a degenerate-but-safe
   stub instead of NPE/throw.

This runs in-process in `AppSpawnXInit.initChild` (the adapter runtime jar + appspawn-x) — **no boot image
rebuild** (not Mac-reproducible), and `check_frozen` is clean (it touches no frozen artifact path).

### Per-service plan (client ctor + safe binder), ranked by the gap table

Ranking from `benchmark/2026-10-01-system-service-gap/gap-table.csv` (requested-key / U9-not-lit / call-sites):

| rank | service | name | manager (client ctor) | safe local binder | keys / not-lit | status |
|---|---|---|---|---|---|---|
| 1 | telephony | `phone` | `new TelephonyManager(context)` | `ITelephony` → no SIM, `SIM_STATE_ABSENT`, empty IMEI/number, no registration, 0 subscriptions | 35 / 23 | **U11 new** |
| 1b | subscription | `telephony_subscription_service` | `new SubscriptionManager(context)` | `ISub` → empty subscription list | 1 / 1 | U11 (phone drags it in) |
| 2 | wifi | `wifi` | `new WifiManager(context, IWifiManager, looper)` | `IWifiManager` → WIFI_STATE_DISABLED, no networks | 30 / 22 | **already installed** — verify it yields non-null & reaches the "wifi off" path, not null |
| 3 | bluetooth | `bluetooth` | `new BluetoothManager(context)` (→ `BluetoothAdapter`) | `IBluetoothManager` → adapter OFF, no bonded devices | 11 / 7 | U11 new |
| 4 | wifip2p | `wifip2p` | `new WifiP2pManager(IWifiP2pManager)` | `IWifiP2pManager` → unsupported/off | 4 / 4 | U11 new |
| 5 | media_session | `media_session` | already registered (`$Proxy21`) | — | 31 / 6 | low priority (25 of 31 already lit → null tolerated) |

**Safe = present-but-off, never fabricated.** Following the `account` ("signed-in-nowhere") and `location`
("present-but-OFF") precedent: no fake SIM / IMEI / phone number / scan results. The manager is non-null so the
cast/`requireNonNull` succeeds and the app takes its "no telephony / wifi off" branch, not the crash branch.
Returning fabricated identifiers would be both dishonest and a privacy problem; an empty/off device is the honest
compatibility floor.

## 4. Evidence apps & expected first-wall move

- **`x`** (`com.twitter.util.telephony.a.run`): `getSystemService("phone") as TelephonyManager` → today null →
  NPE. With the `phone` fetcher installed, the cast succeeds → **first wall moves** past the telephony NPE
  (next wall, if any, read from the window hilog).
- **`toutiao`**: 15 `phone` call-sites + 5 `wifi` call-sites (`system-service-gap` scan). phone/wifi non-null
  removes those null-service walls. toutiao remains `dead` overall (its native libjnigraphics wall + Java-layer
  walls are separate, U11+); this is one wall of several — judged by log, not by lit.

Validation gate (same tiered-freeze rule as the other service floors): freeze the `phone` binder once **≥2
different apps** pass the telephony wall (≥1 lit at t20; others by log — the `TelephonyManager`-null failure gone,
first fatal moved), with a non-regressing unified sweep.

## 5. What was wrong before / what this sets

- **The framing to drop:** "the apex init was deleted/stubbed, so re-add the registration." It was **not**
  deleted — the stock registration runs; specific apex services (`phone`, `wifi`) just resolve to null on
  route-A, and we already backfill them one-by-one in the B8-FETCH path.
- **Rule this sets:** apex-module services join the existing in-process service-floor mechanism, not a boot
  framework.jar edit. Each new manager is **client-constructed + backed by a present-but-off local binder**, is
  gated by the tiered-freeze (≥2 apps past the wall), and fabricates nothing. `phone` is the first and
  highest-impact (35 requesters, 23 not-lit); `wifi` is already in and only needs a non-null verification;
  `bluetooth`/`wifip2p` follow; `media_session` is deferred (already tolerated null by 25/31 requesters).
