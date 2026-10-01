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

## Cluster 5 added — content-provider (U11c)

U11c = U10 + cluster 1 (phone) + cluster 3 (ssl-engine) + **cluster 5 (app ContentProviders)**, one jar version.

- **Finding (quantified):** route-A projects the app's ProviderInfo into `AppBindData.providers` but **never
  instantiates them** — the stock `ActivityThread.installContentProviders` step is not run (confirmed: no such
  call in the adapter; `B8BindExtras.afterProviders` only fills metaData). So `getContentResolver().query(its own
  authority)` returns a null Cursor. **120/168 U9 keys declare >=1 provider** (366 total); notepad is the
  evidence (its authority `content://com.nononsenseapps.notepad.MyContentAuthority`, `Cursor.moveToFirst()` on null).
- **New file:** `src/AppContentProviders.java` — mirrors AOSP 14 `installContentProviders`/`installProvider`
  (local path): per ProviderInfo, `loadClass(name).newInstance()` -> `attachInfo(appContext, info)` (runs its
  onCreate) -> `getIContentProvider()` -> build `ContentProviderHolder` -> publish the batch into
  `adapter.contentprovider.ContentProviderRegistry` (what `ActivityManagerAdapter.getContentProvider` reads).
  All hidden APIs by reflection; per-provider try/catch (one bad provider never blocks the rest, no regression).
- **Wiring (needle) — corrected to post-bind (U11d):** `AppContentProviders.install()` (no-arg; reads
  `ActivityThread.mBoundApplication.providers` + `currentApplication()`) right **after the stock
  `handleBindApplication` reflection call returns** in `AppSchedulerBridge` (the `[B43-BIND] handleBindApplication
  returned OK` point), where `currentApplication()` is non-null. No frozen file touched.
  - **Why not earlier:** the first wiring (U11c, after `B8BindExtras.afterProviders`) was **before**
    `handleBindApplication`, so `makeApplication` had not run and `currentApplication()` was null → `install()`
    skipped (the fix did not fire). AppSchedulerBridge runs `makeApplication` + `Application.onCreate` both inside
    the single opaque `handleBindApplication(data)` call, so the only seam where the Application is live is after
    it returns.
  - **Ordering caveat:** AOSP installs providers inside `handleBindApplication` (before `Application.onCreate`);
    here they install just after it, so provider `onCreate` runs **after** `Application.onCreate`. Correct for
    apps that query their own provider at **Activity**-launch time (notepad: `MainActivity.onCreate`); an app that
    queries its own provider inside `Application.onCreate` is not covered (none observed; the stock path not
    running at all is the pre-existing problem — late install beats never). Verified empirically: U9 hilogs for
    provider apps show `providers populated` + `handleBindApplication returned OK` but **no** publish/instantiation.
- **New JAR SHA:** U11d `84c8da6bb81f8a58da4a07a62cfc29f6dff0d7339e5c03ffd46145f8ceacd44c` (supersedes the
  mis-wired U11c `7443424084bc6848…`); 196 classes (U10 186 + 7 + 2 + 1); deterministic. Each provider failure
  logs `[B8-PROV-INSTALL] provider <class> (authority <auth>) not installed: <ex>` (hilog-visible).
- **Expected first-wall move — `notepad`:** its own ContentProvider is instantiated + published at bind, so
  `query(content://com.nononsenseapps.notepad...)` returns a real Cursor instead of null -> `moveToFirst()` NPE
  gone, MainActivity.onCreate proceeds (light candidate).
- **Regression controls = already-lit keys that declare providers** (e.g. `fd-k9` 9, `fd-android` 9,
  `fd-droidify`, `markor`, `newpipe`, `aegis`): installing their providers must keep them lit (no new provider
  onCreate crash).

### Cluster 5 dedup (U11e)

Before re-instantiating a provider, `AppContentProviders` checks `ActivityThread.mLocalProvidersByName` by
`ComponentName(packageName,name)`; if stock already instantiated it -> `[B8-PROV-INSTALL] <authority> already
instantiated by stock; skipped` and skip (never run a provider onCreate twice). Final log counts both
(`installed N/total app providers (M already instantiated by stock)`). On the first board run **M splits the root
cause**: M>0 => stock's installProvider succeeded (gap = publish/registry); M=0 => stock never instantiated (gap =
the install step). **New JAR SHA:** U11e `b093243b0da702b74af1c693af93ea937652fae08192760c0a9c536d647816c8`
(supersedes U11d); 196 classes; deterministic. Cluster 4 (keystore) is cc-wiki's; merges in later.

## U11g — cluster 7 J10d guard + cluster 4 keystore probe; cluster 6 stopped

- **Cluster 7 (appcompat, fd-api/termux) — J10dTheme alias guard (needle):** `J10dTheme.restore` now returns early
  when `ai.targetActivity != null && !ai.targetActivity.isEmpty() && !ai.targetActivity.equals(ai.name)` (an alias
  launch whose target theme `AliasTargetTheme` already re-resolved), logging `[J10d-THEME] <name> skipped: alias
  target theme owned by AliasTargetTheme`. Root cause was a fix-interaction: J3 re-resolved the target to the app's
  AppCompat theme `0x7f120252`, J10d then restored the alias manifest theme `0x1030237` (translucent, non-AppCompat)
  and won → AppCompat crash. Guard uses only `ActivityInfo` (android.jar).
- **Cluster 4 (keystore, moodcairns) — cc-wiki KeystoreBoardProbe merged (diagnostic):** `KeystoreBoardProbe`
  (master ffc687465, log-only) is compiled in (a compile-only `SoftwareAndroidKeyStore.NAME` stub lets it build;
  the real class in the base is untouched) and wired via needle `KeystoreBoardProbe.run("_androidx_security_master_key_")`
  right after `AppContentProviders.install()`. `[WL-KS-PROBE]` lines reach hilog (System.err). **Timing caveat:** on a
  fresh run moodcairns creates the master key during its Activity flow, so at the post-bind call the key may be absent
  (`key absent -> not the BadTag path`); if so a keystore-access hook is the follow-up. (Mac probe is 6/6; the on-board
  divergence is the default Cipher provider.)
- **Cluster 6 (pkg-self getInstallSourceInfo) — STOPPED per the reproduction gate:** `PackageManagerAdapter` is in
  **`oh-adapter-framework.jar`, a BCP jar** (`build_aosp_fw.sh`: ECS-only; editing a BCP jar forces an ART boot-image
  rebake, not Mac-reproducible). Routed to the image/BCP lane. No `IPackageManager` Proxy (OHServiceManager records the
  @hide-AIDL Proxy deadlock).
- **New JAR SHA:** U11g `73c0da44a8fb2841fa6ea8cf727778aeed36ab5636b9b5b35f1f288796c39bbd`; 197 classes; deterministic.
  Clusters in the jar: 1 phone, 3 ssl-engine, 5 content-provider(+dedup), 7 appcompat guard, 4 keystore probe
  (diagnostic). Clusters 2 (R8 map) and 6 (image lane) are out.

## U11h — keystore probe selfTest version (next-round FINAL)

Replaced `KeystoreBoardProbe` with cc-wiki's selfTest version (master d2d11b17d). `selfTest()` is key-independent:
it generates its own random 256-bit AES `SecretKeySpec` and runs Tink's exact `AES/GCM/NoPadding` framing through
the DEFAULT provider, logging `[WL-KS-PROBE] selftest cipher provider=… ivLen=… validateAead=…` — so it works at
bind time with **no app key needed** (resolving U11g's timing caveat where the key was absent at bind).
`run("_androidx_security_master_key_")` (unchanged post-bind wiring) now calls `selfTest()` first, then the
per-key check only if the app key exists. **hilog channel confirmed:** the `[WL-KS-PROBE]` lines are
`System.err.println` (verified in the compiled smali) → AppSpawnXJava `[stderr]` → hilog (same channel as
`[B8-FETCH]`/`[WL-KEYSTORE]`). **New JAR SHA:** U11h
`14ed34bc70ad0248a754bd046a70f8a72c9353bac6de5da208da3a6980f31044`; 197 classes; deterministic. This is the
next-round FINAL U11 JAR (clusters 1/3/5+dedup/7 fixes + 4 keystore selfTest probe).

## U11i — cluster-5 empty-providers smoke-marker fix

`AppContentProviders` returned silently when the app declares no providers, so helloworld (none declared) never
printed `[B8-PROV-INSTALL] installed …` → the smoke's helloworld-keyed B8-PROV-INSTALL marker would false-FAIL.
Now it logs `[B8-PROV-INSTALL] installed 0/0 app providers (none declared)` before the empty return (outer,
2026-10-02). **New JAR SHA:** U11i `5ae3dd29d45c2270e8a53a9dc4bbeeca8972b9b092f91898a15d605bc1cc0108`; 197 classes
(class set identical to U11h, only AppContentProviders body changed); deterministic. u10.1.json probe.files jar
sha updated to U11i. This supersedes U11h as the next-round FINAL U11 JAR.
