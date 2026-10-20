# T27 bounded buffer metadata observation — review draft

DESIGN_ONLY_NOT_IMPLEMENTED. No implementation, build, device, or push is authorized by this packet. Future
offline work only; outer must admit the draft before any implementation. No REA by this lane.

## Purpose (verify a prediction, do not change behavior)
The T2 EGL create-null and the T1 YV12 layout-contract gap are distinct. New Mali REA (current recovered state,
exact `e0cb1081` `eglCreateImageKHR` @ELF `0x33e814`) accepts only format `{3,12,13,20,24,25,28,29}`; format
**`11` returns NULL before entering the implementation** (format `12` encodes FOURCC `34324241` then dma-buf;
the `+14` field is pin-header-confirmed as the format). T25 mapped YV12→OH **11**, so the create-null is very
plausibly the buffer carrying a Mali-reject format — but the **actual run descriptor was never captured**. T27's
only job is to **record the actual descriptor + the real create binding** so that prediction can be confirmed or
falsified **offline**, against the Mali accept-set. T27 changes **no** EGL target/context/attrs (cx's T26 already
retargets YV12→OH **12**/RGBA, inside the accept-set; T27 does not touch that).

## Reuse and narrow wiring (four existing insertion points; linked by cx into T26)
Reuse only cx's `t25-observation-blueprint` insertion points; add no new code path. New private TU + explicitly
derived glue **inside T27**; the original T20/T23/T25/T26 and R14/R15 files stay frozen/read-only. cx links the
unit into the single T26 on-board build; this lane produces **no** separate on-board version.
- **CPU native config** — R15 `provider_adapter.c:77–81`, after CONVERTED publication, before returning to
  R14/map; the successful request still owns `buffer`; record window / window-buffer / native identities, op ID,
  then public `GetConfig` width/height/format/stride/`usage_low32`. Do not read after flush/abort.
- **Android output** — R14 `window_module.c:82–84`, when `answer` is complete, before publication; record actual
  width/height/pixel-stride/format + the same op ID (native byte stride ≠ Android pixel stride; size from `h`).
- **Imported native config** — R23 `egl_import.c:56`, after `create_buffer` returns nonnull while its new owned
  window-buffer is retained; convert it back through the exact public `FromNativeWindowBuffer`, then `GetConfig`;
  record original input native ptr, converted ptr, window-buffer, slot/generation. Conversion failure =
  diagnostic UNKNOWN, do not substitute a guessed ptr or change the import outcome.
- **Actual create address** — R23 `egl_import.c:73–75`, around the selected call; copy the selected
  `create_image` fn ptr once, `dladdr` → address/base/file/relative offset, record display/context/target/
  window-buffer/attribs ptr, then call that same ptr once and record the return. Never substitute the
  current-display provider base for this function's owner; do not traverse the attribs ptr.

## Guards (no new footprint)
`GetConfig` has **no rc** (five signed32 fields; `usage_low32` only, upper 32 UNKNOWN). Resolve `GetConfig` /
`FromNativeWindowBuffer` **only** via the already-retained T20 owner / R23 HWUI handle. No new `dlopen`
(incl. NOLOAD), no raw `+0x18` / `+14` read, no `MapPlanes`, no extra map/acquire/reference, no new C++ getter.
Missing/foreign getter ⇒ field UNKNOWN; an otherwise-successful original op stays successful. Preserve `errno`;
**do not consume `eglGetError`** (the HWUI caller already reads it; its `SkDebugf` may appear in hilog).
Concurrency uses the original table/provider synchronization; diagnostics must not invert lock order.

## Bounded records
Bounded ring / fixed slots with a cap; overflow is dropped and counted, never blocks the provider or grows
unbounded. Every event carries PID / TID / transaction ID + op ID. Cache / pair / create-buffer reference counts
stay identical to the original path.

## EGL error — capture it at runtime, not in T27
T27 does **not** read `eglGetError`. The cheapest corroboration of the EGL error is **runtime hilog**: the T25
hilog quick ran *earlier* than the video fatal, so the next window must, **after the trigger and before
rollback**, capture `hilog -z` bounded by the **actual PID** — not infer routing from a stderr with no error.
This is an operational capture note for root, not T27 code.

## Required actual C tests (future; not this packet)
Typed fake provider/owner callbacks, canaries: the two observe paths record the exact fields; missing/foreign
getter ⇒ UNKNOWN with the original op still succeeding; cap overflow dropped+counted with PID/TID/txn/op IDs;
lifetime sampling strictly before flush/abort and before release_failed_create/destroy with no new acquire or
leaked reference; no `eglGetError` consume, no new `dlopen`, no raw read, `errno` preserved. The Rust selector
dispatches the real Python/host checker; static scenarios may pass while the human scenario stays pending_review.

## Boundaries
Only `benchmark/2026-10-20-t27-buffer-observation/**`, the T27 spec, and the T27 Rust selector may change in
future implementation. No EGL target/context change, no format-support guess, no player patch, no device, no
screenshot success claim. Outcome is at most `OFFLINE_CANDIDATE_NOT_DEPLOYMENT_AUTHORIZED`; writer/EGL results
stay unknown; no video PASS.
