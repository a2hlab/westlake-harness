# Window 13 (5cd, 2026-10-03 14:19, U13 821de739cf81/124): mode 0 RESULT PASS — the OH ArkWeb engine renders in-process in an Android app, JS-set colour painted to the surface. M2 route-a render proof.

entry a352a36f (OHOS_PLATFORM-independent, unchanged) + worker ddcbdd46 (-DOHOS_PLATFORM, mode-16-capable). Clean
rollback + UNLOCK after 90 s; runtime fingerprint 821de739cf81 both ends.

## Mode 0 (local consumer surface, now ABI-correct) — PASS

The window-11 OHOS_PLATFORM fix made the local surface work; CreateNWeb then succeeded and the engine painted:

    [A0] S4 InitAndRun(1) -> 1
    [A0] S5 producer surface 0x7f0f952770 (consumer 0x7f0d5f4c20)     <- CreateSurfaceAsProducer no longer crashes
    [A0] S5 CreateNWeb -> 0x7f09d74b68                                 <- non-null (window 12 was 0)
    [A0] S6 handler set, preference=..., resized 720x720, OnContinue
    [A0] S7 LoadWithDataAndBaseUrl rc=0 ; OnPageLoadBegin ; progress 10 -> 70 -> 100
    [A0] S7 console: A0 JS ran
    [A0] S7 OnPageLoadEnd code=200
    [A0] S8 surface frame 1 720x720 stride=2880 fmt=12 centre rgba=ffffffff js_colour=0   <- initial white
    [A0] S8 surface frame 2 720x720 ... centre rgba=12ab34ff js_colour=1                  <- JS-set #12ab34 painted
    [A0] S8 surface frames 3,4,5 ... rgba=12ab34ff js_colour=1
    [A0] RESULT PASS stage=S8 callback_frames=0 callback_js=0 surface_frames=5 surface_js=4 console_js=1 load_end=1 render_exit=-1

The centre pixel of the NWeb-rendered buffer (AcquireBuffer on our consumer surface) is exactly the colour the page's
JavaScript set (#12ab34), proving the OH ArkWeb engine, loaded in-process into an Android app (appspawn-x child) via the
runtime System.load entry and nweb_ns, executed the page and rendered a correct frame. Headless: the probe renders into
its own surface (not the Activity window), so the screen stays blank; the proof is the captured pixel, not the screen.

## Mode 16 (route-a faithful bridge surface) — NOT RUN this window

run_a0.sh breaks the mode loop on the first RESULT PASS (line ~162), so mode 16 did not execute after mode 0 passed.
The bridge-surface cross-check (RS-holder / native-window -> NWeb) is still pending; run a window with MODES="16" alone
(or remove the break-on-PASS) to exercise it. The engine-render capability is already proven by mode 0.

## What this establishes for M2 route-a
- The full chain works on-board: runtime entry -> nweb_ns (both-dirs) -> libarkweb_engine load -> NWebHelper
  Init/InitAndRun -> CreateNWeb(with a real surface) -> Load -> JS exec -> rendered frame.
- The remaining route-a integration is the SURFACE SOURCE: the native backend takes the WebView view's Java Surface
  (mode 16's bridge path is the headless stand-in), not a local consumer surface.
