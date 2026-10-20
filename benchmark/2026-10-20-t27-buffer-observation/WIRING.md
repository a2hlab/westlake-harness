# T27 observer — wiring interface for cx (NOT a full R14 overwrite)

Ownership (2026-10-20 update): **cx owns ALL the integration glue** — the CPU R14/R15 derived copies **and** the
R23/platform joint wiring. **T27 delivers ONLY `observer.c/h` + `test_observer.c`**; it adds **no** R14/R15/R23/
platform derived files, and all originals stay read-only. cx links `observer.c` into the single T26 on-board
build. The call sites below are the **interface reference** for cx's wiring, not files T27 ships. No device, no
independent production/on-board version. The observer never dlopens, never consumes `eglGetError`, never reads a
raw buffer tail; it preserves `errno` (entry errno for pure observers; the provider's errno for the create path).

## Getter injection (cx resolves, observer only calls)
cx resolves, via the **already-retained** T20 owner / R23 HWUI handle (no new dlopen):
`OH_NativeBuffer_GetConfig` → `wl_t27_getters.get_config`, and the public `FromNativeWindowBuffer` →
`wl_t27_getters.from_nwb`. Pass `NULL` for any that cannot be resolved through the retained handle, or that
resolves to a non-admitted instance → the dependent fields record UNKNOWN and **no getter call is made**.
Admitted getter calls are counted by `wl_t27_getter_calls()`, separate from the untouched provider op counts.

## Call sites (one observer call each; surrounding code unchanged)
1. **R15 `provider_adapter.c:77–81`** — after CONVERTED publication, before returning to R14/map, while the
   successful request still owns `buffer`:
   `wl_t27_cpu_native(op_id, txn_id, window, window_buffer, native, &g, cfg_buffer);`
2. **Android output — after T26 `prepare_output`, before publish** (in cx's R14 glue; the returned buffer here is
   the **YV12 scratch**):
   `wl_t27_android_output(op_id, txn_id, scratch_w, scratch_h, scratch_pix_stride, scratch_format, &g, native_packed_buffer);`
   (`native_packed_buffer` is the underlying packed descriptor, recorded separately from the scratch.)
3. **R23 `egl_import.c:56`** — after `create_buffer` returns non-null while the new window-buffer is retained:
   `wl_t27_import_config(op_id, txn_id, input_native, window_buffer, slot, generation, &g);`
   (observer converts `window_buffer` back via `g.from_nwb` once, then `g.get_config`; failure → UNKNOWN.)
4. **R23 `egl_import.c:73–75`** — replace the direct selected-call with the observer, which performs the **single**
   invocation and returns its value for cx to use (no second call):
   `EGLImage img = wl_t27_create_call(op_id, txn_id, selected_create_image, display, context, target, window_buffer, attribs);`
   The observer `dladdr`s `selected_create_image` (records addr/base/file/rel-off — never the current-display
   base), records display/context/target/window-buffer/attribs **pointer** (attribs never traversed), then calls
   it once.

## Lifetime
Sample CPU-side strictly before flush/abort; import-side strictly before `release_failed_create`/destroy. The
observer adds no acquire, leaks no reference, rewrites no return value; cache/pair/create-buffer ref counts stay
identical to the original path.

## Build / tests
`observer.c` (follows) compiles into the T27 unit; cx links it into T26. Host tests (`tools/spec-checks` selector
`toutiao_t27_buffer_observation.rs` → Python/host checker) use typed fake provider/owner callbacks + canaries:
errno preserved, admitted getter calls counted exactly, foreign/NULL getter makes **zero** calls, source-mapping
/ actual create-pointer invoked **once**, cap overflow dropped+counted with PID/TID/txn/op IDs. No device.

## Status
**FROZEN for cx wiring:** `observer.h` (ABI mirrors SDK `OH_NativeBuffer_Config` width,height,format,usage,stride
with compile-time offset asserts), `observer.c` (bounded 256-slot ring + immediate bounded stderr emit with
`<TRUNC>`+newline guard, separate getter counting, entry/provider errno semantics, dladdr-only, no eglGetError),
and `test_observer.c` (host test **PASS**). Raw build/run argv+stdout+stderr+rc and artifacts persisted under
`$HOME/.local/share/westlake/t27-observer-cc/` (see `RECEIPTS.md`). cx owns and wires all glue.
