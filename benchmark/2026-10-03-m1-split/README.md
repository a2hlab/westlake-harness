# M1 split into its own file — `android_graphics_m1_copy.cpp`, built + A′-proven on a2hlab

#90, offline (build on a2hlab), **no deploy, frozen table untouched**. Per the M1 freeze dossier's preferred
option (`benchmark/2026-10-03-m1-freeze-dossier/evidence/split-plan.md`), the `[M1-COPY]` cross-copy
window/Surface rescue is lifted out of the shared `android_graphics_compat_shim.cpp` into its own translation
unit, so a future **U16** runtime can freeze just that file's source blob (after the 3-app re-verify) while
other shim fixes keep landing. This builds the split with the U13 runtime's own frozen recipe and proves it is
faithful. (`patch/` = the shim patch; `src/android_graphics_m1_copy.cpp` = the new file; `evidence/build.log`
= the tee'd build; `evidence/disasm-compare.txt` = the A′.)

## The split (design)
- **New file `src/android_graphics_m1_copy.cpp`**: the `m1_*` helpers (`m1_exec_range_contains`, `m1_is_bridge`,
  `m1_find_own`, `m1_collect_others`) + the entry `m1_native_window_from_other_copies`, now **external linkage**
  in `namespace android`. It references **no shim global** — the resolved bridge fn is passed in as a parameter.
- **Shim patch `patch/android_graphics_compat_shim.split.patch`** (against the N2 baseline `b94f69e4`): one
  file-scope forward declaration (`namespace android { void* m1_native_window_from_other_copies(void*(*)(int32_t), int32_t); }`)
  + one changed line in `oh_wm_get_native_window` (`return nw != nullptr ? nw :
  m1_native_window_from_other_copies(g_oh_wm_get_native_window_fn, sessionId);`). `g_oh_wm_get_native_window_fn`
  stays **file-static**, so the shim object is the baseline plus exactly that one call.

## Build (a2hlab, the U13 runtime's frozen recipe)
`recipe/split_a_prime.run.sh` sets the u13 "m1" variant's driver env and runs `head -505` of its *resolved*
`recipe.sh` (the exact `$CXX`/`$COMMON`/`$INC`/`$DEFS` + `-include libcxx_compat.h`, frozen OHOS clang,
`--target=aarch64-linux-ohos -O2 -std=gnu++17 -fno-rtti`), then compiles: the N2 baseline shim, the un-split M1
shim, the split shim (baseline+patch, same path for isolation), and the new `m1_copy.cpp`. Full log:
`evidence/build.log`.

## A′ proof (`evidence/disasm-compare.txt`)
**(0) Build-env fidelity — reproduced the deployed objects bit-for-bit.**
`shim_baseline.o == 40aa2f5f` (deployed baseline) and `shim_m1ref.o == 612236be` (deployed M1), byte-identical.
So the comparison below is against the *real* artifacts, not a lookalike.

**(1) The M1 scan logic is instruction-identical to 612236be.** Normalized disassembly (addresses/relocations
masked) of the two address-taken scan callbacks:
`m1_find_own` (56 insns) and `m1_collect_others` (75 insns) → **diff = 0 lines** vs 612236be; even the raw
encodings match (`a9bd7bfd f9000bf5 f9400415 …`). These contain the inlined `m1_is_bridge` /
`m1_exec_range_contains` — i.e. the whole cross-copy scan is bit-for-bit the same code.

**(2) `m1_copy.o` carries exactly the payload that left the shim**: `T android::m1_native_window_from_other_copies`,
the `m1_*` locals, the `[M1-COPY]` string, and the two `dl_iterate_phdr` relocations (= 612236be's two).

**(3) `shim_split.o` = baseline + one call, nothing else.** Full-object normalized disasm vs the baseline
compiled from the same path differs in **one contiguous region only** — the (inlined) `oh_wm_get_native_window`
site gaining the fallback call (`cbnz/ldr/bl` + ternary glue). No other function changed. And:
`m1 helper symbols = 0`, `[M1-COPY] strings = 0`, `dl_iterate_phdr relocs = 0`; the one new undefined symbol
`android::m1_native_window_from_other_copies` **matches** `m1_copy.o`'s exported `T` symbol → **the runtime links.**

**(4) The one expected, documented difference.** In 612236be the entry was *inlined* into
`oh_wm_get_native_window` (no standalone symbol); in the split it is a standalone external function reading its
`resolvedFn` **parameter** instead of the file-static global. That is the sole intended consequence of the TU
boundary (and is what keeps the shim at "+1 call"); semantics are unchanged (same scan, same rescue, same log).

## This round's rule
To split a fix out of a shared file for freezing, prove faithfulness at the layer the fix actually lives: build
with the artifact's **own frozen recipe** (so the deployed objects reproduce bit-for-bit as the anchor), show
the moved logic is **instruction-identical** (the address-taken callbacks here are exact), confine the host
file's change to **one call** (verified by a same-path baseline-vs-patched disasm diff), and confirm the new
**undefined↔defined symbol pair matches** so the link still resolves. The only allowed non-identity is the
glue forced by the TU boundary (inlining undone; a global read becomes a parameter) — name it explicitly.

## Files
- `patch/android_graphics_compat_shim.split.patch` — shim = baseline `b94f69e4` + file-scope decl + one call.
- `src/android_graphics_m1_copy.cpp` — the new translation unit (external `namespace android` entry + `m1_*`).
- `recipe/split_a_prime.run.sh`, `recipe/split_a_prime.inner.sh` — the a2hlab build (paths normalized to `$WORKSPACES`).
- `evidence/build.log` — the tee'd build (verbatim; workspace prefix normalized to `$WORKSPACES`).
- `evidence/disasm-compare.txt` — the A′ writeup; `evidence/{m1_copy,shim_split}.disasm.txt` — raw disasm;
  `evidence/{ref-612236be,cand-split}-m1_*.norm` — the normalized per-function proof inputs (diff = 0).

## Boundaries
Offline build on a2hlab (OrbStack was transiently wedged ~09:50–10:10 — not force-restarted, it self-healed;
the build ran after). **Not deployed; frozen table (`knowledge/frozen/`) untouched.** The `.o`/`.so` build
products are left in `build/` (git-ignored, not landed). Freeze of the `android_graphics_m1_copy.cpp` blob is
the outer's, into a **U16** runtime, after re-verifying the 3 apps (fd-uhabits/wikipedia/noice) on that build —
not U13. Sources read read-only: the N2 baseline shim (`westlake-harness-bms-deploy`), the M1 source
(`westlake-harness-t3 benchmark/2026-10-02-m1-session-slots`), the u13 build recipe + deployed objects
(`westlake-inputs/generations/u13-runtime-m1-v1`, `.work`).
