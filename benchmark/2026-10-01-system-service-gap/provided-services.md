# System-service provisioning inventory vs request scan (U9 runtime, #90)

**What our deployed U9 runtime hands back non-null for `getSystemService` / `ServiceManager.getService`, how each is
provided (real OH / local binder / stub), with file:line — joined with oc-t4's per-app request scan into a gap table.**

Source of truth = `vm-copies/westlake-current/framework` (RUNBOOK §79: read-only tar snapshot of the live VM tree that
builds `oh-adapter-runtime.jar`). Its `OHServiceManager.java` is **byte-identical** to the newest deploy copy
(`westlake-harness-bms-deploy/bms/src/.../OHServiceManager.java`, 2026-09-28), so this is the deployed lineage — **not**
the stale `_cc-wiki-b1-src` bridge worktree (Unity-era OHServiceManager that still routed `audio`/`vibrator_manager`
to `unitySvcStub` and had `launcherapps`/`usagestats` cases the current tree dropped).

## Three provisioning mechanisms (do not conflate them)

A service shows up as "provided" through **one of three** code paths; a request only traces to our `ServiceManager`
for the first two:

1. **`ServiceManager` path** — `getService(name)`/`getServiceOrThrow(name)` returns a binder because either
   (a) `ServiceManager.sServiceManager` = our `OHServiceManager` answers `name` in `lookupAdapter()`, or
   (b) `ServiceManager.sCache` was pre-seeded with `name`→binder.
2. **Framework static-holder path** — an `installXxxStub()` in `AppSpawnXInit.initChild()` writes the manager singleton
   **directly into AOSP's own static field** (`ActivityThread.sPackageManager`, `WindowManagerGlobal.sWindowManagerService`,
   `InputManagerGlobal`, `ActivityClient.INTERFACE_SINGLETON`, AudioManager's static). `getSystemService` is satisfied
   **without ever calling our ServiceManager** — so these never appear as a `getService` hit.
3. **`SystemServiceRegistry.SYSTEM_SERVICE_FETCHERS` swap** — the fetcher map entry is replaced reflectively, so
   `getSystemService` builds a manager from our object with no binder lookup at all.

`initChild` order (`AppSpawnXInit.java:1064–1111`): `installActivityManagerStub → installPackageManagerStub →
installWindowManagerStub → installInputManagerAdapter → installAudioServiceStub → installJobSchedulerStub →
installServiceManagerAdapter(+primeWebViewUpdateServiceCache) → installContentServiceAdapter →
installStorageManagerAdapter → installActivityClientControllerStub → preInitSettingsCache`.

## Inventory — provided non-null (quality matters as much as presence)

All paths below are under `vm-copies/westlake-current/framework/`.

### Real OH-routed adapters (bridge to OH inner_api; real data)
| service | how | file:line |
|---|---|---|
| `activity` | `ActivityManagerAdapter` (real OH via samgr `nativeGetOHAbilityManagerService`; **Proxy-stub fallback** on samgr hang, and skipped entirely under `ASX_DIRECT_LAUNCH=1`) | `core/java/OHServiceManager.java:88` / `appspawn-x/.../AppSpawnXInit.java:1296` |
| `activity_task` | `ActivityTaskManagerAdapter` (real) | `OHServiceManager.java:90` |
| `package` | `PackageManagerAdapter` (real; Proxy-stub fallback) + `ActivityThread.sPackageManager` | `OHServiceManager.java:92` / `AppSpawnXInit.java:1385` |
| `permission` (`permissionmgr`) | `PermissionManagerAdapter` | `OHServiceManager.java:94` / `package-manager/java/PermissionManagerAdapter.java` |
| `window` | `WindowManagerAdapter` (real; Proxy-stub fallback) + `WindowManagerGlobal.sWindowManagerService` | `OHServiceManager.java:96` / `AppSpawnXInit.java:1423` |
| `display` | `DisplayManagerAdapter` | `OHServiceManager.java:98` / `window/java/DisplayManagerAdapter.java` |
| `input` | `InputManagerAdapter` (real, **no Proxy fallback** — returns on failure) into `InputManagerGlobal` | `AppSpawnXInit.installInputManagerAdapter:1470` |
| `connectivity` | `ConnectivityManagerAdapter` — **backed by the OH default network** (real reachability; the #90/Toutiao-era fix for "network unavailable" on a working radio) | `OHServiceManager.java:123` / `core/java/ConnectivityManagerAdapter.java` |
| `webviewupdate` | `WebViewUpdateServiceAdapter` (conditional `isAvailable()`) + `sCache` prime | `OHServiceManager.java:112` / `AppSpawnXInit.primeWebViewUpdateServiceCache:2364` |

### Compatibility-floor adapters (binder present, deliberately degenerate — NOT real OH yet)
| service | how | file:line |
|---|---|---|
| `input_method` | `InputMethodManagerAdapter` — **NO_IME** baseline (non-null binder so AOSP IMM doesn't throw; no actual IME) | `OHServiceManager.java:105` / `window/java/InputMethodManagerAdapter.java` |
| `location` | `LocationManagerAdapter` — **present-but-OFF** (providers exist, none enabled, no fixes; takes apps down the "location disabled" path, not the crash path). Real OH routing is a separate change. | `OHServiceManager.java:128` / `core/java/LocationManagerAdapter.java` |

### In-process local binders (`LocalServiceBinders` — idle-phone answers; **nothing reaches OH**)
| service | behaviour | file:line |
|---|---|---|
| `uimode` | NORMAL mode type; night mode from `Resources` config | `OHServiceManager.java:132` / `core/java/LocalServiceBinders.java:54` |
| `power` | interactive; no power-save; wake locks accepted | `OHServiceManager.java:133` / `LocalServiceBinders.java:57` |
| `thermalservice` | `IThermalServiceImpl` local binder (the `power` fetcher also requires it) — *no oc-t4 row (internal to PowerManager)* | `OHServiceManager.java:134` / `core/java/westlake/impl/IThermalServiceImpl.java` |
| `alarm` | `set()` accepted, **never delivered**; no next-alarm | `OHServiceManager.java:135` / `LocalServiceBinders.java:67` |
| `clipboard` | in-process `ClipData`, local to the process | `OHServiceManager.java:136` / `LocalServiceBinders.java:70` |
| `account` | signed-in-nowhere: empty account list, no features, no token | `OHServiceManager.java:137` / `LocalServiceBinders.java:73` |

### Local stubs (no-op binders published into `sCache` / framework statics)
| service | behaviour | file:line |
|---|---|---|
| `audio` | `IAudioService` all-defaults Proxy (void/primitive/object safe defaults); AudioManager static | `AppSpawnXInit.installAudioServiceStub:1569` |
| `storage` / `mount` | `IStorageManager` local Proxy (reports one volume); published as `sCache["mount"]` | `AppSpawnXInit.installStorageManagerAdapter:1669` (`cache.put("mount"…)` :1814) |
| `content` | `IContentService` local Proxy — observer lifecycle no-ops, sync APIs empty defaults; `sCache["content"]` | `AppSpawnXInit.installContentServiceAdapter:1837` (`put …"content"` :1922) |
| *(ActivityClient)* | `ActivityClientControllerAdapter` (real, no fallback) into `ActivityClient.INTERFACE_SINGLETON` — not a named service | `AppSpawnXInit.installActivityClientControllerStub:1997` |

### Registry fetcher swaps (`SYSTEM_SERVICE_FETCHERS`)
| service | behaviour | file:line |
|---|---|---|
| `jobscheduler` | no-op `JobScheduler` — accepts/remembers jobs, **never runs them**; also registers `SYSTEM_SERVICE_NAMES[JobScheduler]`. Fixes McDonald's `null cannot be cast to JobScheduler` abort. | `AppSpawnXInit.installJobSchedulerStub:2073` (put :2121) |

### Settings (non-binder, satisfies reads)
| service | behaviour | file:line |
|---|---|---|
| `settings` | `Settings.Global/Secure/System` `NameValueCache` primed + local `IContentProvider` stub (PhoneWindow lookups bypass the ContentProvider) — not a system-service binder | `AppSpawnXInit.preInitSettingsCache:2245` / `installSettingsContentProviderStub:2164` |

### Explicit null (by design — OH has no analog, boot path tolerates)
`network_management`, `content_capture`, `game` → `OHServiceManager.java:141`.

## Honest gaps in the dispatch vocabulary (flagged, not invented)
- **`B8BindExtras.SERVICES`, `B7BindFixes.installServiceStubs` do not exist** in any deployed lineage searched
  (`vm-copies/westlake-current`, `_cc-wiki-b1-src/adapter`, `westlake-harness/bms/src/adapter`,
  `westlake-harness-bms-deploy/bms/src/adapter`). The current tree uses the `installXxxStub()` methods above instead.
  Those names appear to be from an older/bridge lineage; mapped to their current equivalents above.
- **Projection proxies** (`UserManagerProjectionProxy`, `StorageManagerProjectionProxy`,
  `DisplayManagerProjectionProxy`, `PermissionManagerProjectionProxy`, `PermissionControllerProjectionProxy`,
  `ContentNoOpStub`, `ContentServiceAdapter`) exist **only in `_cc-wiki-b1-src`**, not in the deployed tree — so
  "user"/"storage"-via-projection is **not** how the deployed runtime provides them (storage comes from
  `installStorageManagerAdapter`→`mount`; **`user` is NOT provided** — see gap table).
- **`shortcut` and `media_session` are defined but NOT wired**: `WlShortcutService.install()` (`sCache["shortcut"]`)
  and `WlMediaSession.install()` (`SYSTEM_SERVICE_FETCHERS["media_session"]` + `sCache`) are only called from
  `appspawn-x/tests/.../*HostTest.java`, **never from `initChild`**. Treated as NOT provided at runtime.
- `InProcessServiceBinder` (`activity/java`) is for **in-app `bindService`** to app-local `Service`s (e.g. noice
  `SoundPlaybackService`), not a framework system service — out of scope for this inventory.

## Gap table — VOID (awaiting oc-t4 rework)

**The oc-t4 request scan this was to be joined against was bounced by the outer ring (ACK 90 ②): it must be redone by
call-site, not by string reference.** So the join (`gap-table.csv`) is **void and removed** (see `GAP-TABLE-VOID.txt`);
recompute once oc-t4 redelivers. oc-t4's raw scan is still staged here (`oc-t4-service-summary.csv` /
`oc-t4-requested-services.csv`) only as the input that was rejected — **do not derive conclusions from its lit/dead
numbers.**

What stands (independent of oc-t4) is the **provided-non-null inventory above** (`provided-services.csv`), read straight
from our own source. Count from that: our runtime explicitly provides a non-null answer for **~20** service names
(real-OH / local-binder / local-stub / registry-stub / settings-cache), leaves **3** null by design
(`network_management`/`content_capture`/`game`), and has **2** defined-but-unwired (`shortcut`/`media_session`).

**Why the join needs call-site data (the reason it was bounced):** a raw string-reference scan counts names an app's
code *mentions*, not names that actually reach our `ServiceManager.getService`. AOSP's own `SystemServiceRegistry`
builds many managers (TextServices, Font, Print, Search, client-side Accessibility, LayoutInflater, …) with **no board
binder at all**, and most apps null-check or never exercise the service — so "mentioned but not provided" vastly
over-counts walls. The correct join is **per call-site**: which `getSystemService`/`getServiceOrThrow` calls are on a
reachable path AND dereferenced without a null-check. That is what oc-t4 is reworking.

## Verdict (our-source, oc-t4-independent)
- The highest-leverage services are **already provided** (activity / package / window / input / display / connectivity /
  jobscheduler, + power / clipboard / account local binders) — the walls the campaign already lit through.
- `location` and `input_method` are **present but degenerate** (OFF / NO_IME): binder present so AOSP doesn't throw, but
  no real OH routing. Real routing is a quality upgrade, separate from presence.
- `storage` is provided via the `mount` binder; `content`/`audio` via local no-op stubs; `settings` via a primed
  NameValueCache (non-binder). `user` is **not** provided by the deployed tree (the `UserManagerProjectionProxy` path is
  `_cc-wiki-b1-src`-only) — pending oc-t4's call-site data to say whether that matters.
- Next real wall is judged by **hilog**, not by request-count correlation (Toutiao died at `libflipped`/`libstdc++`, a
  native wall, not a missing service) — which is exactly why the string-reference join was bounced.

Evidence: `vm-copies/westlake-current/framework/{core,activity,window,package-manager,appspawn-x}/java/…` (lines cited).
`provided-services.csv` = the our-source inventory (no oc-t4 columns). Join deferred to oc-t4 call-site rework.
