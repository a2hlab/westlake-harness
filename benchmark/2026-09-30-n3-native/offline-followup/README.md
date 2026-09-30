# Offline continuation after the USB disconnect

A native ownership label is not proof of a native defect. The unchanged N3
candidate already addresses five of the eight N3 clusters. This continuation
covers all **20 primary keys** in cx-bms's corrected addendum; `results.json`
lists expected next actions, including secondary overlaps. No board command or
candidate mutation was made. The 8a7880fa export stays immutable and unverified
on device.

## Tutanota: feature gate precedes native loading

The real framework JAR SHA `3e106350` has two UnsupportedOperationException paths
in WebViewFactory.getProvider: privileged UID (with a message), and unsupported
WebView feature (no message). U2 and U3 fail on the latter. The exact DEX shows
`isWebViewSupported()` caches PackageManager.hasSystemFeature("android.software.webview").
The deployed oh-adapter-framework PackageManagerAdapter lists only six hardware
features, returning false by default. J3's projection proxy contains no feature
special case. Thus a non-null `webviewupdate` Binder is insufficient: U3 logs the
local Binder response before the same no-message exception.

`inspect_webview.py` reads the actual three JARs on Mac with the existing inputs
venv/androguard, records SHA and complete selected method instructions. It does not
modify bytecode. `webview-dex.json` is reproducible evidence, not a binary patch.

The full donor exists locally at vm-copies/westlake-current, clean git HEAD
`532633da63b770d3d459c74683db6d7a1f82a022`. Four unchanged files under `upstream/`
are byte-verified with git show; `sources.json` pins their paths and SHA:

1. PackageManagerAdapter.getSideloadedWebViewPackageInfo: explicit existing APK,
   provider application class, version, nativeLibraryDir and WebViewLibrary metadata;
   feature available only when that provider exists.
2. WebViewUpdateServiceAdapter: real selected provider response, no generic null
   service response; matches the package-manager representation.
3. OHServiceManager: route webviewupdate to that adapter only when available.
4. activity_task_manager_adapter.cpp: wl_prime_webview_update_service_impl and
   wl_set_webview_supported_cache publish/read back both the Binder and feature
   only after the configured provider is available and application is ready.

This is a coordinated Java/native/provider-input change. The N3 manifest contains
no WebView/Chromium payload declaration, and its exact-name ANL scope does not
include Tutanota. Merely returning true would expose a new missing-provider wall.
The native-only contract forbids changing JAR/APK, so no partial implementation
was compiled. Give cc-t3 the donor and coordinate a provider payload before
integration; do not silently extend the current six-plus-thirteen package scope.
The donor's hardcoded version/signatures and single-process behavior are tied to
its matched provider, not proof of arbitrary APK compatibility.

Minimum acceptance: unavailable provider remains feature=false; configured APK
hash and native closure match its declaration; package feature=true, public
ServiceManager lookup equals selected Binder, waitForAndGetProvider names the
same package; Tutanota passes getProvider with real Chromium JNI initialization,
then t20 screenshot. Preserve HW/ZZ controls. Only Tutanota is a supported immediate
prediction; do not count untested secondary WebView consumers as unlocked.

## VLC and four observation-only keys

The U2 launch transaction passes Onboarding theme 0x7f1402ec, but the failing
inflater theme is Transparent 0x7f1402f9. The existing APK graph proves the latter
has no background_default; no new evidence proves an OH resource parser defect.
Next discriminant is the actual inflater Context and its base chain before
inflate, after app setTheme, and the theme IDs on the activity vs wrapper. Compare
with the same APK on Android if scheduled; do not substitute a color or globally
replace Theme resolution. No board is currently available for that experiment.

U3 Termux successfully creates/binds TermuxService and calls finishActivity two
milliseconds later. The caller is not logged, so PTY/service/renderer blame
would be speculation. A future minimal trace at the existing Java finishActivity
boundary should record the caller stack and Activity identity without changing
return behavior. AppManager loopback slow refusal was disproved by cc-wiki;
mobile and uhabits have no proven first fatal. Their repair remains investigation,
not a fabricated native shim.

## Run locally

```sh
"$WORKSPACES/westlake-inputs/venv/bin/python" benchmark/2026-09-30-n3-native/offline-followup/inspect_webview.py
python3 benchmark/2026-09-30-n3-native/offline-followup/verify.py
```

The offline contract remains 3 pass / 1 pendingreview. The separate device
contract is **1 pass / 2 fail**, because N3 was not deployed and final device
identity cannot be read after physical disconnection. Those are missing evidence,
not candidate regressions, and are not waived.
