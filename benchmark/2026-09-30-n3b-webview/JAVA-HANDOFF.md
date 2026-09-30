# N3b ↔ J4/J5 WebView publication contract

Owner: cc-t3 for Java integration; cx-t0 for the single-runtime N3b candidate.
This is **not** permission to advertise WebView merely because a Binder stub exists.
The unchanged donor is Westlake `532633da63b770d3d459c74683db6d7a1f82a022`.
Whole donor snapshots are in `../2026-09-30-n3-native/offline-followup/upstream/`.

## Exact Java cooperation

Add class `adapter.core.WestlakeWebViewInstall` in the runtime JAR, owning:

```java
private static native boolean nativePrime();
private static native boolean nativePublishAfterBind();
```

Symbols exported by `/system/android/lib64/liboh_android_runtime.so`:
`Java_adapter_core_WestlakeWebViewInstall_nativePrime` and
`Java_adapter_core_WestlakeWebViewInstall_nativePublishAfterBind`, both `()Z`.
Use the runtime ClassLoader's existing native namespace to load that exact path
with System.load before resolving these methods. Its dependencies must inherit
the already-resident runtime/ART owners; do not load a second ART or duplicate
runtime from a private path. The class and loader owning System.load must also
own these native declarations. On a missing symbol/class/library, record unavailable
and preserve the old no-WebView behavior; do not turn success on by catching failure.

The donor checks `adapter.core.WebViewUpdateServiceAdapter.isAvailable()Z`,
`getInstance()Ladapter/core/WebViewUpdateServiceAdapter;`, exact ServiceManager cache
identity and public getService identity, then currentApplication() for publication.
It leaves WebViewFactory.sProviderInstance and all package verification untouched.

1. Copy donor PackageManagerAdapter.getSideloadedWebViewPackageInfo, metadata,
   getPackageInfo/getApplicationInfo branches and
   hasSystemFeature("android.software.webview") **conditional on the real provider**.
   J3 uses a runtime projection proxy around the boot adapter; put the equivalent
   delegation there rather than rebuilding unrelated boot classes. Check both
   callers return the same PackageInfo/identity/signature representation.
2. Copy the real WebViewUpdateServiceAdapter into the runtime JAR and route
   `webviewupdate` to it when available. Replace the generic LocalServiceBinders
   response for this service, not other service routes. Return unavailable when
   the provider APK is absent. The native candidate will not create a provider.
3. After installing the service/package adapters and selecting the provider,
   **before Application bind**, load the runtime in the owning Java ClassLoader
   and call nativePrime. This seeds/verifies the service cache and holds the
   feature false. Repeated prime calls after successful publication do not reset it.
4. **Only after handleBindApplication returns / Application.onCreate completes**,
   and before the first Activity is created, call nativePublishAfterBind on the
   application main thread. A false result is not publication; retry at a genuine
   subsequent bind checkpoint with the same prerequisites, not a timer/log hook.
   Preserve existing exceptions and normal non-WebView app behavior.

No native callback is automatically triggered by loading N3b. Until the Java
helper/call sites above ship, this is an inert capability addition. This explicit
boundary avoids rebuilding the pinned bridge or using its absent startup watcher.
The test_host.py Android classes are **test doubles**, never production JAR inputs.

## Provider payload checklist (still unfulfilled)

- Pin the actual matching WebView APK/version/signatures and arm64 Chromium library
  set; declare each SHA in a deployment package. N3/N3b contain none of these files.
- Configure ASX_WEBVIEW_APK, ASX_WEBVIEW_LIB_DIR and ASX_WEBVIEW_DATA_DIR in the child,
  or provide an equivalent explicit Java configuration using the actual declaration.
  Donor fallback paths/version/signatures are tied to its provider; do not blindly
  assert them for a different binary.
- Provider nativeLibraryDir/ClassLoader namespace requires an audited dependency
  closure. N3 ANL's scoped private package list does not include Tutanota or a
  WebView provider. Do not broaden it speculatively; a separate declared integration
  is required if the existing owner cannot expose the matched inputs.
- Create writable provider data directories for the actual app UID through the
  existing deployment/sandbox preparation path. Do not mutate the installed APK.
- Check the provider has the framework-required static create(WebViewDelegate).
  The donor comments document a legacy constructor-only provider; the Toutiao-only
  compatibility path was deliberately not copied into this generic candidate.
- Keep multi-process disabled only for a provider build that supports the matched
  single-process mode. This candidate does not create Chromium renderer services.

## Acceptance before rollout

Feature false with no real APK; public service/response/PM PackageInfo agree;
prime before bind reports held-unsupported, post-bind logs application=ready and
feature=published; real provider native load succeeds; child maps show one ART;
Tutanota t20 shows its own page, with HW/ZZ protections. Also test a late prime after
publish, invalid provider, public-cache mismatch, and missing Application.
Current host tests cover JNI/cache/order behavior only, **not Chromium or OH ART**.
No new lit app is claimed. Rollout stays blocked until this checklist is fulfilled
and the outer loop schedules board validation.

Important donor caveat: public-cache mismatch can set the feature field true
before returning false (see host-lookup-wrong.log). `feature=published` alone is
not success. Honor the boolean result and require public cache identity; do not
start a provider after false. The original helper was copied without silently
changing this failure ordering.
