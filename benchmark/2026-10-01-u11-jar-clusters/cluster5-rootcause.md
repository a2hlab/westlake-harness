# Cluster 5 root cause — why stock installContentProviders does not publish the app's providers

Outer asked: we call the original `handleBindApplication`, and AOSP 14 runs `installContentProviders` inside it
(before `Application.onCreate`) when `!restrictedBackupMode && !isEmpty(providers)` — why didn't it publish?

## Established offline (evidence)

| # | fact | evidence |
|---|---|---|
| 1 | **Both guards are satisfied.** `AppSchedulerBridge` sets `data.providers` non-empty (`setField(data,"providers",realProviders)`, `[B43-BIND] providers populated: N`) and `data.restrictedBackupMode=false` **before** calling `handleBindApplication`. `handleBindApplication` does **not** rebuild `data.providers`. | AppSchedulerBridge.java:194,222; AOSP ActivityThread.java 6700–6983 has no `.providers =` reassignment |
| 2 | **`handleBindApplication` truly completed (no swallow).** `[B43-BIND] handleBindApplication returned OK` is printed **only** on a normal return of `handleBind.invoke(...)` (no try/catch around it that prints OK on failure). So `installProvider` did **not** throw the `RuntimeException("Unable to get provider ...")`. | AppSchedulerBridge.java (invoke; println right after); no `Unable to get provider` in hilog |
| 3 | **No `installProvider` failure log.** AOSP `installProvider` logs `Slog.w("Unable to get context for package …")` (c==null) or `Slog.e("Failed to instantiate class …")` (provider==null). Slog reaches the hilog (e.g. `C00f00/SystemServiceRegistry: No service published`). **Neither appears** for notepad. | AOSP ActivityThread.java:7726/7756; notepad hilog |
| 4 | **Our publish path works and is routed.** `ActivityManagerAdapter.publishContentProviders` is implemented and registers to `ContentProviderRegistry` (`logBridged(...); ContentProviderRegistry.getInstance().publishProviders(providers)`), and `ActivityManager.getService()` resolves to our adapter via `ActivityManager.IActivityManagerSingleton.mInstance` (AppSpawnXInit installActivityManagerStub). | ActivityManagerAdapter.java:1182–1186; AppSpawnXInit.java:1164–1172 |
| 5 | **But the providers were never published.** No `[BRIDGED] publishContentProviders` line in notepad's hilog, and the query falls to the OH bridge: `query: not connected, authority=com.nononsenseapps.notepad.MyContentAuthority` → null Cursor → `moveToFirst()` NPE. So `ContentProviderRegistry` has no local provider for the authority. | notepad hilog 36855+ |

## The remaining gap (needs one on-board datum)

(1)–(5) narrow it to: inside stock `installContentProviders`, **either** it produced an **empty `results`** (every
`installProvider` returned null **without** hitting the two logged failure paths — i.e. via the
`catch { if (!mInstrumentation.onException(null,e)) throw; return null; }` branch with `onException` returning
true), **or** `installContentProviders` was reached but `publishContentProviders(getApplicationThread(), results)`
did not land providers in our adapter. Both remaining branches are **silent offline**.

## U11d is the minimal experiment that pins it

U11d's `AppContentProviders.install()` instantiates the **same** providers by the **same** calls stock
`installProvider` uses (`cl.loadClass(name).getDeclaredConstructor().newInstance()` → `attachInfo(appContext,info)`
→ `getIContentProvider()`) and publishes them to `ContentProviderRegistry` directly, with per-provider logging.
Running U11d on board reads out the gap **for free**:

- `[B8-PROV-INSTALL] installed N/total app providers` with **N>0** and **notepad lights** ⇒ instantiation +
  attachInfo + publish all work; stock's failure is therefore in the stock path's `results`/publish, not in
  instantiation. Then the order-preserving fix is a stock-side one (see below) and is a refinement, not a blocker.
- `[B8-PROV-INSTALL] provider <class> (authority …) not installed: <ex>` (N small / notepad still dark) ⇒ that
  exception is the shared root — the same thing that makes stock `installProvider` return null via its catch.
  Fix that exception's cause (e.g. a classloader / attachInfo dependency) and both paths work.

So **run U11d first**; its hilog is the probe. No extra offline guessing.

## Order-preserving fix (pursue only if the probe says it's needed)

If an app queries its own provider inside `Application.onCreate` (none observed yet), U11d's post-bind timing
misses it. To restore AOSP order (providers before `Application.onCreate`) we must make stock
`installContentProviders` publish **inside** `handleBindApplication`. Given guards (1) are already satisfied, the
candidate is whatever makes stock `installProvider` return null silently — most likely its context/LoadedApk
resolution (`peekPackageInfo(ai.packageName)` / `getAppFactory().instantiateProvider`) or
`mInstrumentation.onException` returning true. The U11d probe identifies which; the fix then pre-seeds that
input before `handleBindApplication` (e.g. ensure `peekPackageInfo(appPkg)` is non-null, or the provider
`info.applicationInfo.packageName` matches the app) so stock's own `installContentProviders` succeeds and the
post-bind `AppContentProviders` becomes a no-op fallback.

**Recommendation:** keep U11d (working pragmatic fix for the common Activity-query case) and treat its first
on-board run as the probe; decide the order-preserving stock fix from that run, not from more offline analysis.
