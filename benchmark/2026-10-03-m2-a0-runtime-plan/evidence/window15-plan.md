# Window 15 plan: mode 32 (independent child RSSurfaceNode for NWeb, ACE WebPattern) + legacy-namespace entry variant, run MODES="0 32" in one window

After window 14: the route-a surface SOURCE works (CreateNWeb non-null with a bridge surface) but the bridge's
`getOhNativeWindow` returns the Activity's SHARED content node, so NWeb draws but is not presented (window14-mode16.md
§1). The fix is to give NWeb its OWN child surface, as OH ACE WebPattern does for the Web component.

## mode 32 — NWeb's own child RSSurfaceNode (to design, each OH call static-verified before building)
Target sequence (ACE WebPattern `rosen_render_web` / `RenderSurface`): under the Activity's window RSSurfaceNode, create
a child RSSurfaceNode, size/position it, flush the RS transaction, take its Surface, give it to NWeb.

Calls to static-verify (exported non-virtual vs vtable slot, vs board librender_service_client.z.so / libgraphic; same
.relr.dyn method as libsurface):
1. `RSSurfaceNode::Create(const RSSurfaceNodeConfig&, bool isWindow=false)` — static factory, returns
   `std::shared_ptr<RSSurfaceNode>`. Verify the exported mangled symbol and the sret/by-ref ABI. (Config = {name, ...}.)
2. Parent = the Activity window RSSurfaceNode (from the bridge RS-holder, as mode 16 obtained it) — `RSNode::AddChild(
   child, index)` OR set the child's parent; verify.
3. `RSSurfaceNode::SetBounds(x,y,w,h)` / `SetFrame` — size the child to the window; verify (likely virtual on RSNode).
4. `RSTransactionProxy::GetInstance()->FlushImplicitTransaction()` (or `RSTransaction::FlushImplicitTransaction`) — apply
   the node tree change; verify the exported symbol.
5. `RSSurfaceNode::GetSurface()` — already verified non-virtual (window 14).
Then `surface_ = child->GetSurface()` -> NWebCreateInfo::GetProducerSurface (same as mode 16, but NWeb now owns the node).

Decision on headers: RSSurfaceNode::Create/SetBounds/AddChild need more of the render_service_client API than a single
genstub cleanly covers (Create takes a config struct and returns a shared_ptr; SetBounds is likely virtual). Two options,
pick after the static check:
  (a) link librender_service_client + resolve the real include tree (rs_surface_node.h -> platform/drawing/rs_surface.h
      -> ...; add the needed -I dirs) — correct ABI from the compiler, at the cost of several include dirs;
  (b) genstub each call (as GetSurface) — only if each is a simple non-virtual exported symbol with a modellable ABI.
The static-verification step (symbol export + virtual/non-virtual per method) decides (a) vs (b) per call.

Criteria (window15-plan): CreateNWeb non-null on the child; after Load+JS, the t28 screenshot shows the NWeb page
(green #12ab34 中文) on the Activity window (now NWeb owns a child node, no hwui contention); plus js_colour via the
page load/console as before. If still covered, inspect the RS node tree / z-order.

## legacy-namespace entry variant (run in the SAME window, MODES="0 32", independent verdicts)
Entry variant: load the worker into `nweb_ns_legacy` (dynlink.c:4189 permitted target name), and DO NOT create or touch
`nweb_ns` — so when NWebHelper::Init runs, OH itself `dlns_create(nweb_ns, arkwebcore dir)` + inherit ndk to load the
engine (no EEXIST). This is window-10's "cleaner fallback" and what cc-wiki's formal shim will use.
- a0_entry.cpp: ns name "nweb_ns_legacy"; lib_path = /data/local/tmp (worker only) + inherit default (core_loader + 14
  closure resolve); do not pre-create/get nweb_ns.
- Criteria: mode 0 RESULT PASS stage=S8 (js_colour=1) AS BEFORE, AND the OH-creates-nweb_ns log shows a clean create
  (NO `ArkWebBridgeHelperLoadLibFile: dlns_create failed ... errno=17` EEXIST). Rebuild entry x2 identical, pin SHA.
- run_a0.sh break-on-PASS already removed, so MODES="0 32" runs both with independent verdicts.

## Scheduling
cx-t0 window 3 locked 5ea (14:40) and will lock 5cd next; this window runs after window 3 or in a gap it yields, per the
`A0 拟用 <板>` + 2-min protocol, ≤30 min, rollback+UNLOCK.

## UPDATE: mode 32 + legacy-ns BUILT & verified; mode 64 (cc-wiki Plan A) designed
- mode 32 (native child RSSurfaceNode) DONE: real RS headers pull Skia (unbuildable), so genstub the 5 calls — all are
  DIRECT exported non-virtual symbols (RSSurfaceNode::Create/GetSurface, RSNode::AddChild/SetBounds(ffff),
  RSTransaction::FlushImplicitTransaction); RSSurfaceNodeConfig layout replicated exactly (SurfaceId=uint64,
  SurfaceWindowType:uint8). worker 9db43b16 (x2), RS syms UND direct imports, mode-0 slots intact, NEEDED +=
  librender_service_client.
- legacy-ns entry DONE: a0_entry.cpp -DWL_A0_LEGACY_NS -> worker in nweb_ns_legacy, never touches nweb_ns (OH builds it).
  legacy entry 61e57956, default entry afeceead (both x2). run_a0.sh ENTRY=default|legacy + MODES (break-on-PASS removed).
- mode 64 (cc-wiki Plan A = SurfaceView holder Surface, backend d1d38ffad1 nweb_backend.cpp SurfaceFromJava) — TO BUILD:
  * MainActivity.java: add a SurfaceView, holder.setZOrderMediaOverlay(true); on surfaceCreated ->
    nativeSurfaceReady(holder.getSurface()) (a native method of the APK's liba0shim, which MainActivity System.loadLibrary's).
  * a0shim.c: nativeSurfaceReady(env, surface) -> ANativeWindow* anw = ANativeWindow_fromSurface(env, surface)
    (runtime shim returns the bridge AdapterAnw) -> setenv("WL_A0_SV_ANW", "%p", anw). (JNINativeMethod in a0shim JNI_OnLoad.)
  * a0probe.cpp mode 64 (GetSurfaceViewSurface): poll getenv WL_A0_SV_ANW -> oh_anw_get_oh(anw) (dlsym from the bridge,
    unwrap AdapterAnw) -> OHNativeWindow -> OH_NativeWindow_GetSurfaceId -> SurfaceUtils::GetSurface -> NWebCreateInfo.
    Cross-ns hand-off is a same-process pointer via env (like the bridge's WESTLAKE_NATIVE_WINDOW_PTR). Chain == cc-wiki
    nweb_backend.cpp SurfaceFromJava; compare directly.
  * Rebuild APK (new MainActivity + a0shim) and worker (mode 64), re-pin APK_SHA + RT_WORKER_SHA.
- Window 15: ENTRY=legacy, MODES="0 64 32"; independent verdicts; 64/32 judged by t28 screenshot showing #12ab34 on
  screen; if 64 lights, 32 is only a fallback record. After cx-t0 window 3 (5ea 15:25:50 / 5cd 15:26:54), 拟用+2min.
