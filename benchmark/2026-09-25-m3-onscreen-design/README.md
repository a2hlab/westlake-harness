# M3 design — getting on-screen inside a Bionic process (one page)

**Board entry:** M3 design task (`.octos/OUTER_LOOP_REVIEW.md`, outer-loop派单 2026-09-25) · VM-side only, no board.
**Question:** to put a frame on the DAYU600 screen from a **Bionic** app process (the #41-proven `normal_hap` + #39 Bionic linker/libc, #43-proven ART), which OH-facing shims are the minimum, and which are *reuse / rebuild-to-Bionic / new-write*? What is the first minimal verifiable goal and its cost?

## The key fact that reframes M3

westlake **already has the full 64-bit on-screen client stack, and it already puts apps on screen on stock OH 6.1** (musl build). So M3 is **not** "port hanbin's M4 from scratch" — hanbin's M4 chain (`CreateWindow → RSSurfaceNode → surface commit → RS composite`) is already implemented here:

| hanbin M4 piece | westlake file (verified present, on-screen on OH 6.1) |
|---|---|
| `IWindowManager` client: CreateWindow/AddWindow/RequestFocus/RaiseToAppTop | `framework/window/jni/oh_window_manager_client.cpp` (`rs_interfaces.h`, `RSSurfaceNode::Create`, `wl_window_nodes` map) |
| `WindowCallbackAdapter extends WindowStub` (28 IWindow callbacks) | `framework/window/jni/window_callback_adapter.cpp` |
| RSSurfaceNode + surface buffer + `RSTransaction::FlushImplicitTransaction` | `framework/surface/jni/oh_surface_bridge.cpp` (`createSurface → getSurface → notifyDrawingCompleted → FlushImplicitTransaction`), `oh_graphic_buffer_producer.cpp`, `oh_canvas_renderer.cpp` |
| ANativeWindow / SurfaceControl | `window/jni/oh_anativewindow_shim.cpp`, `android-runtime/src/android_view_SurfaceControl.cpp` |

These compile into **`liboh_adapter_bridge.so`** (+ `libhwui`, `libwl_opengl_jni` for GPU). So the on-screen problem in the Bionic direction is: **run this existing, working stack from a Bionic process** — i.e. cross the musl↔Bionic boundary — not re-author it.

## Minimum on-screen path (first goal)

`CreateWindow` (wm SA 4606 client) → `RSSurfaceNode::Create` → fetch the WMS-registered surface (`oh_surface_bridge`) → **software-fill one solid color into the GraphicBuffer** → `RSTransaction::FlushImplicitTransaction` → RenderService composites → pixels on screen. hanbin M4 explicitly allows **software rendering** for the HelloWorld frame, so the GPU stack (Mali) is out of scope for the first goal.

## The shims, mapped to #39's 10 OH-facing libs

Two strategies for the musl↔Bionic boundary (from #37/#41): **(A) rebuild the OH innerkit client subset against Bionic** — clean but needs OH 6.1 RS/wm/ipc *source* (only headers are present, #37), and the RS command layer risks dragging in the `render_service_base → lib2d_graphics → libskia` Drawing closure (hanbin §6.4, whole-lib closure 135); **(B) a musl island** — keep the already-working musl-built OH-facing libs behind a thin C-ABI forwarding boundary, exactly the pattern #37 planned for the Mali blob (`libmc`). **Recommended: (B) first**, because the stack already works in musl; wrapping it costs a boundary, not a reimplementation.

| # | OH-facing lib (#39) | on-screen role | first-goal? | disposition |
|---|---|---|---|---|
| `liboh_adapter_bridge.so` | wm client + RSSurfaceNode + surface + ipc (the hub; CreateWindow's signature is type-coupled to RSSurfaceNode) | **yes** | **(B) reuse in musl island** (else (A) rebuild the on-screen subset ~138/384 syms ≈ 20–25 pd, needs OH src) |
| `libwestlake_binder` + `libbinder_ndk` | IPC transport to WMS SA 4606 / RS SA | **yes** | rebuild-to-Bionic (mechanical set, ~3–5 pd) — or inside the island |
| `libandroid.so` | ANativeWindow (if the SW path uses it) | maybe | rebuild (6 syms, ~1.4 pd) |
| `liboh_android_runtime.so` | EGL/hitrace/hilog support | support | rebuild (9 syms, ~1.4 pd) |
| `libhwui.so` | GLES/EGL/surface → Mali | **no (GPU)** | defer to M4+ (11 pd) |
| `libwl_opengl_jni.so` | GLES | **no (GPU)** | defer to M4+ (20 pd) |
| `liboh_hwui_shim.so` | hwui support | **no** | defer |
| **new-write** | the island C-ABI boundary: `create_window / get_surface / fill_and_flush / window_callbacks`, plus the **GraphicBuffer fd hand-off** across musl↔Bionic | **yes** | **new-write, small (~5–10 pd)** — the one genuinely new piece; the buffer-handle/fd marshalling is the main risk |

liboh_account_state / liboh_connectivity_state / liboh_permission_queries / liboh_ime_helper_capi (the other #39 OH-facing libs) are **not** on the on-screen path — excluded from M3.

## First minimal verifiable goal (M3.0) and cost

**M3.0:** from a Bionic process on the app path (`normal_hap`, #41), drive westlake's existing `oh_window_manager_client::CreateWindow` + `oh_surface_bridge` get-surface + a **software solid-color fill** + `FlushImplicitTransaction`, and confirm the color on the DAYU600 screen (screencap/photo). Deliberately native-only — no ART/APK — to isolate the wm+RS+surface Bionic-client boundary from app complexity.

**Cost to M3.0 via the recommended musl-island route:** island boundary (new-write) ~5–10 pd + binder/ANativeWindow wiring ~4–5 pd + bring-up/debug of the GraphicBuffer hand-off ~5–8 pd ≈ **~15–20 person-days**. This is a *slice* of #39's 98 pd (the on-screen portion behind an island), not additive. The rebuild-to-Bionic route (A) is ~30–35 pd **and** blocked on OH 6.1 RS/wm/ipc source + the Drawing/skia closure risk, so it is the fallback, not the first step.

**Biggest unknown (same as hanbin §6.4, restated for the island):** whether the GraphicBuffer / surface producer handle can be handed from the musl island to (or shared with) the Bionic side cleanly — the buffer is an fd + metadata, so an fd-passing C-ABI should work, but the surface producer object ownership needs a PoC. Recommend a **PoC-0** first: in the musl island alone (no Bionic), CreateWindow + software solid frame from a standalone musl binary under `source_app_namespace` in `normal_hap`, to confirm the on-screen path works headless before adding the Bionic boundary.

## Verified vs assumed
**Verified (source inspection):** westlake has the complete on-screen client stack (files above) and per the board it already renders on OH 6.1; the chain is `CreateWindow → RSSurfaceNode::Create → surface → FlushImplicitTransaction`. #39's 10 OH-facing libs + symbol/effort numbers.
**Assumed / to PoC:** the musl-island fd/surface hand-off; that a software solid fill needs no Drawing/skia; the on-screen subset of adapter_bridge's 384 syms (~138) if route (A) is taken. All flagged for a PoC-0 before committing the M3 build.

## Layout
| path | what |
|---|---|
| `README.md` | this one-page M3 design |
