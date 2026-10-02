# Wall-2 option (b): add _74 alias exports to the Android ICU so tttext's version-74 dlsym resolves

Chosen because option (a) (per-app /system/usr/icu remap) is UNSAFE: the OH platform `libhmicuuc.z.so`, mapped in the
same app process, reads `/system/usr/icu` and requires ICU-74 data (`evidence/wall2-selection.txt`).

## What tttext dlsyms (the alias set)
tttext (`brk_open`) scandirs `/system/usr/icu` → version 74 → builds `<base>_74` and dlsyms it from the handle it got
from `dlopen("libicuuc.so")` / `dlopen("libicui18n.so")`. Base names seen in the apk strings (confirm the full set from
the relocations when building): `u_charType`, `u_hasBinaryProperty`, `ubrk_open`, `ubrk_close`, `ubrk_first`,
`ubrk_next`, `ubrk_setText` (break-iterator C API + a couple of `u_*` property calls).

## Build approach
Our deployed `libicuuc.so`/`libicui18n.so` are ICU 72 and export only `*_72`. Add `*_74` **aliases** pointing at the
`*_72` implementations, in the SAME library (dlsym on a RTLD_LOCAL handle searches that lib), via an alias object at the
re-link — no full ICU recompile:
  - generate `icu74_alias.S` with, for each needed symbol, `.set ubrk_open_74, ubrk_open_72` + `.globl ubrk_open_74`
    (or `__attribute__((alias("ubrk_open_72")))` in a .c), and add it to the final link of libicuuc.so (break-iterator
    + u_* live in libicuuc) — libicui18n only if tttext dlsyms an i18n symbol at _74.
  - this is a re-link of the existing ICU .o set + the alias object (AOSP external/icu, same toolchain as the deployed
    libicuuc), keeping the existing `*_72` cohort (our runtime binds `_72`). The lib then exports BOTH `_72` and `_74`
    for the aliased names — one library, no second copy.

## Caveats (why this needs validation, and the honest alternative)
1. **Semantic skew:** `*_74` names would run ICU-72 code. Safe only where the C ABI is unchanged 72→74 for the aliased
   functions (the break-iterator/property C API is stable, but this is a blanket promise for whatever tttext dlsyms —
   enumerate the real set from relocations before shipping).
2. **ICU data symbol:** if tttext also dlsyms the data symbol `icudt74l_dat` (strings show `icudt`+`%s%s`), our 72 lib
   has no `icudt74l_dat`; either alias it to the 72 data symbol (only if layout-compatible — risky) or rely on tttext's
   data-dir fallback. The loaded 72 code uses OUR 72 data (ICU_DATA=/system/android/etc/icu), which is correct for the
   _72 implementation — but confirm tttext does not hard-require the _74 data symbol.
3. **Honest alternative (c1):** since the OH platform is ALREADY ICU 74, aligning our Android ICU to 74 (rebuild
   libicuuc/libicui18n at 74 + icudt74l under /system/android/etc/icu + flip westlake_icu_overrides.cpp kExpectedSuffix
   "_72"→"_74" and its bind cohort) removes the version-skew lie entirely. Bigger change, but semantically clean. Weigh
   (b) minimal-but-skewed against (c1) larger-but-honest; (b) is the minimal per the dispatch's framing.
