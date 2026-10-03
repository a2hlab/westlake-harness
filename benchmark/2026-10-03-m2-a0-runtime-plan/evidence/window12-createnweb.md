# Window 12 (callback-only): no crash, reached S5, but `CreateNWeb -> 0` because OH 6.1 NWeb REQUIRES a producer surface — "get native window from surface failed". Callback-only is not viable; the surface path (window-11 crash) must be fixed, and route-a must pass the Java window surface.

Window 12 (5ea, 2026-10-03 13:13, U13 `821de739cf81/124`, clean rollback + UNLOCK after 105 s). Same pinned binaries
(entry a352a36f, worker faad4897), `MODES="9"` (= 1 | 8: single render process + **no** producer surface).

## Result: mode 9 cleared the crash, exposed the real CreateNWeb requirement

No SIGSEGV this time (dropping the local producer-surface sidestepped window-11's `Surface::CreateSurfaceAsProducer`
fault). The engine inited again and CreateNWeb was reached, then failed — the chromium log gives the exact cause:

```
C04500/chromium nweb_impl.cc:1165  CreateNWeb NWebId: 1, size 720*720, enhance surface 0
C04500/chromium nweb_output_handler.cc:136  resize for emulator early failed, result = 40001000
C04500/chromium nweb_impl.cc:1621  Init web engine failed, get native window from surface failed   <-- cause
C04500/chromium nweb_impl.cc:1389  Init nweb failed, web engine init failed
C04500/chromium nweb_impl.cc:1174  CreateNWeb init nweb failed
[A0] S5 CreateNWeb -> 0
[A0] RESULT FAIL stage=S5 callback_frames=0 … render_exit=-1
```

**Finding: OH 6.1.0.31 NWeb `CreateNWeb` requires a valid producer surface.** With `GetProducerSurface()==nullptr`,
`nweb_impl.cc:1621` cannot get a native window from the (null) surface, so the render widget / web engine init fails and
CreateNWeb returns null. The `NWebOutputFrameCallback` delivers frames but does **not** replace the window surface —
callback-only is not a supported bring-up path on this engine. (This corrects the roadmap's "callback-only is viable"
assumption.)

## So windows 11 and 12 are the same requirement from two sides

- **Window 11 (mode 0, withSurface=true):** the probe builds its own `IConsumerSurface` → `GetProducer()` →
  `Surface::CreateSurfaceAsProducer(producer)` and **crashed** in `ProducerSurface`'s ctor (`RefBase::IncStrongRef` on a
  bad pointer).
- **Window 12 (mode 9, withSurface=false):** no surface → CreateNWeb refuses ("get native window from surface failed").

Either way NWeb needs a real producer surface. The engine load/init barrier is fully cleared (`Init→1`, `InitAndRun→1`,
`InitWebEngine: succeed to init web engine`); the remaining wall is **supplying a working surface**.

## Next

Two tracks, both needing a valid surface whose `OHNativeWindow` NWeb can take:

1. **Probe (to get a frame as proof):** fix the local producer-surface creation that crashed in window 11. Verify the
   probe's `IConsumerSurface` / `IBufferProducer` / `Surface` / `ProducerSurface` usage and class ABI against the board's
   OH 6.1 headers (sizeof / vtable / sptr layout) — this is the outer's ABI hypothesis, now correctly aimed at the
   **surface** classes, not NWebCreateInfo. Candidate fixes: construct the surface on the right thread/context; or hold
   the `sptr`s correctly (the ctor takes `sptr<IBufferProducer>&` by non-const ref); or use the documented
   `Surface::CreateSurfaceAsConsumer`/producer pairing.
2. **Route-a native backend (the real path):** `nativeCreateNWeb(w, h, Object surface)` converts the Java `Surface` →
   `ANativeWindow`/`OHNativeWindow` (the app window) and passes it as the CreateInfo producer surface — no local surface
   is built, so it does not hit window-11's crash. This is the faithful path and what the backend will do; the probe's
   local-surface detour was only a self-contained cross-check.

The native backend can proceed (it supplies the Java surface), but a probe frame needs the surface-creation fix; the
outer should pick which to run in window 13.
