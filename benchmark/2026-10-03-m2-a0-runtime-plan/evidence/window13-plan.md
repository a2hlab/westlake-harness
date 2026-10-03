# Window 13 plan: give NWeb the Activity's real surface from the bridge (route-a faithful) — not the probe's own IConsumerSurface

Static decision after window 12 (`CreateNWeb -> 0`, "get native window from surface failed"). The outer's three options,
resolved:

## ① OH `nweb_impl.cc:1600-1640` — not readable, reasoned from the contract
`nweb_impl.cc` is in the **closed ArkWeb/chromium engine** (com.ohos.arkwebcore prebuilt), not in the OH610 LTS tree, so
the exact lines can't be read. But the log is unambiguous: `nweb_impl.cc:1621 Init web engine failed, get native window
from surface failed` after `CreateNWeb NWebId:1, size 720*720, enhance surface 0`. So the engine takes
`NWebCreateInfo::GetProducerSurface()` (a `void*` → `sptr<OHOS::Surface>` producer), does `CreateNativeWindowFromSurface`
on it, and **requires a non-null, valid producer surface**. A null surface (callback-only) fails here; the
`OutputFrameCallback` does not substitute for the window. This matches how OH's own ACE `WebPattern` fills CreateInfo:
from an **`RSSurfaceNode`** via `GetSurface()`.

## ② Window-11 crash is NOT a usage error
The probe's sequence is the documented one and matches every OH example
(`graphic_2d/.../pixel_map_from_surface_test.cpp`, `rs_screen_property.cpp`, …):
`IConsumerSurface::Create(name)` → `GetProducer()` → `Surface::CreateSurfaceAsProducer(producer)`. So the SIGSEGV in
`ProducerSurface`'s ctor (`RefBase::IncStrongRef` on a bad pointer) is an ABI/linkage/context problem of building a
**local** surface in the appspawn-x child, not a wrong call order. Chasing it is a rabbit hole — and a locally-created
consumer surface is not the route-a path anyway (route a renders into the real view window).

## ③ CHOSEN — route-a faithful: the Activity window surface from the bridge
The bridge already publishes the Activity's window to env-shared pointers (same process) and the M1 session-slots patch
extended it (`2026-10-02-u14-bridge-r1r3`):
- `WESTLAKE_NATIVE_WINDOW_PTR_V1` (single-slot) / `WESTLAKE_NATIVE_WINDOW_PTR_V2_<id>` (per-session) — the OHNativeWindow;
- `WESTLAKE_RS_SURFACE_NODE_HOLDER_PTR_V2_<id>` — the `RSSurfaceNode` holder;
- reader entry points `getOhNativeWindow(sessionId)` / `oh_wm_get_native_window` / `getRSSurfaceNode`.

**Window 13:** the probe, after the Activity window session exists (seen in windows 11/12: `OH_WindowMgrClient
createSession … 1200x1920`), reads the bridge's published `RSSurfaceNode` (V2 holder, V1 native-window as fallback),
calls `RSSurfaceNode::GetSurface()` → `sptr<OHOS::Surface>` producer, and returns that from
`NWebCreateInfo::GetProducerSurface()` — exactly what OH's ACE WebPattern passes NWeb. No local `IConsumerSurface`, so
window-11's crash is gone; a real native window, so window-12's `nweb_impl.cc:1621` is satisfied.

Implementation notes for the probe change (then request window 13, scheduling rules as usual):
- Resolve the pointer from the env var (the bridge `setenv`s pointer text), cast to `RSSurfaceNode*` (V2 holder) or the
  OHNativeWindow (V1); prefer the RS node to match ACE.
- **Timing:** `a0_probe_start` posts `Run` immediately, but the window target is published only when the Activity window
  session is created (~shortly after launch). Gate CreateNWeb on the env var being present (poll/delay on the probe's
  EventRunner, e.g. retry for a few seconds) so the surface exists before `CreateNWeb`.
- Keep `SetRenderProcessMode(SINGLE)` and the `OutputFrameCallback` (frames still arrive via the callback for the
  pixel/js-colour check) **in addition to** the real surface.

## Native backend (route a) — surface source fixed by this decision
`nativeCreateNWeb(int w, int h, Object surface)`: the Java `Surface` is the WebView view's surface. Native side:
`ANativeWindow_fromSurface(env, surface)` → (runtime shim returns the bridge `AdapterAnw`) → unwrap with the bridge's
`oh_anw_get_oh` → the view's OH `NativeWindow`/producer surface → `NWebCreateInfo::GetProducerSurface()`. So the backend
takes the surface from Java (the real view), never building a local one — same requirement, satisfied the route-a way.
The probe's window-13 bridge-window path is the headless stand-in for exactly this.

## Status of the engine barrier
Fully cleared and stable across windows 11 & 12: entry a352a36f loads via the runtime, `nweb_ns` both-dirs resolves
`libarkweb_engine.so`, `Init→1`, `InitAndRun→1`, `InitWebEngine: succeed to init web engine`. The only remaining wall is
the surface, which window 13 supplies the faithful way.
