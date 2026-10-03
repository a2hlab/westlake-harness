# Window 13 plan: window-11 crash ROOT-CAUSED and FIXED (missing `-DOHOS_PLATFORM` → RefBase off-by-one); run two modes — mode 0 (fixed local surface, proves the engine paints) + bridge-window mode (route-a faithful)

Supersedes the earlier draft. The window-11 SIGSEGV is now statically root-caused (outer RE) and fixed (rebuilt worker,
slot-verified). Evidence: `window13-slot-verification.txt`, `window11-s5.md`, `window12-createnweb.md`.

## Root cause (confirmed) and fix

OH610 c_utils `refbase.h` declares `virtual bool CanPromote()` under `#ifdef OHOS_PLATFORM`. The probe build
(`build_win7_hw248.sh`) passed `-D__MUSL__` but **not** `-DOHOS_PLATFORM`, so the probe's `RefBase` vtable is one slot
short of the board's. Every RefBase-derived virtual call (Surface / IConsumerSurface / IBufferProducer) was off by one
8-byte slot vs the board `libsurface.z.so` (build-id `4f752c38`, built WITH OHOS_PLATFORM). The window-11 crash was
`consumer_->GetProducer()` calling slot `0x48` (= `IsConsumer` on the board) instead of `0x50`.

**Fix:** add `-DOHOS_PLATFORM` to the build. Rebuilt worker **`1ea800e9`** (×2 byte-identical, NEEDED unchanged,
`a0_probe_start` still exported). The three CreateInfo-ctor consumer-surface calls now match the board:

| call | old (faad4897) | new (1ea800e9) | board-correct |
|---|---|---|---|
| `SetDefaultWidthAndHeight` | 0xc8 | **0xd0** | 0xd0 |
| `RegisterConsumerListener` | 0x110 | **0x118** | 0x118 |
| `GetProducer` (crash) | 0x48 | **0x50** | 0x50 |

Each shifted exactly +8 (the restored `CanPromote` slot). Entry unchanged (`a352a36f`; uses no RefBase).
`run_a0.sh` re-pinned `RT_WORKER_SHA=1ea800e9…`. (The DIGEST rule "OH inner_api native must build with `-DOHOS_PLATFORM`
or RefBase-derived virtuals are off by one slot" is landed by the outer, `ac08ce7cf6`.)

## Window 13: two modes in one window

Both on a free board cx-t0 hasn't claimed; `A0_EXPECT_FP` per board; ≤25 min; same rollback/trap; scheduling protocol
(`A0 拟用 <板>` + 2-min). Pass both modes so run_a0.sh runs them in sequence in one lock.

### Mode 0 — fixed local consumer surface (proves "the engine can paint") — READY NOW
`MODES` includes **`0`** (withSurface=true). With the fixed worker the local `IConsumerSurface::Create` →
`SetDefaultWidthAndHeight` → `RegisterConsumerListener` → `GetProducer` → `Surface::CreateSurfaceAsProducer` no longer
crashes; CreateNWeb gets a real producer surface; the `ConsumerListener::OnBufferAvailable` `AcquireBuffer`s each frame
and samples the centre pixel.
- **PASS:** `[A0] S5 CreateNWeb -> <ptr≠0>`, then `S8 surface frame … js_colour=1` (centre pixel = `#12ab34`) → `RESULT
  PASS`. This is the M2 engine-render proof (headless, the probe's own surface).
- **Fallback:** if CreateNWeb still returns 0 or no frame, capture the chromium log line and the new slot usage; the
  bridge mode below is the independent cross-check.

### Bridge-window mode — route-a faithful (needs a small probe addition before this window)
A new mode bit (proposed `16`): instead of a local surface, read the bridge's published Activity window and hand its
surface to NWeb — exactly how OH ACE WebPattern fills CreateInfo.
- Source: `getenv("WESTLAKE_RS_SURFACE_NODE_HOLDER_PTR_V2_<sessionId>")` → cast to `RSSurfaceNode*` → `GetSurface()` →
  `sptr<OHOS::Surface>` producer; fallback `WESTLAKE_NATIVE_WINDOW_PTR_V1` (OHNativeWindow) when the V2 holder is absent.
  (Publisher: bridge `oh_window_manager_client.cpp`, M1 session-slots, `2026-10-02-u14-bridge-r1r3`.)
- **Timing:** gate CreateNWeb on the env var being present — the window target is published only when the Activity
  window session is created (seen in windows 11/12: `OH_WindowMgrClient createSession … 1200x1920`). Poll on the probe's
  EventRunner for a few seconds.
- **Activity stays blank** (the probe renders NWeb into the surface but doesn't composit it to the Activity view).
  Record: `[A0] S5 CreateNWeb -> <ptr>`, the NWeb connection result, and the surface `uniqueId`.
- **PASS:** CreateNWeb ≠ 0 with the bridge surface → the route-a surface source is proven. Frames via OutputFrameCallback.
- **Must NOT steal the main-window producer from hwui:** use a surface that is not hwui's compositor producer for the
  Activity's root. For the probe, reading the RS node and calling CreateNWeb on its surface is a read of the published
  pointer; do not re-publish or re-parent. (See the formal-backend note.)

## Formal backend: which OH surface the WebView's Java Surface maps to
`nativeCreateNWeb(w, h, Object surface)`: the Java `Surface` is the **WebView view's own** surface (a child
SurfaceView/TextureView-backed surface), NOT the Activity root window. Native: `ANativeWindow_fromSurface(env, surface)`
→ the runtime shim returns the bridge `AdapterAnw` → unwrap with `oh_anw_get_oh` → the view's OH producer surface →
`NWebCreateInfo::GetProducerSurface()`. So route a renders into an **independent child surface node** for the WebView
view — it does not contend with hwui for the Activity's main-window producer. The probe's bridge-window mode is the
headless stand-in (it borrows the published Activity window only because a headless probe has no view of its own).

## Status
Engine barrier cleared and stable (windows 11/12: `Init→1`, `InitAndRun→1`, `InitWebEngine: succeed`). Surface crash
fixed (1ea800e9, slot-verified). Window 13 proves rendering via the fixed local surface and cross-checks the route-a
bridge surface. Boards currently held by cx-t0 U14 window 2 (locked 13:29:28); window 13 waits for a free board per the
scheduling protocol, avoiding cx-t0's declared boards.
