# M2 full-screen WebView: ArkWeb is on the boards and reachable from our app process; recommended route = an Android WebViewProvider backed by OH NWeb (route a), gated by one 30-minute in-process probe

#90, offline roadmap. No artifact was built. One read-only board survey ran on 5cd (OpenHarmony-6.1.0.31) under
LOCK/UNLOCK, about 5 minutes, with no writes. OH source was read on hw248. a2hlab was not used.

Cohort (`2026-10-03-white-residual-u13`, cae186de0f): the largest unowned white cluster. Each key is alive and white,
with a full-screen WebView:
- cv2-ca-vaults-randomlydie, cv2-com-degeder-yam, cv2-com-paultirk-yatoo, cv2-timur-webrtc-check, fd-tutanota;
- plus jiten (M2+M5, remote HTTPS) and caniwebview (lit control, blank browser region).

## What was wrong before

`2026-10-03-webview-provider-plan` (cx-bms) costed only route b, an Android Chromium 109 provider, at 43–66 rounds
before first content. It names `OhWebViewBridge` as "not an ArkWeb implementation" but never asked whether OH's own
engine is usable. It is:
- installed on every board;
- bind-mounted into our Android app processes;
- creatable from native code with only a Surface (OH's own unit test does exactly that).

That changes the cheapest route.

## ① Current state

**What route A's WebView is today** (identical in every process; e.g. U13 window-4 hilogs):
```
[B8-WEBVIEW] WebViewFactory.sProviderInstance seeded (type-zero stub) — getProvider() short-circuits instead of throwing
[J10e-WEBVIEW] enriched WebViewFactoryProvider seeded (forwarding ViewDelegate + concrete CookieManager + J10g extras)
[J10g-WEBVIEW] WebViewFactory.sPackageInfo seeded (com.android.webview 9999)
[B8-SVC] webviewupdate answered in process (LocalServiceBinders)
[B8-WEBVIEW] unavailable (no ASX_WEBVIEW_APK provider)
```
- The runtime JAR classes behind these lines:
  - `WebViewProviderFix` (zero-handler proxy);
  - `J10eWebView` / `J10eViewDelegate` / `J10eCookieManager` / `J10fWebSettings` / `J10gWebExtras`;
  - `WebkitSupportGlue` + `SupportLibReflectionUtil` (androidx.webkit glue);
  - `WebViewPackageFallback`, `WestlakeWebViewInstall`, `WebViewUpdateServiceAdapter`.
- Every `WebView` therefore constructs. Every call is a typed no-op: `loadUrl` does nothing and `draw` paints nothing.
  The app stays alive with a white rectangle, so the first-fatal move is 0 for every M2 key.

**Where the pages come from** (`m2_web_scan.py` → `evidence/m2-web-scan.json`). The API columns are DEX string-pool hits,
an upper bound.

| key | page source | APIs named in the DEX |
|---|---|---|
| randomlydie | Capacitor, local SPA `assets/public` (16 files) served by Capacitor's local server on `https://localhost` (the Capacitor ≥5 default) | addJavascriptInterface, shouldInterceptRequest, evaluateJavascript, WebViewAssetLoader, addWebMessageListener, postWebMessage, MessageChannel |
| yam | Capacitor, `assets/public` (5) + SafeArea plugin | the same, without WebViewAssetLoader / postWebMessage |
| yatoo | Capacitor, `assets/public` (10), `androidScheme: https` (virtual-HTTPS local origin) | the same as randomlydie |
| webrtc-check | plain local `assets/index.html` + `assets/pc1/` (4) | addJavascriptInterface, evaluateJavascript, onPermissionRequest |
| fd-tutanota | local `assets/tutanota/` (1566 html/js/css; mithril SPA, native-bridge IPC) | addJavascriptInterface, shouldInterceptRequest, evaluateJavascript, postWebMessage, MessageChannel |
| jiten (M2+M5) | no web assets; remote HTTPS after its own server dialog | loadUrl only |
| caniwebview (control) | `assets/html` (4) via WebViewAssetLoader | shouldInterceptRequest, WebViewAssetLoader, web messages |

**The common minimum** across the five keys:
- `loadUrl`, plus JavaScript / DOM-storage settings;
- `shouldInterceptRequest`, used by 4/5 (it is how Capacitor and tutanota serve local files);
- `addJavascriptInterface` and `evaluateJavascript` (5/5);
- web message ports (4/5);
- page-load callbacks.

None of them needs camera, media or a remote network for its first screen. webrtc-check's first page is explanatory
text.

## ② Renderers available on the board: OH ArkWeb (`evidence/arkweb-inventory.txt`, `app-process-reachability.txt`)

**Where it lives.** OpenHarmony-6.1.0.31 ships ArkWeb as the system app `com.ohos.arkwebcore` (`ArkWebCore.hap`, 138 MB):

| file | role | exports |
|---|---|---|
| `…/com.ohos.arkwebcore/libs/arm64/libarkweb_engine.so` (185 MB, `2b209e33…`) | the Chromium-based engine | 2877 defined / 1045 undef; NEEDED = OH NDK only (native_window, native_buffer, net_ssl, ability_runtime, ace_napi, vulkan, …) |
| `libarkweb_render.so` (`a767f4ef…`) | renderer-process entry | NEEDED libarkweb_engine.so |
| `/system/lib64/platformsdk/libarkweb_core_loader.z.so` (`ab45f985…`) | **NWebHelper / NWebAdapterHelper** inner API | 178 defined |
| `/system/lib64/ndk/libohweb.so` (`1376aa3c…`) | public NDK `OH_ArkWeb*` / `OH_NativeArkWeb*` | 104 defined (scheme handlers, cookies, JS bridge on an *existing* web; it cannot create one) |
| `libnweb_ohos_adapter.z.so`, `libohos_adapter_glue_source.z.so`, `libarkweb_core_loader_glue.z.so` | OH-side adapters the engine calls back into | — |

**Can our process get it? Yes, statically. All three preconditions hold on 5cd today:**
1. **The engine is visible inside our sandbox.** For an Android app process (appspawn-x child 20955, helloworld, uid
   20010774), `/data/storage/el1/bundle/arkwebcore` is bind-mounted from `/data/app/el1/bundle/public/com.ohos.arkwebcore`
   (its mountinfo), and `libarkweb_engine.so` is listed through `/proc/20955/root`. Every bundle, ours included, has
   this mount point.
2. **The loader is reachable by name.** `appspawn-x` runs in the `systemscence` musl section. Its default namespace has
   `/system/lib64/platformsdk` and inherits `ndk` with `allow_all_shared_libs`. So `liboh_adapter_bridge.so`'s namespace
   can `dlopen("libarkweb_core_loader.z.so")`. The loader then opens the engine from the bundle path itself.
3. **A creation API that needs only a Surface is exported**
   (`llvm-nm -D -C libarkweb_core_loader.z.so`):
   - `NWebHelper::SetBundlePath`, `NWebHelper::InitAndRun(bool)`, `NWebHelper::CreateNWeb(shared_ptr<NWebCreateInfo>)`;
   - `NWebAdapterHelper::CreateNWeb(sptr<Surface>, shared_ptr<NWebEngineInitArgsImpl>, w, h, incognito)`;
   - `NWebSurfaceAdapter::GetCreateInfo` / `OutputFrameCallback`.
   OH's own test `base/web/webview/test/unittest/common/nweb_create_window.cpp:85-104` is the complete native recipe:
   `RSSurfaceNode::Create(config)` → `GetSurface()` → `NWebAdapterHelper::CreateNWeb(surface, initArgs)` with
   `--bundle-installation-dir=/data/app/el1/bundle/public/com.ohos.arkwebcore`.
   ACE's `web_delegate.cpp:3076` (window mode) and `:3592` (surface mode) are the production callers.

**Frames can come out as CPU pixels.** `NWebCreateInfo` (`nweb.h:127-146`) is an abstract interface we can implement.
Its `GetOutputFrameCallback()` receives `Handle(const char* rgba, w, h)`. OH's own `NWebSurfaceAdapter`
(`nweb_surface_adapter.cpp`) just `memcpy`s those frames into a CPU-writable `SurfaceBuffer`. The same frames can be
copied into an Android `Bitmap` instead.

**Every API the five keys need has an NWeb counterpart** (`evidence/oh-source-excerpts.txt`, line numbers in
`ohos_interface/include/ohos_nweb/`):

| Android | NWeb |
|---|---|
| `loadUrl` / `loadDataWithBaseURL` | `Load` (nweb.h:462, 677) / `LoadWithDataAndBaseUrl` (696) |
| `evaluateJavascript` | `ExecuteJavaScript(code, callback)` (553) |
| `addJavascriptInterface` | `RegisterArkJSfunction(V2)` (717, 1412, 1593) + the JS-result callback |
| web message ports | `CreateWebMessagePorts` (783) / `PostWebMessage` (792) |
| `shouldInterceptRequest` | `NWebHandler::OnHandleInterceptRequest` (nweb_handler.h:518) |
| page load / console / permission / render-gone | `OnPageLoadEnd` (436), `OnConsoleLog` (573), `OnPermissionRequest` (665), `OnRenderExited` (681) |
| settings | `NWebPreference::PutJavaScriptEnabled` (141), `PutDomStorageEnabled` (109), … |
| touch / size / lifecycle | `OnTouchPress/Move/Release` (443-446), `Resize` (431), `OnPause/OnContinue/OnDestroy` (434-436) |

**What static reading cannot settle (the runtime gate):**
- `NWebHelper::GetWebEngine` / `GetInitArgs` (nweb_helper.cpp:655-722) need
  `AbilityRuntime::ApplicationContext::GetApplicationContext()` non-null with a BaseDir. Our Android processes never
  run OH's ability `MainThread`, so it is null today. The unit test mocks it; we would attach a real `ContextImpl`
  (bundle info + el2 base dir) before init.
- **Renderer process.** `GetWebEngine` calls `AppMgrClient::NotifyProcessDependedOnWeb`, and renderers are started
  through AppMgr → `nwebspawn`. Our processes are attached AppMgr records of real OH bundles, so this should work, but
  it is unproven. The fallback is `NWebHelper::SetRenderProcessMode` (exported) / single-process.
- **What loading the engine pulls in.** It brings OH ArkUI/ability libraries (`libace_napi`, `libability_runtime`) into
  an ART process. They are new mappings, not duplicates of anything we load (no Android WebView DSO is present), but
  their static initialisers are unknown.

## ③ Three routes

### a) Android WebView → ArkWeb (recommended)

**Pieces:**
1. **Bridge, a new native file.** It sets up ApplicationContext, sets the bundle path, calls `InitAndRun` and
   `CreateNWeb`, and pumps frames, touch and lifecycle. It is built against the OH 6.1.0.31 headers (hw248 source tree,
   read-only) with the frozen clang feef13a3, and linked to the board's loader and render-service libraries
   (platform-link copies match: hashes above).
2. **Runtime JAR.** An `android.webkit.WebViewProvider` (+ `WebSettings`, `WebViewClient`/`WebChromeClient` dispatch)
   backed by JNI → NWeb. It replaces the zero-proxy only for opt-in keys; it is not a BCP change.
3. **Composition, two options:**
   - **a1 (start here):** CPU frames from `NWebOutputFrameCallback` → `Bitmap` → `WebView.onDraw`. It needs no new
     window or RS node, so z-order and scrolling stay inside the Android View tree.
   - **a2 (later, performance):** an RS child surface node over the WebView bounds, like ACE's surface mode.
4. **Input.** `WebView.onTouchEvent` → `OnTouchPress/Move/Release`; IME and key events later.

| stage | scope | exit gate | rounds (risk 1.5) |
|---|---|---|---|
| **A0 probe** (minimal key experiment, AGENTS exception for runtime behaviour) | one test `.so` loaded in helloworld's process: ApplicationContext attach → `SetBundlePath` → `InitAndRun` → `CreateNWeb` with our own `NWebCreateInfo` (1200×1200, output-frame callback) → `LoadWithDataAndBaseUrl` (Chinese text + a JS-coloured block) | **pass:** ≥1 frame callback whose RGBA contains the JS colour, the renderer pid visible (or single-process logged), no crash. **fail class:** loader / ApplicationContext / renderer spawn / frame. 30-minute window on a free board. | 8–12 (build env + probe) |
| A1 provider core | load / settings / page callbacks / intercept / `evaluateJavascript` / JS interface / message ports, a1 composition, touch | webrtc-check + one Capacitor key draw their first page on the board (screenshot) | 25–40 |
| A2 per-app fit | Capacitor bridge (`androidBridge` + WebMessageListener feature answer), SafeArea, tutanota IPC, back key, IME | 4–5 keys show their own first screen | 10–20 |
| A3 (optional) | a2 composition, network fidelity (jiten), file chooser, permissions | — | 15–25 |

### b) A minimal Chromium provider (`2026-10-03-webview-provider-plan`)

- **Cost:** prerequisite 11–15 + stage 1 32–51 (+ stage 2 30–49) rounds.
- **Missing pieces:**
  - a frozen provenance for the transformed Chromium 109 ELF, with 13 UND symbols outside our libraries;
  - a bionic helper;
  - a single `libjnigraphics` / Canvas owner;
  - the renderer-service story.
- **Size and age:** about 100 MB of Chromium 109 per process, and it does not track OH updates.
- **Verdict:** keep it as the fallback only if A0 fails on a class that ArkWeb cannot fix (e.g. renderer spawn is
  impossible for non-ArkTS processes and single-process is refused).

### c) Offline rendering of local SPAs only (without ArkWeb)

- **Not realistic.** The local content is Ionic/Capacitor SPAs and tutanota's 1566-file mithril app. They need a full
  JS engine with DOM, CSS layout (flex/grid), fetch/XHR through the intercept, IndexedDB/localStorage and
  MessageChannel. That is a browser.
- A static HTML painter (litehtml-class) would at most show webrtc-check's explanatory text.
- Route c only makes sense as "ArkWeb headless", which is a1.

## ④ Prediction (first fatal / white)

| route | first-fatal moves | white → own content (conditional) |
|---|---|---|
| a, after A0 + A1 | 0 (all alive today) | **2**: webrtc-check, and the first Capacitor key (yatoo or randomlydie) |
| a, after A2 | 0 | **4–5**: randomlydie, yam, yatoo, webrtc-check; tutanota if its IPC bridge runs (medium). caniwebview's browser region also fills (already lit, 0 new). |
| a3 | 0 | +0 at t20: jiten's own server dialog stays on top (M5) and its content is remote |
| b (existing plan) | 0 | 4 after stage 1 (randomlydie, yam, yatoo, webrtc-check), +1 with stage 2 (the plan counts jiten; tutanota is a further local candidate it does not list) |
| c (no ArkWeb) | 0 | ≤1 (webrtc-check's static text) |

**Not counted:** keys whose WebView is not the main screen (login, help, ads). Their first fatal is elsewhere, so per
AGENTS they do not move first-fatal and are not promised.

**Recommendation:**
1. Do **A0 first**: one free-board 30-minute window, a standalone probe `.so`, no JAR, no bridge change, rolled back by
   killing the test process.
2. If A0 passes, A1 replaces route b's prerequisite + stage 1 at roughly half the rounds and with no new 100 MB
   binary.
3. If A0 fails on ApplicationContext or the renderer, the fail class decides: fix that one dependency, or fall back to
   route b.

## Rules this round sets

- **Before costing a ported engine, inventory the platform's own engine and check that our process can actually reach
  it.** Three facts settle that: the sandbox mount, the musl namespace config, and the exported inner API. Here all
  three were readable in five minutes, and none was in the previous plan.
- **OH inner C++ APIs are callable from route A** when the library sits in a namespace our bridge can see
  (`platformsdk`) and the board version matches the headers (6.1.0.31 both). Pin the board hashes in the plan, as
  above.

## Files

- `README.md`, `results.json`.
- `m2_web_scan.py` → `evidence/m2-web-scan.json` (page sources + API names).
- `evidence/arkweb-inventory.txt`: board hashes, exports/NEEDED, creation symbols, `OH_*` list.
- `evidence/app-process-reachability.txt`: sandbox mount, musl namespaces, sceneboard maps.
- `evidence/oh-source-excerpts.txt`: `NWebCreateInfo`, `GetWebEngine` / `GetInitArgs`, `CreateNWeb`, the unit-test
  recipe, `NWebSurfaceAdapter`, the ACE callers, and the API line map.
- The ArkWeb binaries (185 MB engine etc.) are not kept in the repo. Their hashes are above, and a re-pull is one
  `hdc file recv` per file.
