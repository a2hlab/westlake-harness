# Window 16 (5ea, legacy entry, MODES="64 32"): MODE 32 LIT THE SCREEN — route-a in-process ArkWeb render ON SCREEN via NWeb's own child RSSurfaceNode. kill_app fix worked (both modes ran fresh). mode 64 (SurfaceView) env-absent (secondary fix).

## kill_app fix worked: both modes ran fresh
    == mode 64 ... [a0] kill_app: uid=20011006 clean (no processes) ... S0 pid=30180 mode=64
    == mode 32 ... [a0] kill_app: uid=20011006 clean (no processes) ... S0 pid=30348 mode=32
Each mode re-bound a fresh process (distinct pids, a0_probe_start ran per mode). Clean rollback + UNLOCK (222 s),
fingerprint 821de739cf81.

## mode 32 (native child RSSurfaceNode) — ON SCREEN (the milestone)
    [A0] S5 bridge parent RSSurfaceNode=0x7f2661a040
    [A0] S5 child node=0x7f23cdda30 parent=0x7f2661a040 GetSurface=0x7f23bce4d0 (bounds 0,0,720x720)
    [A0] S5 CreateNWeb -> 0x7f229bc0b8        <- non-null, on NWeb's OWN child node
    [A0] S7 console_js=1 load_end=1           <- page loaded, JS ran
    [A0] RESULT FAIL stage=S8 surface_frames=0 (probe can't AcquireBuffer NWeb's own child surface -- benign)
t28 (evidence/window16-mode32-ONSCREEN-t28.jpeg): the NWeb page is COMPOSITED ON THE ACTIVITY WINDOW — a green #12ab34
720x720 region (the JS-set background) with the page H1 "中文 A0 探针" in black, top-left (the SetBounds 0,0,720x720). So
the full route-a chain renders ON SCREEN: runtime entry (nweb_ns_legacy) -> engine -> CreateNWeb on an independent child
RSSurfaceNode (RSSurfaceNode::Create + AddChild under the Activity window node + SetBounds + FlushImplicitTransaction) ->
Load -> JS exec -> frame composited. No hwui contention (own node), unlike window-14 mode 16 (shared content node).

## mode 64 (cc-wiki Plan A SurfaceView) — did not light, env absent (secondary)
    [A0-JAVA] surfaceCreated -> nativeSurfaceReady   (Java called it, no exception)
    [A0] S5 mode64: WL_A0_SV_ANW absent (SurfaceView not ready within timeout) -> FAIL ; CreateNWeb -> 0
a0shim's native nativeSurfaceReady ran (Java success path) but emitted no [A0-SHIM] line and never set WL_A0_SV_ANW -> most
likely ANativeWindow_fromSurface (dlsym) returned null at that instant (the SurfaceView's buffer not yet valid in
surfaceCreated) so the `if(anw) setenv` was skipped. Fixes for a later window: use surfaceChanged (surface valid) instead
of surfaceCreated; and/or call ANativeWindow_fromSurface by NEEDED not dlsym; log fromSurface/anw unconditionally. Not
blocking: mode 32 already proves on-screen route-a rendering with a native-built child node.

## Verdict for the formal route-a backend
- PROVEN on-screen: NWeb's OWN child RSSurfaceNode under the window node (mode 32). cc-wiki's backend can use a native
  child node (this path) directly; it lights the screen with no hwui contention.
- cc-wiki Plan A (SurfaceView holder Surface) is the same idea at the Java layer; it needs the a0shim surfaceChanged/
  fromSurface fix to deliver the surface, but the NWeb side is identical (SurfaceFromJava -> producer surface -> NWeb).
- Combined proof chain: mode 0 (engine paints, pixel readback) + mode 32 (on-screen via child node) + legacy-ns (OH owns
  nweb_ns cleanly). M2 route-a in-process ArkWeb rendering is demonstrated end-to-end, on screen.
