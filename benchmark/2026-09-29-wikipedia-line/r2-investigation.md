# R2 investigation — artifact map + interface audit (2026-09-29, cc-wiki)

Evidence-first. Goal of R2 (outer ring): connectivity direct-Manager + tolerant
exception handler + interface-class check + WebView stub, on 5ea, deploy ASAP.
Investigation shows two of these are **not** a quick `oh-adapter-runtime.jar` swap.

## Board artifact map (which JAR holds what, 5ea v3a)

| class | board artifact | replaceable? |
|---|---|---|
| `adapter/activity/*` (AppSchedulerBridge, LocalServiceBinders, B7/B8 helpers) | `oh-adapter-runtime.jar` (72 KB) | YES — I build it via `build.py` (baksmali-inject), bind-mount overlay (R1 did this) |
| `adapter/core/OHServiceManager` | `oh-adapter-framework.jar` (123 KB) | YES — small, runtime-loaded, baksmali-patchable, bind-mount overlay |
| `adapter/core/ConnectivityManagerAdapter`, `OhConnectivityState` | **absent on board** | route-A never ported them (Westlake has them) |
| `com.android.internal.os.AppSpawnXInit` (item 5 tolerant handler) | ~~boot image~~ **CORRECTED: `oh-adapter-runtime.jar`** (non-BCP, PathClassLoader; r14 dex has `AppSpawnXInit`, `$BackgroundTolerantUncaughtHandler`, `$FatalUncaughtHandler`). The original "0 hits" grep covered framework.jar, framework-classes.dex.jar and oh-adapter-framework.jar only — the runtime jar was never searched. | YES — runtime-JAR swap (as cc-t3's tolerant UEH did) |
| `android.net.IConnectivityManager` | **absent from both framework jars** (0 hits) | — the v3a BCP has no such interface class |
| `android.net.ConnectivityManager` | referenced in both framework jars but **class def not found in either** — route-A connectivity is non-standard; def location unknown | — |

## Interface-class loadability audit (item 2) — LocalServiceBinders `proxy(name, DESCRIPTOR, …)`

`proxy()` does `Class.forName(DESCRIPTOR)`; a missing class → ClassNotFoundException → that service returns null.

| service | interface descriptor | in v3a BCP? |
|---|---|---|
| uimode | android.app.IUiModeManager | YES |
| power | android.os.IPowerManager | YES |
| alarm | android.app.IAlarmManager | YES |
| clipboard | android.content.IClipboard | YES |
| account | android.accounts.IAccountManager | YES |
| audio | android.media.IAudioService | YES |
| appops | com.android.internal.app.IAppOpsService | YES |
| locale | android.app.ILocaleManager | YES |
| notification | android.app.INotificationManager | YES |
| jobscheduler | android.app.job.IJobScheduler | YES |
| **connectivity** | **android.net.IConnectivityManager** | **NO → CNFE → null** |
| location | android.location.ILocationManager | YES |
| webviewupdate | android.webkit.IWebViewUpdateService | YES |
| batterystats | com.android.internal.app.IBatteryStats | YES |
| batteryproperties | android.os.IBatteryPropertiesRegistrar | YES |

**Result: only `connectivity` is broken by a missing interface class.** All 14 other
stubs are fine. This exactly matches the R1 divergence (onGoOffline NPE from a null
connectivity service).

## Why the outer ring's R2 items are blocked / need re-scope

- **item 5 (tolerant handler)**: ~~lives in `AppSpawnXInit` = boot image, not a JAR~~
  (corrected: `AppSpawnXInit` is in the runtime JAR, see table). The main-thread point stands: my
  R1 crash is on the **main thread** (`onGoOffline` via `Handler.handleCallback` → `Looper.loop`
  → `ActivityThread.main`). Westlake's `initChild` doing `return;` instead of `System.exit(1)`
  keeps the *process* alive but the main looper is already dead → no UI. So item 5 would not
  *light* this crash (it's the fix for the background `onCreate:538` NPE, which R1 already got past).
- **item 1 (connectivity)**: the direct fix (make the app online → onGoOffline never fires),
  but `android.net.IConnectivityManager` is absent, so Westlake's `ConnectivityManagerAdapter`
  (which `Class.forName`s it) cannot be copied verbatim; and route-A's `ConnectivityManager`
  itself is non-standard (class def not in the framework jars). Fix spans `oh-adapter-framework.jar`
  (OHServiceManager) + a route-A-native online answer + `liboh_connectivity_state.so`
  (staged only in `/data/local/tmp/a2hlab-framework-*/`, needs the app namespace).

## Decision needed from outer ring

1. Connectivity: do I own `oh-adapter-framework.jar` (OHServiceManager) + a route-A-native
   "online+validated" answer that does **not** need `android.net.IConnectivityManager`, plus
   getting `liboh_connectivity_state.so` into the child's namespace? Or is cc-t3/cx-bms already
   wiring the connectivity service/.so?
2. ~~AppSpawnXInit (boot image) tolerant handler — who owns the boot-image rebuild~~ — moot: it is
   in the runtime JAR; cc-t3 shipped a tolerant UEH there (r15). Later in the day connectivity was
   also solved in the runtime JAR (OnlineConnectivityManager subclass), see README.
3. cx-bms's ClassNotFound risk table confirms item 2; the above audit is my independent version.
