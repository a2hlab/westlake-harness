# U17 ④ bridge gate-free `oh_anw_unwrap` — ready-to-apply patch (build-env gap noted)

#90, offline. cc-t3 (reassigned from cc-wiki; cc-wiki finishing the A1 jar).

## Frozen check (outer: stop if frozen)
`liboh_adapter_bridge.so` / `oh_anativewindow_shim.cpp` are **NOT in the frozen registry** (grep of FROZEN.md/frozen.json
for oh_adapter_bridge/oh_anativewindow/oh_anw/AdapterAnw = empty; the bridge is actively versioned — M5/M6, 84695d62/7daa5435).
So **no frozen-stop** — adding one export is in scope.

## U16 bridge base
U16 deployed/resident bridge = **`84695d62`** (u16-final-assembly expected-per-board / candidate-package); the M5/M6
candidate is **`7daa5435`** (native/package.json). native manifest `570e82e0`.

## The patch (the ONLY change; oh_anw_get_oh untouched)
- `patch/oh_anw_unwrap.cpp.add` — add `oh_anw_unwrap` right after `oh_anw_get_oh` (shim .cpp ~L813):
  `{ auto* a = as_adapter(aosp); return a ? a->oh : nullptr; }` — magic-check via `as_adapter` (==ANW1), **no
  `directPathLive` gate** (that gate is what made `oh_anw_get_oh` return 0 for a SurfaceView AdapterAnw in A0 window 19).
- `patch/oh_anw_unwrap.h.add` — the matching `extern "C"` decl in the shim .h (~L57).
- Exported via `extern "C"` default visibility (same as `oh_anw_get_oh`/`oh_anw_wrap`; the bridge uses no version script
  for these) → **export count +1**, no other symbol touched.

## Interface (for fd-plus + route-a backend to switch to it)
```c
// Surface.mNativeObject (the AdapterAnw*, from JNI GetLongField) -> real OHNativeWindow*, gate-free:
OHNativeWindow* ow = oh_anw_unwrap((struct ANativeWindow*)mNativeObject);  // nullptr if not an ANW1 shim
if (ow) { OH_NativeWindow_GetSurfaceId(ow, &id); /* -> SurfaceUtils::GetSurface -> NWeb */ }
```
Replaces the probe-only `*(void**)(p+0xc0)` raw-offset read (A0 window 19) and the gated `oh_anw_get_oh` (returns 0 unless
direct-path UNBOUND/LIVE). fd-plus `SurfaceFromJava` and the route-a cc-wiki backend both call `oh_anw_unwrap`.

## Gates to run at build (per outer)
x2 byte-identical; export count +1 (only `oh_anw_unwrap` added); every OLD function instruction-identical under address
masking; `abi_diff --calls` shows NO deletions; NEEDED unchanged; open_site unchanged; build log tee'd.

## Build-env gap (why this is a patch, not a built .so)
Byte-identical reproduction of the U16 bridge base (`84695d62`) needs that bridge's EXACT source snapshot + lock command +
toolchain. On hand: the built artifact only (hw248 vm-copy `bridge-84695d62`, and the local `_cc-wiki-b1-src` tree builds a
DIFFERENT bridge `c3c356aa` via `_cc-wiki-b1-build/{recipe,run-compile,run-link}.sh`). So either (a) point cc-t3 to the
U16 bridge reproducible build dir (source+lock command for 84695d62) and this patch applies + gates run there; or (b)
cc-wiki (owns the U16 bridge build env) applies these two adds to their U16 bridge source and runs the gates. The code is
final; only the byte-identical rebuild is blocked on the owner's build env.
