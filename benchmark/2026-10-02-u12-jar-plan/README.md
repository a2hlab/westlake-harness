# U12: the round's one JAR plan (offline). One runtime jar, one stubs jar, no framework jar

#90, offline, nothing deployed. U12 is the next round's **single** JAR version. It merges three pieces:
- ① upstream 1c883ad's `WlSettingsProvider`, copied verbatim;
- ② U11j `OwnProviderLocal` (57aaaf7d63);
- ③ the android.net stub members (c6b1eb3bc0).

Each piece lands in exactly one jar, and each jar has one version. Both versions pass `deployed_class_diff --frozen`
against both board bases.

| jar (class loader) | U12 version | pieces | needs before a window |
|---|---|---|---|
| `oh-adapter-runtime.jar` (runtime `PathClassLoader`, `/system/android/framework/`) | **`3bca82c5ffba…`** (`build_u12.py`, U11i 5ae3dd29 + 4 new classes + 2 one-line needles) | ① + ② | single-file replace through `deploy_generation.sh`; no boot-image change |
| `adapter-mainline-stubs.jar` (boot classpath) | **`3a12918a624d…`** (c6b1eb3bc0's build on 2f365a75, unchanged) | ③ | **FZ-005 boot-image rebake on hw248 + T8's four gates (rb / t4b / G1 / G2)** |
| `oh-adapter-framework.jar` (boot classpath) | no change (keeps the board's copy) | none | – |

Persisted:
- runtime: `$WORKSPACES/westlake-inputs/generations/u12-runtime-v1/` (jar + `receipt.json`: base, sources,
  upstream blobs, scripts, toolchain, paired stubs SHA);
- stubs: `$WORKSPACES/westlake-inputs/generations/net-stubs-members-v1/on-2f365a75/`.

c6b1eb3bc0's second build (`on-f3bcc9d7`, `646a3199…`) is **retired**: the one stubs version is the 2f365a75
build. It also passes against the U9 stubs (gates below), so a separate per-base build is not needed.

## What was wrong first

- **"Copying WlSettingsProvider fixes jellyfin's ANDROID_ID" does not hold for our corpus.**
  - Across all 166 U9 hilogs, AOSP's NameValueCache fallback line `Settings: Can't get key android_id` appears in
    **one** key, `x`, and x survives the null. Its first fatal comes 2 s later, at `TelephonyManager` (hilog:31895
    vs :32788).
  - In 271 U10/U10.1 hilogs, android_id is read by no key.
  - `fd-mobile` (jellyfin, the upstream ledger row) never reaches the read. On U9 it is a black window with no
    fatal; its WebView UI is unavailable (`2026-10-02-upstream-copy-map`).
  - Predicted first-fatal moves from ①: **0**.
- **"The settings authority is not connected" is not upstream's wall.**
  - Upstream's path A (§611e) exists because their `acquireProvider("settings")` returned null and
    `Settings$Config.getStringsForPrefix` NPE'd (Material Catalog).
  - Route-A never returns null there. `ContentProviderRegistry` answers with an OH DataShare bridge that fails
    softly: `OH_CPBridge: query: not connected` in 162/166 U9 hilogs.
  - AOSP then reads null and logs `Can't get key` (162 keys, 18 distinct settings, `evidence/settings-census.csv`).
  - No settings read in any U9 hilog succeeded through the bridge, so replacing it cannot lose a working value.
  - In U9 the only Settings exception with a stack is subwaysurfers' AppLovin `SettingNotFoundException:
    limit_ad_tracking`, which the app catches.
- **Toutiao's U9 first fatal is not on any of these walls.**
  - U9 hilog:31733: `Unable to instantiate activity …MainActivity`, `Boolean.booleanValue()` NPE.
  - Cause: `MainActivity.<init>` unboxes `A9Q.a("enableGlobal")`. The APK's only put of `"enableGlobal"` is in
    `ArticleApplication.configInitScheduler`, which never ran: `attachBaseContext` had already died on the
    `libflipped.so` dlopen (hilog:31265-31291, `evidence/u9-wall-lines.txt`).
  - That is wall 1, native, handled by U10.1 policy; this JAR does not touch it.
- **Route-A's own copy of path B is hollow.** The deployed `AppSpawnXInit.installSettingsContentProviderStub` prints
  `[SettingsCache] provider injection skipped (rely on preInitSettingsCache)` and returns: 207 times across 165 U9 hilogs (every
  child process). `injectProviderHolder` is still in the jar but nothing calls it. No local source records why
  the method was emptied. U12 does not edit it: it adds the upstream body as a new class, called right after it.

## Where upstream hooks it, and where route-A's counterpart is

Upstream: a2hlab/westlake, `origin/corpus2-fixes` 2c46770aa27f (local `vm-copies/westlake-current`). Commit 1c883ad
adds the ANDROID_ID answer to an existing §611e provider.

| | upstream (framework 68 line) | route-A (U11i 5ae3dd29, baksmali line) | U12 |
|---|---|---|---|
| provider class | `framework/activity/java/WlSettingsProvider.java`, blob 22911038 (same at 1c883ad and at 2c46770) | none | **copied byte-identical**: `src/adapter/activity/WlSettingsProvider.java` |
| path A: synthetic `ProviderInfo{authority "settings", name adapter.activity.WlSettingsProvider}` appended to bind providers | `AppSchedulerBridge.java` (blob d048bb78) :547-560, then `realProviders.add(spi)` | `AppSchedulerBridge.smali` :3369 `buildProvidersFromManifest` → `setField(AppBindData, "providers")` → :3378 `B8BindExtras.afterProviders` | **not copied** (see below) |
| path B: `IContentProvider` Proxy injected into `NameValueCache.mProviderHolder.mContentProvider` of Settings$Global/$Secure/$System; `call` answers `WlSettingsProvider.answer(method, name)` | `AppSpawnXInit.java` (blob 30a699c1) :2273-2360, called first thing in `preInitSettingsCache` (:2364) | `AppSpawnXInit.smali` :4099 hollow `installSettingsContentProviderStub`; :6295 its call in `preInitSettingsCache` (:6280); `injectProviderHolder` :2294 still present, uncalled | **copied verbatim** as `adapter.activity.WlSettingsStub` (only edit: `private`→`public` on the entry method); needle after :6295 |

AOSP 14 matches upstream's AOSP 15 names: `sNameValueCache` (Settings.java:3754 System, :6261 Secure, :16755 Global; Config :18943 is not injected, as upstream),
`mProviderHolder` (:3103), `mContentProvider` (:3065), and `IContentProvider.call(AttributionSource, authority,
method, arg, extras)`. Upstream's "last two Strings" rule therefore yields `("GET_secure", "android_id")`.
`test_u12.py` replays AOSP 14's `getStringForUser` fast path (:3219ff.) against this.

**Why path A is deferred (inference, not proven):**
- AOSP's `installProvider` instantiates `info.name` through the **app** class loader, whose parent is the boot
  class loader.
- `adapter.activity.*` lives in the runtime jar, loaded by its own `PathClassLoader` (`Attempting to load
  AppSpawnXInit via PathClassLoader from …oh-adapter-runtime.jar`). It is not in either BCP jar: checked over every
  jar of both generations, including `oh-adapter-framework.jar` and `framework.jar`.
- A synthetic provider entry would therefore likely fail with `Unable to get provider` inside every app's
  `handleBindApplication`. With U11j's `OwnProviderLocal`, the same by-name path is taken even earlier.
- Path B covers everything the U9 hilogs show reading settings (all via NameValueCache).
- Minimal experiment, if wanted: one helloworld window, bind data plus a synthetic `adapter.activity.WlSettingsProvider`
  entry. Pass: `installProvider` logs no ClassNotFound and `content://settings` resolves to it. Fail: roll back the
  same window.

## Gates (`gate_u12.py` → `gates/gate-u12.txt`)

Bases are the `framework/` overlay the boards run: **promoted** = T8 v3 package, **unpromoted** = U9
`westlake-generation-u9-j10g-238ffc14`. On U9 the allow lists add the outer-approved T8 policy
(`2026-10-02-u10-1-t8-rerun/approved-static-policy-current.json`: U11i's J10e split and 14 adds; T8 stubs'
phonenumbers and SSLParametersImpl). That is exactly the promotion delta U12 inherits.

| check | result |
|---|---|
| runtime U12 vs promoted 5ae3dd29, `--frozen` | rc=0: 0 dropped, 0 reshaped, 0 unlisted added (4 allowed: `OwnProviderLocal`, `WlSettingsProvider`, `WlSettingsStub`, its d8 lambda), 0 frozen broken |
| runtime U12 vs U9 238ffc14, `--frozen` + T8 policy | rc=0, same |
| stubs 3a12918a vs promoted 2f365a75, `--frozen` | rc=0 (8 allowed new android.net classes) |
| stubs 3a12918a vs U9 f3bcc9d7, `--frozen` + T8 policy | rc=0 |
| members U11i→U12 (`verify_identity.py`) | 1452 members, exactly 2 changed: `B7BindFixes.apply` and `AppSpawnXInit.preInitSettingsCache`. The label-normalised diff is the two added `invoke-static` lines (`gates/needle-diff.txt`) |
| members U11j→U12 | 1459 members, exactly 1 changed (`preInitSettingsCache`); `OwnProviderLocal` identical to U11j |
| `check_frozen.py` | 0 violations. Without `--package` it validates the registry only; frozen classes are covered by the `--frozen` rows above |
| build | built twice byte-identical; same SHA from a bare `PATH` (javac pinned to temurin-21) |
| host JVM (`test_u12.py`, 4 tests, JDK 21 and 1.8) | 3 holders injected; android_id is 16 hex digits, stable, persisted to `no_backup/westlake-android-id` and read back by a fresh process; other keys null **without** the query fallback; jar SHA |

## Prediction (written before any window; `predictions.csv`, one row per key with its U9 first-fatal hilog file:line)

**Keys whose first fatal moves: none (0 of 166).** Only two keys touch a U12 wall, and neither first fatal is on it:

| key | U9 | wall touched (U9/U10 hilog) | U9 first fatal (hilog line) | moves? |
|---|---|---|---|---|
| x | alive-white-window | `:31895 Settings: Can't get key android_id from content://settings/secure` | `:32788 … NullPointerException: null cannot be cast to non-null type android.telephony.TelephonyManager` | no: android_id becomes 16 hex digits, the TelephonyManager fatal stays |
| toutiao | dead | android.net (U10 61b :32766 `NoSuchMethodError NetworkInfo.getSubtype`, CronetInit, background); own provider PPMP (U10) | `:31733 Unable to instantiate activity …MainActivity` (← `:31265` libflipped.so dlopen in `attachBaseContext`) | no: wall 1 is native. On the promoted base, U11j's prediction stands: PPMP local, `plugin_exception_monitor` 0, t20 lit not expected |

**Upstream controls on the same walls** (102-row ledger, joined by package in `2026-10-02-upstream-copy-map`):
- Settings/ANDROID_ID: `jellyfin` (1c883ad), which draws upstream after the fix. Ours is `fd-mobile`: U9
  alive-black-window, no fatal, android_id **not read** in its hilog. Prediction: unchanged; a later window may
  show the read only once its WebView first screen exists.
- android.net members and own-provider-before-bind: **no ledger row** on either wall. Upstream's direct launch has
  a real AMS answer and different stubs, so there is no upstream draw to compare against.

**What the window must show (markers):**
- Every child process logs `[SettingsCache] IContentProvider Proxy installed in 3 holders` once (after the old
  `provider injection skipped`) and `[OWN-PROV-LOCAL] installed over` once.
- `Can't get key … from content://settings/{global,secure,system}` appears in **0** hilogs (U9: 162 keys). Every
  NameValueCache read now ends in the call fast path.
- `OH_CPBridge: query: not connected, authority=settings` drops by at least those reads. Reads outside
  NameValueCache (direct `ContentResolver` queries, observers) still reach the bridge, so it need not reach 0.
- x: no `android_id` line; first fatal still TelephonyManager.
- Lit set: unchanged (114). ① only turns null-reads that already failed into the same null, plus ANDROID_ID.

**Smoke stop rule.** The WlSettingsStub call sits outside `preInitSettingsCache`'s own try, as upstream's does.
`initChild`'s catch-all ends in `initChild failed` + `System.exit(1)`. So if the new class failed to load or verify
on the board's ART, **every** app would exit at init. The first app of the first board must show the 3-holders
line and no `initChild failed`; otherwise roll back the runtime jar at once.

## Files

- `src/adapter/activity/WlSettingsProvider.java`, `src/adapter/activity/WlSettingsStub.java`: the upstream copies.
- `compile-only/android/app/ActivityThread.java`: stand-in for the hidden `currentApplication()`; javac classpath
  only, asserted not in the dex.
- `build_u12.py`: the deterministic build (imports `build_u11j.py`'s toolchain and base).
- `gate_u12.py`, `gates/gate-u12.txt`: the seven gates. Also `gates/needle-diff.txt` and `gates/receipt-u12.json`.
- `predict_u12.py` → `predictions.csv` (166 rows: U9 first fatal file:line, wall touches, android_id read line,
  `Can't get key` / `not connected` counts, upstream control) and `evidence/settings-census.csv` (non-primed
  settings each key read).
- `evidence/u9-wall-lines.txt`: the hilog lines cited above, plus toutiao's `enableGlobal` dexdump.
- `test_u12.py`: 3 host-JVM behaviour tests plus 1 build-identity test.
