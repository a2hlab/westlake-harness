# child9544 WebView first-fatal: local read-only finding

Treating this stack as a missing `IWebViewUpdateService` implementation would be incorrect. The real service is present in the retained RouteB adapter JAR and executed in child9544. The remaining question is the capability hold/release and service-getter path at the fatal instant, not whether a provider service must be invented.

## Evidence

- `evidence/child9544-excerpts.txt`: line 304 releases the Java WebView support hold; line 436 executes the real `waitForAndGetProvider` for `com.android.webview`; lines 437–440 republish the service cache but report `feature=held-unsupported`. The first fatal is line 1049, after platform-support JNI loading. There are zero `feature=published` records. An earlier successful lookup does not prove the later getter returned the same object.
- `evidence/deployed-class-inventory.json` and `deployed-service.smali.txt`: the retained `fw/adapter-runtime-bcp.jar`, SHA `ea5d8b277f1207c928d289196876ad69505d73ab586815daccbda7080169523e`, contains `WebViewUpdateServiceAdapter`, `OHServiceManager`, and `AppSpawnXInit`. Its service returns sideloaded provider metadata, not the RouteA empty-provider substitute.
- `evidence/deployed-WebViewFactory.smali.txt`: retained `fw/framework.jar`, SHA `4a3d1688fe3753e7ac5164d2404cca3be1217c698ad7ce8383238713be44b0dd`, contains the capability-gated getter and the unchecked `Stub.asInterface` lookup. Either boundary needs actual state evidence before assigning the null result.
- `evidence/deployed-AppSchedulerBridge.smali.txt`: the adapter has `releaseWebViewSupportHold` and the explicit post-bind checkpoint. This prevents claiming that all release wiring was omitted.

These JAR identities come from the retained 61b runtime archive and are consistent with the same-child class/log behavior. This lane did not sample fresh current-boot JAR hashes. The archive is evidence of the retained artifact, not an independent current-board identity check.

## Existing implementation and verification limits

Local donor root: `$WORKSPACES/vm-copies/westlake-current/framework/`; hashes are in `evidence/source-pins.json`.

| Implementation | Exact boundary |
| --- | --- |
| `core/java/WebViewUpdateServiceAdapter.java:28–39` | Real sideloaded provider response |
| `activity/jni/activity_task_manager_adapter.cpp:155,216,425,1494` | Published-feature latch; cache/publish split; historical direct provider-class fallback; separate prime/publish entry points |
| `core/jni/adapter_bridge.cpp:355,403,438–466` | Application-ready watcher primes only the cache; explicit post-bind checkpoint publishes the feature |
| `activity/java/AppSchedulerBridge.java:633` | Source donor sends the native post-bind checkpoint after `handleBindApplication` returns |

The recorded adapter donor path commit is `e2b0bf669ca33459c74618883614f4c603fbccbb`. Historical candidate05 verification is described in `benchmark/2026-10-03-webview-provider-plan/evidence/source-lines.json`, quoting `OH-FIVE-GAP-REPAIR-2026-09-04.md` at `f82d1f1a9d0a8760de6bb215f8d130cbb81b21a4`: capability-publication repair, Toutiao search text/images/scroll, and independent WebView controls. Its original screenshots/logs/manifest are absent from this local snapshot. This is a historical method donor, not proof that current RouteB native bytes match or that this failure is fixed.

## Minimal recommendation

Keep the sealed assembly unchanged. First reconcile the actual RouteB Java release, native watcher and post-bind publication with the retained artifact identities. A later authorized targeted observation should distinguish `sWebViewSupported`, public binder readback and `Stub.asInterface` at the failed lookup. Do not turn the cache-only watcher into unconditional feature publication: its source explicitly avoids starting Chromium during the cold bind path.

The fatal-instant feature value and the exact null-producing boundary remain unproved. This finding concerns only child9544's first fatal and does not establish the cause of the earlier random SIG11 failures. No board commands, remote access, downloads or builds were performed; frozen assembly files were unchanged.

`closure-missing.json` is a separate local archive comparison. Its historical donor-only entries are not approved deployment inputs and do not establish the WebView fatal cause. `results.json` is the machine-readable conclusion; `documentation.json` records suggested follow-up documentation without changing the root digest or layout.
