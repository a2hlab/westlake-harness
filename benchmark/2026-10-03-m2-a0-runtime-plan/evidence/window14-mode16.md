# Window 14 (5cd, 2026-10-03 14:39, MODES=16): the route-a faithful SURFACE SOURCE works — bridge RSSurfaceNode -> GetSurface -> CreateNWeb non-null, page+JS loaded. On-screen shows the Activity's OWN UI (main-window contention with hwui), confirming the formal backend must use the WebView view's child surface.

entry a352a36f + worker ddcbdd46 (mode 16). Clean rollback + UNLOCK after 105 s; fingerprint 821de739cf81 both ends.

## Bridge surface obtained and CreateNWeb succeeded (route-a faithful)
    [A0] S4 InitAndRun(1) -> 1
    [A0] S5 bridge env: RS_holder=0x7f0df8bdf0 native_window=0x7f0fc1b650   <- deployed U13 bridge publishes BOTH
    [A0] S5 bridge RSSurfaceNode=0x7f0dece5e0 GetSurface=0x7f0dfacfd0       <- RS-holder PRIMARY path worked (non-virtual GetSurface)
    [A0] S5 bridge surface=0x7f0dfacfd0
    [A0] S5 CreateNWeb -> 0x7f09a20e28                                      <- non-null, with the real Activity surface
    [A0] S7 LoadWithDataAndBaseUrl rc=0 ; OnPageLoadBegin ; progress 10->70->100
    [A0] S7 console: A0 JS ran ; OnPageLoadEnd code=200
    [A0] RESULT FAIL stage=S8 surface_frames=0 callback_frames=0 console_js=1 load_end=1

## The RESULT FAIL is benign; the on-screen screenshot is the real verdict
In mode 16 the probe renders into the ACTIVITY's surface (not a local consumer), so it has no buffer to AcquireBuffer
from -> surface_frames=0 -> auto-verdict FAIL. That is a probe-instrumentation limitation, not an engine failure:
CreateNWeb succeeded with the bridge surface and the page loaded + ran JS.

t28 screenshot (evidence/window14-mode16-t28.jpeg): shows the probe Activity's OWN Java UI ("A0 ArkWeb probe" TextView
on light-gray), NOT the NWeb page (which is the green #12ab34 中文 page seen as pixels in window-13 mode 0). So NWeb
rendered into the Activity's MAIN window surface but hwui/ArkUI owns that producer and composited the Activity's own
content -> the NWeb frame did not reach the screen. This is exactly the "must not steal the main-window producer from
hwui" caveat (window13-plan.md).

## Verdict for route a
- SURFACE SOURCE validated: bridge RSSurfaceNode -> GetSurface -> NWebCreateInfo::GetProducerSurface -> CreateNWeb works
  (the probe's mode-16 code path, which cc-wiki's formal shim mirrors with the Java view Surface).
- REQUIREMENT confirmed: the formal backend must hand NWeb the WebView VIEW's OWN surface (an independent RSSurfaceNode /
  child SurfaceView), not the Activity main window — otherwise it contends with hwui and nothing shows. nativeCreateNWeb
  gets the view's Java Surface (its own child surface), so it satisfies this by construction; the probe only had the
  main window to borrow (headless), which is why mode 0 (private surface, pixel readback) is the cleaner render proof.
- Combined with window-13 mode 0 (engine paints, js_colour=1): the full route-a chain is proven — engine renders, and
  the faithful surface source connects; the open item is purely giving NWeb a non-contended child surface.

## ① connect-fail vs drew-covered — answered: DREW, not presented (shared content node)
- The bridge's getOhNativeWindow(sessionId=1354) **seeded a content child producer** named `AdapterActivityContent`
  (RS nodeid 57711475556355, surfaceNode 0x7f0dece5e0 = what GetBridgeSurface returned, uniqueId 0x34100000838) and
  connected it itself: `OH_GBProducer: [IPC] ENTER GBProducer.connect` at 14:39:04.615, BEFORE CreateNWeb (04.820).
- After CreateNWeb, NWeb's compositor initialized: `C04500/chromium root_compositor_frame_sink_impl_ext.cc:61
  rootCompositorFrameSinkImpl::SetDrawMode` (14:39:04.989), render process org.westlake.a0probe:render (pid 13515,
  isolated_render) spawned, GPU eglCreateContext OK. **No GSERROR / "already connected" / RequestBuffer failure** is
  logged for the probe's surfaces.
- So NWeb did not fail to connect — it drew, but into the Activity's **shared content node** (the same
  `AdapterActivityContent` the Activity's own ArkUI content uses), so SceneBoard presents the Activity's content
  ("A0 ArkWeb probe" TextView), not NWeb's frame. Drew-but-covered/not-presented, not connect-fail.
- Root issue: `getOhNativeWindow` gives the Activity's content node, not a node owned solely by NWeb. Fix = an
  INDEPENDENT child RSSurfaceNode (mode 32).
