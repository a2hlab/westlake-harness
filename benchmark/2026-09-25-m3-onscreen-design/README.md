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

## Correcting the earlier "musl island" hand-wave

The first draft said "reuse the whole musl OH client closure behind a thin C-ABI, ~5–10 pd." That was wrong, per the outer loop, and the library evidence proves it. hanbin's `libmc` is narrow: it gives **one** self-contained musl blob (the Mali GPU driver) a musl-ABI **libc surface** *inside* a Bionic process, forwarding to Bionic underneath so there is **one** TLS/pthread/heap owner — and even that single-instance resolution hanbin marks UNVERIFIED. It is not a wrapper you can put around the OH IPC client closure.

The OH on-screen libs are not self-contained. Measured `DT_NEEDED` on the board:

- `libhilog.so` → `libsec_shared.z.so`, `libbegetutil.z.so`, **`libc.so`, `libc++.so`** — needs the OH musl libc **and** OH libc++.
- `libsurface.z.so` → **12** OH libs (`libipc_single`, `libutils`, `libdisplay_buffer_hdi_impl_v1_4`, `libhilog`, `libhitrace_meter`, `libbegetutil`, `libsec_shared`, `libbuffer_handle`, `libsync_fence`, `libconfigpolicy_util`, `libcjson`) + `libc.so` + `libc++.so`.

So even hilog pulls in OH musl libc + libc++, and surface pulls a 12-lib IPC/HDI subtree. Putting these *in* the Bionic process means a **second libc in the process** (two TLS owners both claiming `TPIDR_EL0`, two `pthread_t`/`FILE`/`errno`/heap layouts, two libc++ with incompatible `std::string`/`sptr`). That is exactly the coexistence problem the outer loop flagged.

### In-process vs out-of-process

- **Out-of-process (recommended for the full stack).** Keep the OH on-screen client stack in a **separate OH-native (musl) process** — ABI-pure, talks to WMS/RS over OH IPC natively, no coexistence at all. The Bionic app process drives it over a small IPC channel and shares frames as **dma-buf fds** (the surface producer is already fd-based; this mirrors the normal app↔RenderService split). New code = a create/flush/input protocol + buffer-fd hand-off. This sidesteps the two-libc problem entirely and is the sound M3 architecture for the whole `liboh_adapter_bridge` + OH-innerkit closure.
- **In-process, libmc-style (only for narrow C-API leaves).** A dedicated linker namespace holds the OH lib; a libmc-style shim answers the **musl libc/libc++ symbols it imports** by forwarding to Bionic (one TLS owner), and only plain C scalars/strings cross the boundary. Viable when the imported libc surface is small and no incompatible struct/thread crosses — `libhilog` (C API `HiLogPrint`, logging-only libc surface) is the plausible candidate; `libsurface` (IPC + HDI + threads + `sptr`) is where it is expected to break. **M3.crux** below measures exactly where the line is.
- **(A) rebuild OH innerkits to Bionic** stays the clean-but-blocked fallback: needs OH 6.1 RS/wm/ipc *source* (only headers present, #37) and risks the `render_service_base → lib2d_graphics → libskia` Drawing closure (hanbin §6.4).

## The shims, mapped to #39's 10 OH-facing libs

Disposition below assumes the **out-of-process** stack (so "reuse (OOP)" = runs unchanged in the musl helper process); the in-process column is what M3.crux probes.

| # | OH-facing lib (#39) | on-screen role | first-goal? | disposition |
|---|---|---|---|---|
| `liboh_adapter_bridge.so` + its OH innerkits (render_service_client/base, wm, ipc_single, surface, sync_fence…) | wm client + RSSurfaceNode + surface + ipc (the hub; CreateWindow's signature is type-coupled to RSSurfaceNode) | **yes** | **reuse (OOP)** in the musl helper (in-process: too large — 12-lib surface subtree, breaks libmc scope) |
| `libwestlake_binder` + `libbinder_ndk` | IPC to the helper / WMS SA 4606 / RS SA | **yes** | Bionic side: rebuild-to-Bionic (mechanical, ~3–5 pd); helper side: reuse (OOP) |
| `libandroid.so` | ANativeWindow, if the app produces buffers Bionic-side | maybe | rebuild (6 syms, ~1.4 pd) |
| `liboh_android_runtime.so` | EGL/hitrace/hilog support | support | reuse (OOP) / rebuild (9 syms) |
| `libhwui.so` | GLES/EGL/surface → Mali | **no (GPU)** | defer to M4+ (11 pd) |
| `libwl_opengl_jni.so` | GLES | **no (GPU)** | defer to M4+ (20 pd) |
| `liboh_hwui_shim.so` | hwui support | **no** | defer |
| **new-write** | the cross-process protocol (create/flush/input) + **dma-buf fd hand-off** (OOP), or the libmc-style musl-libc/libc++ shim (in-process, per M3.crux scope) | **yes** | **new-write** — sized only after M3.crux |

liboh_account_state / liboh_connectivity_state / liboh_permission_queries / liboh_ime_helper_capi (the other #39 OH-facing libs) are **not** on the on-screen path — excluded from M3.

## M3.crux — does in-process musl loading work at all, and how far?

Before sizing anything, run the experiment the outer loop asked for: in the **#43 Bionic process**, load a real OH musl library through a libmc-style translation layer and call one function through it. This bounds the in-process option empirically instead of guessing.

**Setup.** Add an isolated linker namespace (call it `ohmusl`) to the #43 `ld.config.txt` whose search paths are the OH platform dirs (`/system/lib64`, `/system/lib64/platformsdk`, `/system/lib64/chipset-sdk-sp`, …). The libmc-style shim is a small Bionic-side `.so` that **satisfies the musl `libc.so` / `libc++.so` symbols the OH lib imports** (forwarding to Bionic so there is a single TLS/pthread/heap owner). The OH lib's other OH `DT_NEEDED` resolve within `ohmusl` from the real platform libs.

**Step 1 — `libhilog.so` (the easy leaf).** `dlopen` it in `ohmusl`; `dlsym("HiLogPrint")`; call `HiLogPrint(3, 4, 0xD000F00, "M3crux", "%{public}s", "hello")`; confirm the line in `hilog`. Boundary is C scalars + `const char*` only. Its libc surface is small (snprintf/write/mutex/gettid/clock) — the shim is tractable.
  - **Free first data point:** #44's on-board run already does `dlopen("libhilog.so")` + `HiLogPrint` from the Bionic-built liblog.so. Whether that call reaches hilog on the board *is* M3.crux Step 1's answer for the no-shim case (does the Bionic linker even load musl libhilog and does HiLogPrint run). Read it out of the #44 run first.

**Step 2 — `libsurface.z.so` (the real test).** `dlopen` it in `ohmusl` and call one function (e.g. a producer/`GetDefaultWidth`-class getter). This drags the 12-lib subtree (ipc_single, HDI display-buffer, utils, sync_fence) and exercises `sptr`, sockets/`ioctl`, threads. Record **where it breaks**: which musl libc symbol is missing/mismatched, whether OH libc++ collides with Bionic's, whether the OH lib spins a thread whose TLS fights Bionic's `TPIDR_EL0`. That breakpoint is the datum that decides the in-process/out-of-process line for the whole stack.

**Decision rule.** If Step 1 works but Step 2 breaks on threads/`sptr`/second-libc (the expected outcome), the on-screen stack goes **out-of-process** and in-process libmc-style stays reserved for narrow C-API leaves (hilog, possibly a rendering leaf). If Step 2 somehow works cleanly, in-process becomes viable and gets sized then. PoC-0 (headless island) is dropped — M3.crux subsumes it.

## First minimal verifiable goal

**M3.crux is the first goal** (above): one OH musl function called through the translation layer in the #43 Bionic process, hilog then surface. It is small (namespace + a hilog-surface shim ≈ a few days for Step 1; Step 2 is measurement, not build) and it removes the biggest unknown before any stack-level estimate. Only after it do we size **M3.0** (`CreateWindow` + a software solid frame): out-of-process if Step 2 breaks (helper process + protocol + dma-buf fd — a fresh estimate once the protocol shape is known), or in-process if it holds. The earlier ~15–20 pd figure is **withdrawn** as unfounded until M3.crux fixes the architecture.

## Verified vs assumed
**Verified (source + on-board `DT_NEEDED` inspection):** westlake has the complete on-screen client stack (files above) and per the board it already renders on OH 6.1; the chain is `CreateWindow → RSSurfaceNode::Create → surface → FlushImplicitTransaction`. `libhilog.so` needs OH musl `libc.so`+`libc++.so` (+2 utils); `libsurface.z.so` needs a 12-lib OH subtree + musl libc/libc++ — so neither is self-contained and the in-process route means a second libc in the Bionic process. #39's 10 OH-facing libs + symbol counts.
**Assumed / to be settled by M3.crux:** whether an isolated `ohmusl` namespace + a libmc-style musl-libc/libc++ shim can load and call `libhilog` (Step 1) and how far it survives on `libsurface` (Step 2, threads/`sptr`/second-libc); the dma-buf fd hand-off for the out-of-process route. No stack-level effort number is asserted until M3.crux fixes in-process vs out-of-process. #44's on-board `dlopen(libhilog)`+`HiLogPrint` is the first data point.

## Layout
| path | what |
|---|---|
| `README.md` | this one-page M3 design |
