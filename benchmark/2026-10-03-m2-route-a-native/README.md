# M2 route-a native backend — the NWeb JNI layer behind NativeNWebBackend

#90, native, offline. The formal native backend for route-a WebView: the JNI implementation of
`org.westlake.webview.NativeNWebBackend`'s 20 native methods (`benchmark/2026-10-03-m2-route-a-java`), driving
OpenHarmony NWeb. Engine bring-up / CreateNWeb / NWebCreateInfo are **copied from cc-t3's A0 probe** (board-proven,
`../westlake-harness-t3/benchmark/2026-10-03-m2-a0-probe`, worker ddcbdd46); this adds the per-WebView surface chain,
the NWebHandler→Java-sink upcalls, and the RegisterNatives surface. **Built on hw248 with the frozen clang, ×2
byte-identical; all static gates pass. Not deployed — on-board waits for cc-t3's window13 surface conclusion.**

```
libwl_nweb_backend.so      (worker) = 8475da6fb6dd0016ffb361e2ebac075a849e4ad2845c65ce9559a155779577af  (×2)
libwl_nweb_backend_shim.so (shim)   = ba3e05612a390d7ef37bd32528b946c43c8e84e70b07cc775373086e4f11557b  (×2)
```

## Architecture (mirrors A0, but uses nweb_ns_legacy — DIGEST 761)
Two `.so`, one C-ABI symbol across the namespace boundary:
- **shim** (`nweb_backend_shim.c`, `libwl_nweb_backend_shim.so`): the runtime `System.load`s it in the app ns. Its
  `JNI_OnLoad` dlns get-or-creates **`nweb_ns_legacy`** (the `is_permitted` PERMITIED_TARGET2, dynlink.c:4189; lib_path
  = the worker dir only; inherit `default`), `dlopen_ns` the worker there, then calls the worker's C-ABI
  `nweb_backend_register(JavaVM*)`. **It never creates or touches `nweb_ns`** — formal route-a leaves `nweb_ns`
  entirely to NWebHelper, which `dlns_create`s it (arkwebcore libs dir + inherit ndk) at `Init` time to load the
  engine; whoever creates `nweb_ns` first wins its lib_path, so a self-loader that pre-creates it breaks OH's engine
  load (OH's create → EEXIST → wrong lib_path → engine dlopen errno=2). (A0's co-own of `nweb_ns` was experimental
  convenience, not formal — DIGEST 761. This was the one fix over the first cut: the outer's dispatch said "copy A0"
  without excluding A0's namespace shortcut.)
- **worker** (`nweb_backend.cpp`, `libwl_nweb_backend.so`): in `nweb_ns_legacy`; its NEEDED (`libarkweb_core_loader.z.so`
  the loader, `libsurface`/`libutils`/`libhilog`/`libc++`) are system libs that resolve through the inherited `default`
  ns — the arkweb **engine** is loaded separately by NWebHelper into OH's own `nweb_ns`. `nweb_backend_register`
  `RegisterNatives` the 20 methods and caches the `NWebCallbackSink` upcall method-ids. No mangled `Java_*` exports
  (RegisterNatives), no second engine copy across the boundary.

## ① Engine code copied from A0 (not rewritten)
`nativeInitEngine` = A0 S3/S4 verbatim: `NWebHelper::Instance().SetBundlePath(/data/storage/el1/bundle/arkwebcore)` →
`Init(true)` → (mode 1) `SetRenderProcessMode(SINGLE_MODE)` → `InitAndRun(true)`, guarded by `std::call_once`.
`nativeCreateNWeb` = A0 S5: a `NWebCreateInfo` subclass (W×H, `NWebOutputFrameCallback`, `GetProducerSurface`
returning `&surface_`) + `NWebHelper::Instance().CreateNWeb(info)` + `Resize`/`OnContinue`. `NWebEngineInitArgsImpl`,
the handler pattern (S6) and the create info are the A0 shapes.

## ② Surface chain (`SurfaceFromJava`)
The hosted Java WebView's `Surface` → NWeb producer surface, the A0 mode-16 native-window fallback chain started from
the WebView's own Surface:
```
ANativeWindow_fromSurface(env, surface)   (NDK, dlsym)         -> the runtime's AdapterAnw '_wnd' shim
oh_anw_get_oh(anw)   (liboh_adapter_bridge/liboh_android_runtime, dlsym, NOLOAD)  -> OHNativeWindow
OH_NativeWindow_GetSurfaceId(ohnw,&id)    (libsurface)         -> surface id
SurfaceUtils::GetInstance()->GetSurface(id) (libsurface)       -> sptr<Surface> = NWebCreateInfo::GetProducerSurface
```
If `oh_anw_get_oh` returns null (not a shim, already an OHNativeWindow) the window is used as-is. If window13 changes
the surface conclusion (mode 0 local surface vs mode 16 bridge window), this one function is where it adjusts.

## ③ Every OH C++ call statically verified (`evidence/static-calls-*.txt`)
- **Direct (non-virtual) calls — all 13 resolve to a board export** (`static-calls-direct.txt`): `NWebHelper::`
  Instance/SetBundlePath/Init/InitAndRun/Set+GetRenderProcessMode/CreateNWeb → `libarkweb_core_loader.z.so`;
  `SurfaceUtils::GetInstance/GetSurface`, `OH_NativeWindow_GetSurfaceId` → `libsurface.z.so`;
  `RefBase::Inc/DecStrongRef` → `libutils.z.so`; `HiLogPrint` → `libhilog.so`. `--no-undefined` at link already
  requires every one to resolve; this confirms + classifies each against the board dynsym.
- **Virtual calls — vtable slots extracted per method** (`static-calls-virtual.txt`): every `NWeb::*` / `NWebPreference::*`
  call is vtable dispatch (none appears as an undefined import — confirmed), at the slot indices the frozen clang
  emits from the frozen OH 6.1.0.31 headers (e.g. `nativeReload`→slot 25, `nativeGoBack`→21, `nativeStopLoading`→29,
  `nativeLoadWithDataAndBaseUrl`→47, `nativeLoadData`→48). The board `_ZTVN4OHOS4NWeb4NWebE` is a **stripped/local**
  symbol in the release `libarkweb_core_loader`, so the `.relr.dyn` slot→symbol read cannot be done against the board
  binary; slot correctness rests on the frozen-header ABI (same headers + compiler `feef13a3` the board engine was
  built from) and on A0 having exercised a superset of these NWeb virtuals on board. **window13 is the empirical slot
  confirmation.** The NWeb headers carry **no `#if` conditionals** (outer-confirmed), so the slot order is
  unconditional across builds.

### Slot verification table (`evidence/slot-verification-table.txt`)
Per JNI method: the NWeb/NWebPreference virtual it dispatches, the observed vtable offset, and whether A0's
`a0probe.cpp` already exercised that exact virtual on board. a0probe ran, on board, these NWeb/NWebPreference
virtuals: `SetNWebHandler, GetPreference, Resize, OnContinue, LoadWithDataAndBaseUrl, PutJavaScriptEnabled` (plus the
non-virtual `NWebHelper::` Init/InitAndRun/SetBundlePath/Set+GetRenderProcessMode/CreateNWeb). So:

| status | methods | vtable offset |
|---|---|---|
| **verified-on-board (a0probe)** — 7 | nativeInitEngine (non-virtual), nativeCreateNWeb (Resize/OnContinue), nativeRegisterHandler (SetNWebHandler), nativeLoadWithDataAndBaseUrl (slot47/0x178), nativeSetJavaScriptEnabled (PutJavaScriptEnabled slot33/0x108), nativeOnResume (OnContinue slot4/0x20), nativeOnDraw (Resize) | as noted |
| **runtime-unverified → first board call must invoke + log** — 10 | nativeReload (Reload slot25/0xc8), nativeStopLoading (Stop slot29/0xe8), nativeGoBack (NavigateBack slot21/0xa8), nativeCanGoBack (IsNavigatebackwardAllowed slot18/0x90), nativeOnPause (OnPause slot3/0x18), nativeLoadData (LoadWithData slot48/0x180), nativeLoadUrl (Load), nativePostUrl (PostUrl), nativeExecuteJavaScript (ExecuteJavaScript), nativeSetDomStorageEnabled (PutDomStorageEnabled slot33) | clean offset where the JNI fn does no string work; Load/PostUrl/ExecuteJavaScript mix JNIEnv-vtable loads (CStr/arrays) so the NWeb slot is confirmed by the first board call's log |
| N/A — 3 | nativeAddJavascriptInterface, nativeRemoveJavascriptInterface (not wired), nativeDestroy (no NWeb call) | — |

The first on-board run of this backend must drive each **runtime-unverified** method once and log the call + result
(a crash at a wrong slot localises immediately); cc-t3 will validate the legacy path with an A0 window.

## ④ Namespace (`evidence/open-sites.txt`, NEEDED tables)
- Worker NEEDED: `libarkweb_core_loader.z.so libsurface.z.so libutils.z.so libhilog.so libc++.so libc.so` — minimal,
  **no library appears twice**. Shim NEEDED: `libhilog.so libc.so`.
- The worker lives in `nweb_ns_legacy`; its NEEDED resolve from the inherited `default` ns (system libs, one copy
  each) + the worker dir — no app-dir duplicate but the worker itself. `nweb_ns` is OH's (NWebHelper's), untouched.
- `open_site_scan.py`: the worker's only `dlopen`s are the two **NOLOAD** probes for `oh_anw_get_oh`
  (`liboh_adapter_bridge.so` / `liboh_android_runtime.so`) — reuse the already-loaded copy, no new instance. The shim's
  `dlopen_ns nweb_ns_legacy` is through dlsym'd `dlns_*` pointers (the A0 pattern — the NDK libc stub lacks the ns ops), so it
  is indirect and not statically visible to the scanner; the ns edge is the proven A0 get-or-create+inherit.

## ⑤ Build (`recipe/build_nweb_backend_hw248.sh`, `evidence/build-*.txt`)
hw248, OH clang-15 `feef13a3` (the frozen compiler), `libcxx-ohos` (ABI ns `__h`), `-fno-rtti`, `-Wl,--no-undefined`,
include dirs + board libs reused read-only from cc-t3's A0 build area, built in an isolated `out/` (cc-t3's area
untouched). **×2 byte-identical** (worker `8475da6f`, shim `ba3e0561`); logs tee'd (`evidence/build-la.log`, `build-lb.log`).

## ⑥ JNI names/signatures match the Java side (`evidence/jni-signature-check.txt`)
javap of the compiled `NativeNWebBackend` vs the worker's `RegisterNatives` `kMethods` table: **all 20 method
names + descriptors MATCH** (e.g. `nativeCreateNWeb (IILjava/lang/Object;)J`,
`nativeRegisterHandler (JLorg/westlake/webview/NWebCallbackSink;)V`). The worker exports only the C-ABI
`nweb_backend_register` (no `Java_*`), correct for RegisterNatives.

## Known follow-ups (on-board / window13)
- `shouldInterceptRequest` → the NWeb `OnHandleInterceptRequest` response object (`NWebUrlResourceResponse`
  construction) is wired as the upcall only; building the response needs an on-board confirm of the setter names.
- `evaluateJavascript` result: uses `ExecuteJavaScript(code)` + an id-keyed `onEvaluateResult("null")`; the real
  result via `NWebMessageValueCallback` is the window13 follow-up (NWebMessage stringify).
- `addJavascriptInterface`: logged, not wired (Wikipedia's article view needs no JS bridge object);
  `RegisterArkJSfunction` is a separate item.
- shim eager-vs-lazy worker load: gate on "app hosts a WebView" / defer to first `create()` (runtime-loader wiring).

## Files
- `src/native/nweb_backend.cpp` (worker), `src/native/nweb_backend_shim.c` (shim),
  `recipe/build_nweb_backend_hw248.sh`.
- `evidence/static-calls-direct.txt`, `static-calls-virtual.txt`, `open-sites.txt`, `jni-signature-check.txt`,
  `build-SHA256SUMS.txt`, `build-inputs-sha256.txt`.
- Release (for cc-t3/cx-bms): `$WORKSPACES/westlake-inputs/generations/m2-route-a-native-backend-v1/` (payload both
  `.so` + src + SHA256SUMS); persistent on hw248 `/home/alvin/cc-wiki-nweb-backend/out/a/`. `artifacts/*.so` gitignored.
- `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline; built on hw248 in an isolated dir (cc-t3's A0 build area read-only). No board, no deploy, no push. cc-t3 owns
A0/engine-load + window13 (mode 0 local surface / mode 16 bridge window); this backend goes on board only after
window13, and if window13 changes the surface conclusion `SurfaceFromJava` adjusts. The intercept-response,
JS-result, and JS-interface items above are the next cut.
