# Minimal lock/unlock edge obligations

This is a short source/SDK contract audit for the later narrow module's tests. It changes no runtime code, creates no candidate and makes **no claim that these edge cases caused the current Toutiao failure**. Existing code is a reuse reference; no matching device receipts proving its fence/cleanup/concurrency edge cases were found. Hashes are in `edge-contract-sources.json`.

## Existing references and their limits

Paths below are repository-relative unless prefixed `$OH_SDK_NATIVE`.

| Reference | Actual lines | Useful behavior / limit |
|---|---|---|
| `bms/src/adapter/framework/hwui-shim/jni/sync_wait_compat.c` | 9–24 | Rejects negative fd, poll error/POLLERR/POLLNVAL, timeout; retries EINTR/EAGAIN. It does **not** enforce positive POLLIN or one total deadline across retries: do not blindly copy as a bounded-wait implementation. It does not close fd. |
| `sources/api-implementations/source-build-native691/westlake/native/hwui/oh_hardware_buffer.cpp` | 48–63 | Clears output, waits fence before Map, returns failure from Map/Unmap. Its infinite wait is a different contract from a bounded video call. |
| Same file | 65–69 | Conversion result is a borrowed buffer in this source; no acquired reference is released here. Do not invent an Unreference for the narrow module without matching reference ownership. |
| `.../native/hwui/oh_surface_texture.cpp` under the same westlake root | 140–149, 180–197 | Retains owner when release cannot be completed, and refuses a failed fence wait. This is a **consumer** API: its ReleaseNativeWindowBuffer/fence ownership cannot be copied directly to the producer lock path. |
| `$OH_SDK_NATIVE/sysroot/usr/include/native_window/external_window.h` | 479–498, 501–518, 540–552 | Request needs geometry and a corresponding flush; caller closes consumed request fence; flush takes fence ownership; Abort returns a buffer without publishing content. These APIs are explicitly non-thread-safe. |
| `$OH_SDK_NATIVE/sysroot/usr/include/native_buffer/native_buffer.h` | 218–245, 275–286 | Map and Unmap are paired, both have error results, conversion has error result. All are non-thread-safe. |
| `benchmark/2026-10-01-n9-first-damage/upstream/native_window.cpp` | 205–234, 237–280, 322–329 | Archived OH6.1 revision `0bf226a1…`: Request assigns outputs after success; flush propagates lower failure; CancelBuffer **discards** its lower return and returns 0 after wrapper validation. This is an archived revision, not proof of the current board's bytes. |
| `.../framework/webview-shim/webview_bionic_shim.c` under the same westlake root | 3986–4024, 4058–4078 | Donor claims slot before request, but checks neither poll nor Map result; frees slot before unmap/flush; misses cleanup after a successful map followed by unsupported format. These are source audit findings, not measured current faults. |

## Smallest ownership sequence to test

Use these labels only to describe observable ownership; no new framework is requested:

`FREE → CLAIMED → LOCKED → COMPLETING → FREE`

- **CLAIMED:** reserve the observed Android wrapper **and its exact resolved OH window** before any request. The reservation stays busy through request/wait/map, and through later unmap/flush. SDK's non-thread-safe boundary is the OH window; two wrapper aliases for one OH window must not bypass serialization. A small state-table mutex alone is insufficient if released before an unprotected same-window request/flush.
- **LOCKED:** publish nonnull writable output only after request returned 0/non-null buffer, fence readiness was confirmed (or fence=-1), conversion/Map succeeded, and format/geometry/stride bounds were accepted. Track whether Map actually succeeded; a nonnull pointer with an error return is not success.
- **COMPLETING:** exactly one matching unlock consumes a LOCKED record. It keeps the reservation busy until unmap and flush terminate; another lock, alias lock, or second unlock cannot reuse/free it during this interval. Do not require the same thread unless the actual caller contract establishes that restriction.
- **FREE:** normal success means successful unmap followed by successful flush; no double unmap/abort/flush or fd-close. If mapping succeeded but later pre-publication validation fails, unmap before cancellation. Failure before successful Map never invokes Unmap.
- **Uncertain cleanup:** retain the failed window/buffer record and refuse new operations on it rather than clear ownership and claim release. Missing resolver/API, failed Unmap, failed flush, or failed Abort cannot produce success. A cleanup-only Abort can be attempted after a rejected flush only under a positively understood ownership contract; failed flush does not prove it was unqueued. The archived CancelBuffer return-0 caveat means a stubbed Abort return cannot prove backend release. Record the cleanup attempt/result separately; do not endlessly retry or assume a safe double cancel.

For a bounded fence wait: use one monotonic deadline across EINTR/EAGAIN retries; only readiness with POLLIN and no error/invalid event permits mapping. A timeout, terminal error, or HUP-only event returns failure and never exposes bits. The consumed request fd is closed exactly once; no close for -1. No requirement is made to call newer MapWaitFence APIs: their exact availability and behavior on the deployed OH version have not been bound.

`handle->virAddr != NULL` is not proof of a live writable mapping. The narrow module should reject conversion/Map failure instead of silently falling through to that pointer, unless a separately evidenced already-mapped ownership path is explicitly admitted. Check Map/Unmap symbol availability before requesting a buffer, together with request/handle/abort/flush and the proven unwrap provider.

## Required refusal and pairing cases for later tests

These are test inputs/expected behavior, **not executed tests**. Use a call journal and barriers at request/map/unmap/flush so concurrency outcomes are deterministic.

| Case | Must refuse / observable obligation |
|---|---|
| Missing required function, unknown object/provider, null output | No request, no slot left occupied, no output bits; negative result |
| Request failure or request rc0 with null buffer | No Map/flush, no successful lock; close any actually returned owned fd once; inconsistent owned outputs require explicit cleanup rather than guessed success |
| Fence=-1 / ready POLLIN | No wait for -1; otherwise successful readiness before first Map and one fd close |
| Fence timeout, EINTR storm, EAGAIN, POLLERR/POLLNVAL, HUP-only | No Map/output/flush on failure; total deadline remains bounded across retries; cleanup journal and fd close exactly once |
| Conversion failure; Map error with null or nonnull bits | No successful lock or virAddr fallback; Unmap only if Map truly succeeded; retain/abort owned request according to admitted cleanup contract |
| Successful Map followed by unsupported format or invalid dimensions/stride | One Unmap before cancellation; no pixel pointer published; no flush |
| Successful unlock | One Unmap, then one flush(window,buffer,-1,whole region); same lock-owned buffer; only after success may slot become FREE |
| Unmap error or missing function | No flush and no success; retain failed ownership record; later lock/unlock cannot double-consume it |
| Flush error / cleanup failure | Negative result and preserved error/ownership record; no unconditional memset-to-FREE, no fake frame acceptance |
| 8 occupied slots and a ninth independent window | Ninth refused before Request; 8 active records unchanged; only genuinely released slots reused |
| Same wrapper twice / two aliases sharing one OH / unlock during CLAIMED | Second operation refused or serialized without overlapping SDK calls; no extra request, unmap, or flush and no premature slot release |
| Lock during COMPLETING / two simultaneous unlocks | First matching completion alone owns the record until terminal outcome; deterministic blocked/refused second operation, zero double flush |

Full-region `{NULL,0}` is supported by the archived OH implementation, but its fallback uses **window-config dimensions** (native_window.cpp:258–263). That is not automatically the returned buffer's size and is not proof of nonzero/current dimensions. Geometry remains a separately bound input; no new damage-policy change is authorized here.
