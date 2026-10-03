# Window 15 build: mode 32 + mode 64 + legacy-ns entry, all static-verified. Worker 76e8fc9b, legacy entry 61e57956 / default afeceead, APK 7054457c, a0shim b8ecccfc — all x2 byte-identical.

## Reminder (1): mode 32 RSSurfaceNodeConfig genstub layout (vs rs_surface_node.h:60, SurfaceId=uint64/SurfaceWindowType:uint8)
Field order/types copied verbatim from rs_surface_node.h:60-78 (SurfaceId=uint64_t rs_common_def.h:48; SurfaceWindowType
: uint8_t rs_common_def.h:564). libc++ std::string = 24 bytes on arm64. Offsets the compiler lays out (identical for the
real struct and the genstub, since same field types+order):
  off 0   std::string SurfaceNodeName            (24)
  off 24  void*       additionalData             (8)
  off 32  bool        isTextureExportNode         (1)
  off 40  uint64_t    surfaceId                   (8)   (7 pad after the bool)
  off 48  bool        isSync                      (1)
  off 49  SurfaceWindowType surfaceWindowType     (1, uint8)
  off 56  shared_ptr<RSUIContext> rsUIContext     (16)  (6 pad)
  off 72  bool        isSkipCheckInMultiInstance  (1)
  sizeof 80. If mode 32 FAILs on-board, suspect this layout first (dump the config bytes Create reads).
RSNode::SetBounds: the header has two virtual overloads (SetBounds(Vector4f), SetBounds(ffff)), but RSSurfaceNode does
NOT override either (no _ZN...RSSurfaceNode9SetBounds export — only _ZN4OHOS5Rosen6RSNode9SetBoundsEffff). The genstub
declares SetBounds(ffff) non-virtual, so the compiler emits a direct bl to that exported RSNode symbol = the one and only
implementation (vtable dispatch would resolve to the same). No slot involved.

## mode 64 (route-a FORMAL, cc-wiki Plan A = SurfaceView holder Surface)
- MainActivity.java: FrameLayout(TextView + SurfaceView); SurfaceView.setZOrderMediaOverlay(true); surfaceCreated ->
  nativeSurfaceReady(holder.getSurface()).
- a0shim.c (app ns, System.loadLibrary'd): Java_..._nativeSurfaceReady -> ANativeWindow_fromSurface (dlsym; runtime hook
  returns the bridge AdapterAnw) -> setenv("WL_A0_SV_ANW", "%p", anw). Resolved by name (no RegisterNatives). setenv
  declared explicitly (sysroot gates it behind a feature macro).
- a0probe.cpp mode 64 (GetSurfaceViewSurface): poll getenv WL_A0_SV_ANW (after surfaceCreated, before CreateNWeb; 10s
  timeout -> log + FAIL, no crash) -> oh_anw_get_oh (dlsym from the runtime handle, like flutter_egl.cpp) unwrap ->
  OHNativeWindow -> OH_NativeWindow_GetSurfaceId -> SurfaceUtils::GetSurface -> NWebCreateInfo. Same chain as cc-wiki
  nweb_backend.cpp SurfaceFromJava; cross-ns hand-off is a same-process pointer via env (like the bridge's
  WESTLAKE_NATIVE_WINDOW_PTR).
- New OH calls static-verified: oh_anw_get_oh (dlsym, not a hard import -> 0 UND); ANativeWindow_fromSurface (dlsym in
  a0shim); OH_NativeWindow_GetSurfaceId + SurfaceUtils::GetSurface (libsurface, already linked). Worker 76e8fc9b: 5 RS/
  surface UND imports, oh_anw_get_oh 0 UND (dlsym), mode-0 slot 0x50 intact.

## Pins (run_a0.sh): APK_SHA=7054457c (v3), RT_WORKER_SHA=76e8fc9b; ENTRY=default(afeceead)|legacy(61e57956); MODES runs all.
## Window 15: ENTRY=legacy, MODES="0 64 32"; independent verdicts; 64/32 judged by t28 screenshot (#12ab34 on screen);
## 64 lights -> 32 is only a fallback record. After cx-t0 window 3 (5ea 15:25:50 / 5cd 15:26:54), 拟用 + 2min.
