# U14 native_abi for Gecko: stopped at the reproduction gate. d2053066's toolchain is Linux-only and cannot be re-run on the Mac; the Mac build matches every loaded byte but not the file bytes

#90, native, offline. Nothing was built for deployment and nothing went to a board. **Status: stopped as instructed**
("faithfully reproduce d2053066 ×2 first; if it does not match, stop and report the difference"). The 10 exports were
**not** added.

## 1. Source and build receipt of d2053066: found

| | |
|---|---|
| source | `westlake-harness-bms-deploy` `benchmark/2026-09-30-n4-native/src/{native_abi.c, bionic_stdio_compat.c, native_abi.map}`, committed (44b8e0b0ad; clean in that tree: native_abi.c `6cf69a57`, bionic_stdio_compat.c `e5cfec3d`, map `362acdc8`). Not in master's tree. |
| recipe | `benchmark/2026-09-30-n4-native/build-abi.sh` (`5d66488b`): frozen OH toolchain + sysroot under `bms/src/.work/b68-generation/.work/product-tls-generation/frozen`, `-O2 -g`, `-Wl,-z,global`, `--version-script=native_abi.map` |
| receipt | `build-abi.log` in that directory: `d20530661a30b8af…` = the deployed file |
| what d2053066 itself says | DWARF `comp_dir` = the bms-deploy repo root (`$WORKSPACES/westlake-harness-bms-deploy`); **producer of both CUs = `OHOS clang 15.0.4 (llvm-project feef13a3…)`** (`evidence/dwarf-producers.txt`) |

## 2. Why a faithful reproduction is not possible on the Mac

- The recipe's compiler, frozen `toolchain/bin/clang-15`, is a **Linux x86-64 ELF**. It carries `feef13a3`, the
  producer recorded in d2053066 (`evidence/toolchains.txt`). Running `repro_d2053066.sh` (the committed build-abi.sh,
  cwd = bms-deploy root, output redirected) on the Mac fails with `clang-15: cannot execute binary file`
  (`evidence/repro-original-toolchain-on-mac.log`).
- The original was evidently built in a Linux VM that mounts the Mac paths at the same `/Users/...` location, i.e.
  OrbStack / a2hlab. The DWARF `comp_dir` and file names are Mac paths.
- **No local Mac clang is `feef13a3`:**
  - DevEco OH SDK `llvm` is `99548401`;
  - the generation toolchain `u10.1-…/toolchain/clang` is `99548401`;
  - BiSheng is `2ed87471`.

## 3. The closest Mac build and exactly how it differs (`mac_attempt.sh`, `evidence/`)

**What was held fixed and what changed.**
- Same flags, cwd, sources, map and sysroot, and the same clang resource dir (the frozen toolchain's
  `lib/clang/15.0.4`, so header paths match).
- Only the compiler and linker binaries are DevEco's `99548401` (clang + ld.lld 15.0.4).

**Result.** Built twice: **`1e2726d9a091…`, byte-identical**, ≠ d2053066.

| check | result |
|---|---|
| functions (`equiv.py`, every address operand resolved) | **31/31 instruction-equal** |
| loaded bytes (`elf_load_and_symtab.py`): all 4 PT_LOAD segments, with only the 20-byte build-id descriptor and the unused `e_shoff` masked | **all 4 SAME** |
| allocated sections | `.text .rodata .data .data.rel.ro .dynsym .dynstr .gnu.version .gnu.version_d .hash .gnu.hash .rela.dyn .rela.plt .got .got.plt .plt .dynamic .eh_frame(_hdr) .init(_array) .fini(_array) .note.ohos.ident`: **all SAME** |
| differing sections | `.comment` (compiler version strings), `.debug_str` and `.debug_str_offsets` (the CU producer string `99548401` vs `feef13a3`), `.note.gnu.build-id` (hash of the above), `.symtab` (2 `$d` mapping-symbol values inside `.debug_str`) |

**Reading of the result.** On the Mac, d2053066 can be reproduced **behaviour-identically** (every byte the loader maps
and every instruction), but not **byte-identically**. The only differences are the compiler identity strings and their
hashes. By your gate (×2 faithful match), that is a stop.

## 4. android_dlopen_ext semantics source: found (for the next step)

Lookup order: local, then a2hlab (skipped: window period), then hw248.
- Local has only NDK 23's `dlext.h`, not the 14 tag.
- hw248 `aosp-14.0.0_r1-art/bionic` (also identical in the r16 tree), copied into `evidence/aosp14r1-bionic/`:
  - `libdl/libdl.cpp` (`57a9079a`): `android_dlopen_ext(filename, flag, extinfo)` only forwards to the linker's
    `__loader_android_dlopen_ext(filename, flag, extinfo, caller_addr)`;
  - `libc/include/android/dlext.h` (`058542f0`): the flags.
- The real semantics are in `linker/dlfcn.cpp` (`bd730714`) / `do_dlopen`: extinfo flags `USE_LIBRARY_FD`,
  `USE_NAMESPACE` 0x200, `FORCE_LOAD` 0x40, `RESERVED_ADDRESS*`, …
- So a faithful route-A `android_dlopen_ext` has to map those flags onto OH musl's `dlopen` / `dlopen_ns`, not ignore
  `extinfo`. DIGEST 683 (PPSSPP) is the same point.

## 5. Ways forward (outer's choice)

1. **Wait for the window to end and run the committed recipe on a2hlab.** That is where the original evidently ran:
   same Linux clang `feef13a3`, same `/Users` mount paths. Expected byte-identical ×2; then add the 10 exports there.
2. **hw248 (Linux x86-64) with the frozen toolchain** copied over, plus `-fdebug-compilation-dir` / `-ffile-prefix-map`
   to the original Mac paths. Byte-identity is likely but not certain, and it adds two flags the original did not
   have.
3. **Accept the Mac toolchain as the baseline**, with the evidence above: 31/31 functions, all loaded bytes equal. Then
   add the 10 exports on the Mac, with `1e2726d9` (not d2053066) as the per-function diff reference. The file-byte
   identity to d2053066 is lost by design.

For any of these, the export work is unchanged:
- implementations from `webview_bionic_shim.c` 532633d (8), `bionic_assert_compat.c:133` (`__assert2`), and
  `android_dlopen_ext` written to the AOSP linker semantics above;
- gates: exactly +10 dynamic exports at version `LIBC` (vna_hash `0x50d63`), open sites unchanged, strings only the
  implementations' own;
- `reloc_order.py` musl-order replay of libmozglue/libxul: 0 unresolved, except `plugin-container.__libc_init`.

## Rules this round sets

- **Check a native artifact's DWARF producer against the recipe's toolchain before trying to reproduce it.** The
  receipt named a toolchain directory; only the binary's own `DW_AT_producer` and `.comment` say which compiler
  revision actually ran, and on which host type.
- **Report "behaviour-identical" separately from "byte-identical".** Compare PT_LOAD bytes (build-id and `e_shoff`
  masked), allocated sections and resolved instructions, so a toolchain-identity difference is not mistaken for a
  code difference, and vice versa.

## Files

- `repro_d2053066.sh`: runs the committed recipe in place, output redirected, log teed.
- `mac_attempt.sh`: the Mac build.
- `elf_sections.py`, `elf_load_and_symtab.py`.
- `evidence/`:
  - `dwarf-producers.txt`, `toolchains.txt`;
  - `repro-original-toolchain-on-mac.log`, `mac-attempt-build.log`;
  - `sections-*.txt`, `ptload-symtab-*.txt`, `equiv-*.txt`;
  - `aosp14r1-bionic/`.
- `results.json`.
- Build outputs: `$WORKSPACES/westlake-inputs/generations/u14-native-abi-gecko/` (`mac-a`, `mac-b`, `SHA256SUMS`;
  `repro-a/b` hold only the failed logs).
