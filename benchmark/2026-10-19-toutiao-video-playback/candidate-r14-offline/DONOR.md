# Donor and deliberate differences

The reference is the repository-tracked `webview_bionic_shim.c`, SHA
`f12c5c921bdff7df8ea2f955b1de69eed2e4cec12fc7b830028027f30572a02a`,
under `sources/api-implementations/source-build-native691/westlake/framework/webview-shim/`.
Lines 3901–4078 provide Android Buffer/Rect layout, the seven format conversions,
byte-to-pixel stride conversion, and the Request/Map/Unmap/Flush outline. The
upstream snapshot is `691433b967ba01365a382d30fbd820c1231c0811` as recorded by
source-build-native691; its Apache-2.0 license is retained in donor-LICENSE.
Exact source and EDGE-CONTRACT inputs are in source-lock.json. This is an adapted
narrow module, **not byte-identical donor code or a validated OH implementation**.

Changes required by EDGE-CONTRACT:

- All provider access is supplied by immutable explicit callbacks. No dlopen,
  dlsym, raw wrapper access, window creation, audio/JNI/loader code or virAddr fallback.
  `handle` copies metadata through a trusted callback; it is not an OH struct cast.
- Reserve wrapper AND resolved OH identity through CLAIMED, LOCKED, COMPLETING,
  and failed ownership. The table mutex never spans a blocking provider call.
  Same-OH aliases cannot bypass the reservation; exact lock wrapper alone unlocks.
- A single monotonic 3000 ms fence deadline survives EINTR/EAGAIN. Only POLLIN
  without ERR/NVAL/HUP succeeds before deadline. Each returned owned fd is closed
  once; close errors are retained without unsafe retry.
- Map rc0 alone establishes a successful Map and requires one Unmap, even when
  bits is null or later geometry fails. Error+nonnull bits does not authorize Unmap.
  All pre-publication failures leave output cleared; no fallback pointer is exposed.
- Explicit full returned-buffer dirty rectangle; no donor NULL-region fallback to
  unrelated window geometry. Format, integer bounds, allocation size and divisible
  byte stride are checked. Flush callback ABI is offline-only and not an OH binding.
- A failed lock may attempt one Abort after request ownership, but never after
  failed Unmap. Abort success is NOT release proof: FAILED stays occupied. A flush
  error never causes Abort because queue state is unknown. Primary and cleanup
  return values remain independently inspectable, without double consumption.
- Every request error, including no-buffer/no-fd, conservatively quarantines the
  reservation. Eight such errors exhaust this instance and the ninth request is
  refused. There is deliberately no reset/free-failed API. A later recovery contract
  would be required to reclaim uncertain ownership; none is inferred here.

Lifetime is caller-owned: one module per OH ownership domain, immutable callback
lifetime, no concurrent destroy and no in-flight or new API calls during destroy.
Destroy requires externally established quiescence, then refuses any non-FREE slot.
It does not refcount calls still in unwrap. Tests assert occupied-slot EBUSY and
successful destroy after all normal completions; they do not exercise forbidden
concurrent destruction. Failed test contexts are quarantined until process exit.
