# R15 adapter — field/ABI/Region + lifecycle review

Lines in `provider_adapter.c` `5fc32ea5…`; types in `candidate-r14-offline/window_module.h`
`28a88796…`.

## Signed 24-byte handle (handle:58-71) — CORRECT
- `r14_handle` is `{int64 width,height,stride_bytes,size_bytes; int32 format}` (window_module.h:11).
  Provider byte layout is width@4, **stride@8, height@12**, size@16, format@20.
- Locals filled in **offset order** (65): `width←+4, stride←+8, height←+12, size←+16, format←+20`.
- Positional init (69) `{width,height,stride,size,format}` → `.width=+4, .height=+12 (local height),
  .stride_bytes=+8 (local stride), .size_bytes=+16, .format=+20`. The cross-over (`stride`↔`height`)
  is handled correctly; `int32→int64` assignment **sign-extends** (signed interpretation then widen).
- **24-byte bound proven by guard page** (test_adapter.c:66-67): second page `PROT_NONE`,
  `prefix=alloc+page-24`, so byte 23 is the last readable byte. `memcpy(p+20,4)` reads p[20..23] — in
  bounds; any tail read would SIGSEGV. Signed values pinned at the guard page by test:94
  (`width@4=-1→h.width==-1`, `stride@8=INT32_MAX→h.stride_bytes==INT32_MAX`). Byte 0-3 not read (not
  in the consumed offset set). Units (byte-stride/capacity) are deliberately not asserted; R14 does the
  `%bytes`/`/bytes`/product checks (window_module.c:81). ✓.

## Region by value + LTRB→xywh (flush:105-114) — CORRECT
- Gate (109) rejects before any provider call: `!rect`, `width<=0||height<=0`,
  `width>INT32_MAX||height>INT32_MAX`, `fd!=-1`, `r->buffer!=b`, `phase!=UNMAPPED`, `failed||uncertain`,
  double-flush. `width/height` are `int64=(int64)right-left` so right-left can't overflow int32.
- `struct Rect ohrect={left,top,(uint32_t)width,(uint32_t)height}` (111): cast safe (width∈[1,INT32_MAX]).
  `Region region={&ohrect,1}` — **by value**, `rectNumber=1`; `a->p.flush(w,b,-1,region)` — **fence=-1**,
  `ohrect` is a valid stack local for the synchronous call. ✓.
- Host ABI pinned by `_Static_assert` (8-9): `sizeof(Rect)==16, w@8, h@12`; `sizeof(Region)==16,
  rects@0, rectNumber@8`. Under `R15_OH_SDK` the `MATCH` asserts (11-17) check each provider fn type
  is `__builtin_types_compatible_p` with the real `OH_NativeWindow_*`/`OH_NativeBuffer_*` prototype.
  **Proven by the outer's byte-identical OH ET_REL object** (compile-only `PASS`); I did not re-run it.
- Tested: `region-0 {4,6,12,10}`→journal x=4,y=6,w=8,h=4 (test:98); reversed/overflow/zero regions
  `region-1..5` all rejected pre-flush (test:99). ✓.

## Lifecycle phase gates — CORRECT (one documented coupling)
`EMPTY,RESERVED,REQUESTED,CONVERTED,MAPPED,UNMAPPED` (19). `phase!=EMPTY` doubles as "slot occupied".
Phase advances: request→REQUESTED(51/54), convert→CONVERTED(80), map→MAPPED(90), unmap→UNMAPPED(101),
flush success→`memset`(113). `handle` requires REQUESTED and does **not** advance phase (so it must run
**before** convert). **Coupling (condition):** the adapter encodes R14's call order (handle-before-
convert) in its phase gates; valid under the one-adapter↔one-R14 binding and proven by the passing
`pair` suite, but it is an ordering assumption, not an independent invariant.

## Construction / teardown — CORRECT
- `r15_create` (126-130): null-checks all 12 provider+capability fns (`-ENOSYS`), `calloc`+mutex,
  installs a plain typed thunk table into `r14_ops` (no OH fn pointer is cast into an R14 slot — each
  thunk has the exact R14 signature). `memset(ops,0,…)` first so a failure leaves a clean `ops`.
- `r15_destroy` (135-136): `-EBUSY` if any slot occupied; else destroy mutex+free. Matches R14's
  "failed records never reset/reuse" (no force-reset API).
- `unwrap` (42-44) delegates to the injected capability; the adapter never dereferences the wrapper
  itself — "可信unwrap能力", no arbitrary pointer validation.

## Bug table (field/ABI/Region/lifecycle)
**none.**
