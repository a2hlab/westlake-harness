# M2 route-a: where the Java side gets the NWeb surface — decision = Option A (a SurfaceView in the WebView)

#90, offline, static. cc-t3 window14 found the bridge's Activity-window surface is the shared content node and NWeb
painting into it doesn't reach the screen; WebView itself isn't a SurfaceView. This decides where
`NativeNWebBackend.create(...)`'s `surface` comes from. **Decision: Option A** — the provider hosts an
`android.view.SurfaceView` inside the WebView (a ViewGroup) and feeds NWeb that holder's Surface. Reasons below; Java
draft + a passing offline unit test (12/12) included; Option B (native mode-32 child node) is the documented fallback.

## ① Static findings — why a SurfaceView, and what its Surface resolves to
Our own runtime already encodes the rule (`oh_window_manager_client.cpp:1455-1498`, getOhNativeWindow PRESENT-FIX):
> *"RS does NOT composite a bare APP_WINDOW_NODE's own GetSurface() consumer buffer … hwui's Activity decor reached the
> producer queue but was never acquired/composited … display stayed on launcher. A SELF-DRAWING child node
> (isWindow=false) AddChild'd under the WMS-registered window node IS GPU-composited into the parent window layer
> (mirrors ArkUI XComponent … and the SurfaceView path `oh_rs_get_child_surface_window`)."*

That **is** window14's finding: the bridge's Activity-window surface (bare window node / `AdapterActivityContent`-as-window)
is not composited. The fix the runtime already ships: a **self-drawing child RSSurfaceNode AddChild'd to the window** —
which is exactly what a SurfaceView gets:
- **SurfaceView → self-drawing child node.** `android_graphics_compat_shim.cpp:449` `[STAGE2-SURFACEVIEW]` resolves a
  "dedicated, RS-composited child surface for a SurfaceView (so its EGL producer has a live consumer instead of
  colliding with the main window's APP_WINDOW_NODE producer)" → `oh_rs_get_child_surface_window`
  (`oh_window_manager_client.cpp:1221`): `RSSurfaceNode::Create("AdapterSurfaceView", isWindow=false)`,
  `SetHardwareEnabled(true, XCOM)`, `parent->AddChild(child,-1)`, hands back `child->GetSurface()`. AOSP
  `android.view.SurfaceView` reaches it through `BLASTBufferQueue.nativeUpdate` (our `BBQ_nativeUpdate (JJJJI)V`) /
  `SurfaceControl`.
- **`oh_anw_get_oh` resolves to that child node's producer.** The holder's `Surface` → `ANativeWindow_fromSurface` →
  an `AdapterAnw` (magic `ANW1`) → `oh_anw_get_oh` unwraps to the bare `OHNativeWindow` of the producer it was built
  from = the `AdapterSurfaceView` child node's `GetSurface()` (self-drawing, composited) — **not** the bare window node.
- **Flutter corroboration.** U14 `localsend` (FlutterSurfaceView, an `android.view.SurfaceView` subclass) hilog:
  `AdapterSurfaceView` ×25, `AdapterActivityContent` ×26, `SurfaceView` ×6, `createSession androidType=1`. U14's Flutter
  EGL fix produced `EGLSurface=<non-zero>` on that path (`benchmark/2026-10-03-u14-predicted-vs-actual`: localsend moved
  past `eglCreateWindowSurface`) — i.e. a SurfaceView holder's Surface is a working, composited producer.
- `android.webkit.WebView` extends `AbsoluteLayout` (a ViewGroup), so it can host a child SurfaceView directly.

## ② Decision: Option A (SurfaceView in the WebView), not Option B
**A** reuses the proven, already-shipping composited-child path (`AdapterSurfaceView`) — the same self-drawing-child
mechanism (`AdapterActivityContent`) that makes *every lit View-system app* reach the screen — and lets the **View
framework sync the SurfaceView's position/size/visibility/z-order for free**. The native backend's `SurfaceFromJava`
(benchmark/2026-10-03-m2-route-a-native) already consumes `holder.getSurface()` unchanged. It is a **Java-only** change
in the provider, no native/mode-32 dependency.

**B** (native builds its own child RSSurfaceNode, Java syncs geometry/visibility/z-order via JNI, cc-t3 mode 32) would
duplicate the `AdapterSurfaceView` mechanism and put the geometry/visibility/z-order sync on us to do by hand — exactly
what a real SurfaceView does automatically. B is the right fallback only if A's SurfaceView proves unreliable on board
(see risks). So: **A primary; B fallback.**

Risks of A (and mitigations, all in the draft):
- *EGL/surface timing* — the M3 cluster's GLSurfaceView `IllegalArgumentException "… valid Surface"` came from touching
  the surface before `surfaceCreated`. Mitigation: `NWebSurfaceLifecycle` creates NWeb **only** in `surfaceCreated`
  (unit-tested: nothing before the surface).
- *z-order* — SurfaceView defaults to a layer behind the window punching a hole. The WebView paints nothing in route-a,
  so the SurfaceView *is* the content; `setZOrderMediaOverlay(true)` keeps it above the empty WebView, below true
  overlays. (If an app draws View content over the WebView, revisit — rare for a full-screen WebView.)

## ③ Option A — Java change draft + unit test
- `src/org/westlake/webview/NWebSurfaceLifecycle.java` — the **android-free, unit-tested** core: decides when to
  `create`/`drawFrame`(resize)/`destroy` the NWeb handle from the SurfaceHolder events, defers `loadUrl`/settings until
  the surface exists, recreates on a new surface.
- `src/org/westlake/webview/OhNWebSurfaceHost.java` — the thin Android glue (framework-classpath): adds a match-parent
  `SurfaceView` to the WebView ViewGroup, `setZOrderMediaOverlay(true)`, and forwards its `SurfaceHolder.Callback` to
  the lifecycle. **Wiring:** `OhNWebProvider` constructs one `OhNWebSurfaceHost(backend, sink, bundlePath)` and calls
  `attach(theWebView)` from WebView init / `onAttachedToWindow`; its `WebViewProvider.loadUrl/onPause/onResume/...`
  forward to `host.lifecycle()`.
- `test/NWebSurfaceLifecycleTest.java` — offline, no Android/native, recording `NWebBackend` mock. **12/12 PASS**
  (`evidence/test-run.log`): no create before the surface; `onSurfaceReady` creates with the holder's Surface + extent
  then applies the deferred url + settings; idempotent re-ready; `surfaceChanged`→drawFrame; `surfaceLost`→destroy;
  re-ready→recreate on the new surface.

### Option B fallback — the sync interface for cc-t3's mode 32 (if A loses on board)
If the native side owns the child RSSurfaceNode (mode 32), the Java side must drive it. Minimal JNI the provider would
call (handed to cc-t3 to align with mode 32):
```
long nativeCreateChildSurface(int sessionId, int width, int height)        // -> child RSSurfaceNode, returns its surface handle for CreateNWeb
void nativeSetChildGeometry(long child, int x, int y, int width, int height)  // from WebView.getLocationInWindow()+onLayout
void nativeSetChildVisible(long child, boolean visible)                     // from onVisibilityChanged / onWindowVisibilityChanged
void nativeSetChildZOrder(long child, int z)                               // from the view hierarchy order
void nativeDestroyChildSurface(long child)                                 // from onDetachedFromWindow
```
This is strictly more code than A (the View framework already computes all four). Not implemented here.

## Files
- `src/org/westlake/webview/{NWebSurfaceLifecycle,OhNWebSurfaceHost}.java`, `test/NWebSurfaceLifecycleTest.java`.
- `evidence/node-tree-findings.txt` (the static source quotes + Flutter corroboration), `evidence/compile.log`,
  `evidence/test-run.log`.
- `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline, static source reading + an offline unit test; no board, no deploy, no push. The runtime SurfaceView plumbing
(`oh_rs_get_child_surface_window` / `[STAGE2-SURFACEVIEW]` / BBQ) is read-only cc-t3/framework territory. The on-board
confirmation (NWeb into a SurfaceView holder's Surface reaches the screen) rides cc-t3's A0/mode validation window; if
it changes the surface conclusion, the backend's `SurfaceFromJava` + this host adjust together.
