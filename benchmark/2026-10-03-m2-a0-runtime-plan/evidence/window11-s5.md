# Window 11: the engine now LOADS and INITS (S3 Init→1, S4 InitAndRun→1 — past window-10's wall); the SIGSEGV is the probe's own producer-surface creation (mode 0 took the surface path), not NWebCreateInfo

Window 11 (5ea, 2026-10-03 13:01, U13 `821de739cf81/124`, clean rollback + UNLOCK after 92 s). Runtime entry a352a36f,
worker faad4897. Full backtrace was read from the window's own captured hilog (`hilog-all.txt.gz`) — **no board read
needed** (5ea's lock was respected; it was free anyway after the window UNLOCKed).

## The win: the window-11 nweb_ns fix cleared the S3 engine-load wall

The runtime entry fired (B7BindFixes `System.load` of the bind-mounted `libwestlake_html_compat.so`), created `nweb_ns`
with the both-dirs lib_path, and the worker ran:

```
[A0] entry ns nweb_ns (lib_paths=/data/local/tmp:/data/storage/el1/bundle/arkwebcore/libs/arm64): dlns_get(nweb_ns)=126 create=0 … inherit=0
[A0] S1 NWebHelper::Instance … in /system/lib64/platformsdk/libarkweb_core_loader.z.so
[A0] S2 attached ApplicationContext … baseDir=/data/storage/el2/base bundleName=org.westlake.a0probe
C04500/webview ArkWebBridgeHelperLoadLibFile: succeed to load lib file …/arkwebcore/libs/arm64/libarkweb_engine.so   <-- loads now
C04500/webview GetWebEngine: web engine libraryloaded
[A0] S3 … Init(1) -> 1   (window 10 was -> 0)
[A0] S4 InitAndRun(1) -> 1
```

So the both-dirs `nweb_ns` lib_path (window-11 fix) **works**: OH's `ArkWebBridgeHelperLoadLibFile` still logs the
`dlns_create … errno=17` (EEXIST, non-fatal) but then **succeeds** loading `libarkweb_engine.so` from the arkwebcore dir
now in the shared `nweb_ns` lib_path. Engine loaded, `Init`→1, `InitAndRun`→1. (`GetWebEngine: api level of arkweb core
is 0` is a non-fatal warning; `icudtl.dat not exists` and `libdsmm_innersdk … errno=2` are also non-fatal.)

## The crash: producer-surface creation, in the probe's own CreateInfo ctor — mode 0 took the surface path

```
Reason: SIGSEGV(SEGV_MAPERR)@0xfe41b909b4   Tid:25013 Name:CrBrowserMain
LastFatalMessage: … [src/native/a0probe.cpp(a0_probe_start:322)] EventName 'a0-run'
#00 RefBase::IncStrongRef(void const*)+0                            libutils.z.so
#01 ProducerSurface::ProducerSurface(sptr<IBufferProducer>&)+632    libsurface.z.so
#02 Surface::CreateSurfaceAsProducer(sptr<IBufferProducer>&)+68     libsurface.z.so
#03 a0_probe_start::$_0::operator()()+1716                          libwl_a0_nweb.so   (our Run() task)
#04 EventHandler::DistributeEvent … (the posted a0-run task)
```

This is **before** `CreateNWeb` (S5) — there is no S5 WL-A0 line. It is the probe's `CreateInfo` constructor surface
path: `consumer_ = IConsumerSurface::Create(...); producer = consumer_->GetProducer(); surface_ =
Surface::CreateSurfaceAsProducer(producer)` → `ProducerSurface` ctor → `RefBase::IncStrongRef` on a bad pointer
(`@0xfe41b909b4`).

**Root cause = the run mode, not NWebCreateInfo.** The worker `faad4897` is the **full** build (it NEEDs
`libsurface.z.so` + `libsync_fence.z.so`; the `-DWL_A0_RUNTIME` variant trims those). `a0_probe_start` in the full build
reads `debug.westlake.a0probe.mode`; I ran the window with `MODES="0"` → `mode=0` → `CreateInfo(args, (mode&8)==0)` =
`withSurface=true` → the local consumer/producer-surface path ran and crashed. The outer's hypothesis (NWebCreateInfo
vtable/layout) is **not** where it died — the fault is two frames below our lambda, in `libsurface`, and S5 was never
reached.

- **NWebCreateInfo ABI is not implicated:** the probe compiled against the board's OH 6.1.0.31 `nweb_create_info.h`
  headers (the same image the engine ships), and it overrides every pure virtual (else it would not link), so its vtable
  matches the base declaration order. CreateNWeb has not yet been exercised.
- Whether `Surface::CreateSurfaceAsProducer` itself has an ABI/usage fault (bad `producer` sptr / RefBase layout) is
  **moot** for A0: the runtime-faithful A0 path is **callback-only** (the `NWebOutputFrameCallback` gives RGBA CPU
  frames), and route-a gets its window surface from Java (`nativeCreateNWeb(…, Object surface)`), never by creating a
  local consumer/producer surface. The probe only built a local surface as an optional cross-check.

## Fix for window 12: callback-only (mode bit 8) — no rebuild

Run window 12 with **`MODES="9"` (= 1 | 8: single render process + no producer surface)**, same pinned binaries (entry
a352a36f, worker faad4897). Then `CreateInfo(args, false)` → `withSurface=false` → no `Surface::CreateSurfaceAsProducer`
call; `GetProducerSurface()` returns `nullptr` → `CreateNWeb` goes callback-only, and the `OutputFrameCallback` delivers
frames (the js-colour pixel check, the actual M2 render proof). This both sidesteps the surface crash and is the
runtime-faithful path.

- **Cleaner follow-up (optional):** rebuild the worker with `-DWL_A0_RUNTIME` so callback-only is unconditional (forces
  `1|8`, drops the `libsurface`/`libsync_fence` NEEDEDs and the param dependency). Not required for window 12; mode 9 on
  the existing worker is sufficient to answer "does the engine paint".
- **For the route-a native backend:** `nativeCreateNWeb` uses the Java-provided surface, so it does **not** reproduce
  this crash; but it must also avoid the probe's local-surface path. The backend's CreateInfo will return the
  Java-derived window (or callback-only + blit in `nativeOnDraw`), not `Surface::CreateSurfaceAsProducer`.

## Next

Window 12 = 5ea/any free board cx-t0 hasn't claimed, `MODES="9"`, A0_EXPECT_FP per board, ≤25 min, same rollback. Watch
for `[A0] S5 CreateNWeb -> <ptr>`, S6/S7 (LoadWithDataAndBaseUrl), and `[A0] S8 callback frame … js_colour=1` →
`RESULT PASS`.
