# Toutiao wall ① (own-provider lookup during attachBaseContext): root cause and a JAR candidate (U11j, not deployed)

#90, offline. U10 61b toutiao: at t+12.9s the ActivityThread is still in
`ArticleApplication.attachBaseContext`. Mira's `PluginPackageManager` cannot reach its own in-process provider
`com.ss.android.article.news.pm.PPMP`, failing 6 times exactly 0.6 s apart on six threads. Evidence:
`evidence/u10-toutiao-provider-lines.txt` (hilog with line numbers) and `evidence/mira-ppmp-chain.txt` (dexdump of
APK a1112a0c).

## What was wrong first

- **"Providers are installed too late" is not the whole story.** The stock `handleBindApplication` does install
  toutiao's providers right after `attachBaseContext`, at 23:37:51.455 on the main thread. That is the AOSP order:
  `makeApplication` → `installContentProviders` → `Application.onCreate`, with `mBoundApplication = data` at
  ActivityThread.java:6718. The failure is what our side answers **before** that install, and that the answer then
  sticks.
- **Our `getContentProvider` never answers "instantiate it yourself".** The deployed BCP
  `ContentProviderRegistry.acquireProvider` returns any authority it has not published as an **OH DataShare bridge**
  holder: `provider` is non-null, `info.name = adapter.contentprovider.ContentProviderBridge`. AOSP's AMS answers a
  provider that can run in the caller's process with `newHolder(null, true)` (provider null, `mLocal` true), and the
  client then instantiates it locally.
- **Mira's 0.6 s cost is not where the 13 s went.** The main thread was busy in app init from t+2s. Its largest
  silent stretch is 3.3 s (40.27→43.55, at app class-loader/namespace setup). Mira's first failure is at t+12.3s.
  Mira adds 0.6 s per call and, worse, makes the plugin package manager permanently unusable.

## The chain, line by line

Mira, from APK a1112a0c dexdump (`evidence/mira-ppmp-chain.txt`):

1. `PluginPackageManager.getInstance()`: while `sInstance == null`, under the class lock, makes up to 4 tries with
   `ThreadMonitor.sleepMonitor(200)` between them, calling `generatePluginPackageManager()`.
2. `generatePluginPackageManager()` builds `Uri.parse(String.format("content://%s.pm.PPMP/call", pkg))`, then
   `BinderProvider.b(context, uri)`, then `queryLocalInterface("com.bytedance.mira.pm.IPluginPackageManager")`.
3. `BinderProvider.b`: when `ToolUtils.H(app)` is true and the authority ends in `.pm.PPMP` / `.am.PAMP` /
   `.frankie`, it returns null. Otherwise it calls `context.getContentResolver().call(uri, "query_binder", null, null)`,
   then reads `bundle.getParcelable("binder")` and `BinderParcel.getBinder()`.
4. `ToolUtils.H` is true only for sub-processes (name ends with `ToolUtils.e` or `:widgetProvider`). In the main
   process the call is made.
5. Provider side: `BinderProvider.call("query_binder")` returns `Bundle{"binder": BinderParcel(a())}`. PPMP is
   declared without `android:process`, so it is in the main process.

Our side:

6. `ContentResolver.call` → stock `ActivityThread.acquireProvider` (:7293). It misses `acquireExistingProvider` and
   calls `IActivityManager.getContentProvider`, which reaches `ActivityManagerAdapter.getContentProvider` and then
   `ContentProviderRegistry.acquireProvider(auth)`. That method finds no local holder, creates a
   `ContentProviderBridge` (OH DataShare) and returns a holder with provider set to the bridge and
   `noReleaseNeeded` true.
7. hilog 32087/32088 (tid 26448, 49.865): `projected resolveContentProvider ...pm.PPMP -> PluginPackageManagerProvider`
   immediately followed by `E datashare_helper: Creator: token is nullptr`. The bridge's call returns null, so Mira
   fails and retries.
8. `ActivityThread.installProvider` treats the bridge as a remote provider and caches it under `...pm.PPMP` in
   `mProviderMap`.
9. hilog 32471 (main, 51.455): stock `installContentProviders` instantiates the real `PluginPackageManagerProvider`,
   but `installProviderAuthoritiesLocked` finds the key taken. It logs
   `Content provider ...PluginPackageManagerProvider already published as ...pm.PPMP` and keeps the bridge. The
   failures at 52.276, 52.880 and 53.481 come after the real install: the cache is poisoned for the process's life.
   (The authority is unique in the manifest, so the earlier entry can only be the step-8 bridge. This step is
   inferred from AOSP `installProviderAuthoritiesLocked` semantics plus that log line.)

Across all 290 signed hilogs (U9 166 + U10/U10.1 124), `already published as <own authority>` appears only for
toutiao. No other key asks for its own provider before bind installs it.

## Candidate: U11j = U11i + `OwnProviderLocal` (new file, one needle)

`src/OwnProviderLocal.java` wraps `ActivityManager.IActivityManagerSingleton` in the same way as the existing
`ActivityManagerBindProxy`. It answers `getContentProvider` for a provider from **this app's own bind data**
(`AppBindData.providers`) that can run here (AOSP `ContentProviderRecord.canRunHere`, :122: multiprocess or same
process name) with AOSP AMS's answer: a `ContentProviderHolder(info)` with `mLocal = true`, `noReleaseNeeded = true`
and `provider = null` (AOSP `ContentProviderHelper.getContentProviderImpl` :256/:455, from hw248
aosp-14.0.0_r1). The stock `acquireProvider` then installs the provider locally (`installProvider` → `attachInfo`
→ `onCreate`) and records it in `mProviderMap` / `mLocalProvidersByName`. The later stock `installContentProviders`
reuses that instance (`mLocalProvidersByName` hit), and U11i's `AppContentProviders` skips it ("already instantiated").
Everything else is delegated unchanged: other packages, other processes of the same app (toutiao's `:push` / `:smp`
providers still get the old answer), and any failure inside the lookup.

| check | result |
|---|---|
| build (`build_u11j.py`, base = U11i 5ae3dd29 from the round's bundle) | **`96fd4eee07906bf5…`**, built twice byte-identical; same SHA from a bare PATH (javac pinned to temurin-21) |
| `deployed_class_diff --frozen` vs U11i | rc=0: 0 dropped, 0 reshaped, 1 allowed add (`OwnProviderLocal`), 0 frozen broken |
| members vs U11i (`verify_identity.py`) | 1452 members, exactly 1 changed: `B7BindFixes.apply`, whose label-normalised diff is the single added `invoke-static OwnProviderLocal.install()` (`gates/needle-diff.txt`) |
| `check_frozen.py` | 0 violations (FZ-004 only names B7BindFixes as the class its fix was split out of; U11i already needled B7BindFixes) |
| host-JVM behaviour (`test_own_provider_local.py`, toutiao's manifest rows) | PPMP → local holder (mLocal, provider null); the Tinker p0 authority, listed as the 2nd entry of "a;b", → local; `:push` AccountSyncProvider and other packages → delegate; a 2nd `install()` adds no 2nd proxy. Passes on JDK 1.8 and 21 |

Persisted: `$WORKSPACES/westlake-inputs/generations/u11j-own-provider-local-v1/` (jar plus `receipt.json`: base,
output, source, script and toolchain hashes).

## Prediction (written before any window)

**Toutiao (only if it installs: 61b, see wall 0):**
- `[OWN-PROV-LOCAL] installed over ...` appears.
- `[OWN-PROV-LOCAL] com.ss.android.article.news.pm.PPMP -> local holder com.bytedance.mira.pm.PluginPackageManagerProvider` appears.
- `plugin_exception_monitor` lines: **0** (U10: 6).
- `already published as com.ss.android.article.news.pm.PPMP`: **0**.
- The main thread saves at least the 0.6 s it paid in attachBaseContext. Background init threads stop paying
  0.6 s per Mira call, and Mira's plugin package manager works for the rest of the process.

**t20 lit: not expected.** In U10 the bind took about 13 s of mostly app init, and the hilog stopped at t+15.8s.
The next walls of `2026-10-02-toutiao-wall3-prediction` (TTNet/Cronet native symbols, metasec) are untouched.
Best case at t20 is the MainActivity window drawing its first frame (splash). Confidence low; take t60 before
judging.

**Other apps:**
- 121 of the 166 keys declare ≥1 main-process provider (359 providers, `provider-census.csv`).
- The proxy changes the answer only for an own authority asked before the stock install puts it in
  `mProviderMap`. After the install, `acquireExistingProvider` answers first and the proxy is not consulted.
- In 290 hilogs that early own-authority lookup is seen only for toutiao. Predicted lit-set change: none.
  Regression risk is low: the old answer for that case was a DataShare bridge that fails.
- The smoke marker is `[OWN-PROV-LOCAL] installed over`, printed once by every app at bind (B7BindFixes).

## Second finding, not in U11j (needs an outer decision)

`[B8-PROV] bind providers=54`: route-A puts **all** manifest providers into `AppBindData.providers`, including the
11 toutiao declares for `:push`, `:smp`, `:plugin1` and `:stubp1-3`. The stock `installContentProviders` therefore
instantiates push and sub-process providers in the main process. AOSP's AMS hands bind only the providers that
can run in the process (`generateApplicationProvidersLocked`). The U10 `already published` lines for
`stub.p0/p1.STUB_AUTHORITY` come from this:
- `p1` is shared by two sub-process providers that were both put in main;
- `p0` is a duplicate authority already in the manifest.

The fix is to filter bind providers by `canRunHere` at the B8-PROV projection. Affected: **7 keys, 17 providers**
(toutiao 11; 5 of the 7 keys are lit, so it needs its own regression run). Not bundled, to keep U11j single-variable.

## Files

- `src/OwnProviderLocal.java`, `build_u11j.py`: the candidate and its deterministic build.
- `gates/`: `gate-u11j.txt` (class-diff, identity, frozen), `needle-diff.txt`, `receipt-u11j.json`.
- `evidence/`: `mira-ppmp-chain.txt` (dexdump excerpts), `u10-toutiao-provider-lines.txt` (hilog lines).
- `provider-census.csv`: per key, providers / main-process / other-process (aapt2 manifest dump, 166 keys).
- `predictions.csv`: per key, the expected effect of U11j and of the second finding.
- `test_own_provider_local.py`: 3 host-JVM behaviour tests plus 1 build-identity test.
