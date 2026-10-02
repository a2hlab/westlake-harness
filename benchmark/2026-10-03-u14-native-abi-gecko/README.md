# U14 native_abi for Gecko: d2053066 reproduced on hw248 with its own clang (all diffs path-only), then +10 LIBC exports = 86882caf; libmozglue/libxul replay 0 missing; two items for the outer (a new open site, and `__loader_android_dlopen_ext` has no provider)

#90, native, offline. Nothing went to a board. Route B (outer, 03:23): hw248 with the same frozen clang-15; a2hlab was
left to the executor.

## 1. Faithful reproduction of d2053066 (hw248): passes the outer's criterion

**Toolchain check.** hw248's copy of the frozen `clang-15` reports `OHOS (dev) clang version 15.0.4 (llvm-project
feef13a36e78…)`. That equals d2053066's `DW_AT_producer` for both its CUs. The clang-15 (`b107ce03`) and lld
(`8583bdc8`) binaries are byte-identical to the Mac copies.

**Setup.**
- The bms-deploy layout is mirrored on hw248 under a root of the **same length** as the original (58 chars):
  `$HW248_HOME/cc-t3-nabi-2026103/westlake-harness-bms-deploy`.
- Only what the recipe reads is copied, at its original relative paths: frozen `toolchain/{bin/clang-15, clang, lld,
  ld.lld, lib/libxml2*, lib/aarch64-linux-ohos, lib/clang/15.0.4/{include, lib/aarch64-linux-ohos}}`, `sysroot`,
  `n3-native/flutter/include`, and the n4-native sources + `build-abi.sh`.
- `build_hw248.sh` runs build-abi.sh's compile/link lines verbatim, with cwd = root and output to the original default
  `bms/src/.work/n4-native/abi`. Its first line, `check_frozen.py`, is a source gate and is not run.
- One environment failure (lld could not find `libunwind.a` because `toolchain/lib/aarch64-linux-ohos` was not yet
  copied) was fixed by copying that directory. No source or link failure.

**Result.** Built twice: **`554bf6bc563ff7805f2e69a179f7e12f44946694fc9afb7a9c19922ec613c923`**, byte-identical.

Against d2053066 (`evidence/faithful-554bf6bc-vs-d2053066.txt`, `evidence/faithful-diff-offsets.txt`):

| check | result |
|---|---|
| all allocated sections, `.comment`, the 4 PT_LOAD segments (build-id masked) | **byte-identical** |
| after replacing each file's root path (6 occurrences each) with a same-length placeholder and masking the build-id | 1758 bytes still differ, **all in non-allocated sections**: `.debug_line` 20, `.debug_line_str` 573, `.debug_str` 1065, `.debug_str_offsets` 86, `.symtab` 14 (full offset list in `faithful-diff-offsets.txt`) |
| why they remain | lld places merged debug strings by content, so a different path string moves strings and every offset that points at them. `.symtab`'s 9 differing entries are all `$d` mapping symbols inside `.debug_str` / `.debug_line_str`. |
| proof they are path-only (`dwarf_equal.py`) | `.debug_str` (139) and `.debug_line_str` (23) string multisets are **equal** after the root placeholder; `llvm-dwarfdump --debug-info --debug-line` with strings resolved: 4229 vs 4229 lines, **0 differing** |

The earlier Mac attempt (`1e2726d9`, DevEco clang 99548401) is kept as history in `mac_attempt.sh` / `evidence/*mac*`.
It also differed in `.comment` (compiler identity); the hw248 build does not.

## 2. +10 exports: `86882caf`

**What was added.**
- `src/gecko_abi.c`, one new object linked after `native_abi.o` / `stdio.o` (the original two sources are untouched).
  Bodies are copied verbatim:
  - `__gnu_strerror_r`, `__open_2`, `__cmsg_nxthdr`, `strtoll_l`, `strtoull_l`, `__strncpy_chk2`,
    `__pthread_cleanup_push/pop`: `webview_bionic_shim.c` @532633d (lines 1481, 1619, 1630, 1680/1686, 1749,
    1855–1883);
  - `__assert2`: `bionic_assert_compat.c` @e2b0bf6:133;
  - `android_dlopen_ext`: AOSP 14 r1 `bionic/libdl/libdl.cpp` 57a9079a:66–71 + 134–138, verbatim. It is a weak
    definition that only forwards to the weak `__loader_android_dlopen_ext(filename, flag, extinfo, caller)`;
    `android_dlextinfo` is passed through, so it is declared opaque.
- `src/native_abi_gecko.map`: the original map with these 10 names added inside `LIBC { global: … }`.

**Build.** Same recipe on hw248, built twice: **`86882caf60b821d526cc41034db923484cf4f42298b21e28ef0ebce1c43373d3`**,
byte-identical, no compiler warnings (`evidence/hw248-gecko-{a,b}.log`). Paths cancel because both builds use the same
root.

### Gates, faithful `554bf6bc` → `86882caf`

| gate | result |
|---|---|
| exports | **exactly +10, 0 removed**, all `@@LIBC`: 9 GLOBAL, plus `android_dlopen_ext` WEAK as AOSP defines it. Version definitions unchanged: BASE, `LIBC` (index 2), `LIBC_O`. `elf_hash("LIBC") = 0x50d63` = libmozglue's `vna_hash`. |
| imports | **+16, 0 removed**, all in musl except one: `open strerror strerror_r strtoll strtoull memset` (the bodies), `pthread_key_create/delete pthread_getspecific/setspecific pthread_once malloc realloc free memcpy` (compiler-rt emutls, see below), and **`__loader_android_dlopen_ext` WEAK** |
| strings | **only the implementations' own**: 5 text strings (`%s:%d: %s: assertion "%s" failed`, `Unknown error %d`, the `__open_2` / `__strncpy_chk2` diagnostics); 0 non-text |
| functions (`equiv.py`) | 30/31 old functions instruction-equal. 1 changed: `__emutls_unregister_key` (compiler-rt, 1 → 12 insns). New (13): the 10 export functions, plus emutls `__emutls_get_address`, `emutls_init`, `emutls_key_destructor`. |
| open_site_scan | 0 → **1**: `android_dlopen_ext → __loader_android_dlopen_ext` (path/flags/extinfo from the caller). **Not "no new open site"**; see item B below. |
| musl-order replay (`replay_with_abi.py`, the real 86882caf as the provider, plus a version check) | **libmozglue and libxul (fennec + firefox) and every other Gecko library: 0 unresolved**, except `libplugin-container.__libc_init` (child-process executable). No version mismatches. Control: the same replay against 554bf6bc still stops libmozglue at `__gnu_strerror_r`, as on the board. |

**Where the emutls change comes from.** The verbatim `__pthread_cleanup_push/pop` keep a `static __thread` list head.
The OHOS target compiles `__thread` as emulated TLS, so compiler-rt's emutls is linked in; that is why
`__emutls_unregister_key` is no longer a 1-instruction stub. That behaviour comes from compiler-rt and the recipe's
flags, not new code of ours.

## Two items for the outer

**A. Accept the emutls change?** It is a direct consequence of copying `__pthread_cleanup_*` verbatim under the
original flags. The alternative, compiling `gecko_abi.c` with native ELF TLS, would add a flag the recipe does not
have.

**B. `android_dlopen_ext` per the AOSP semantics forwards to a symbol no route-A provider defines.**
- `__loader_android_dlopen_ext` is defined by none of OH musl, libbionic_compat 015aa3a6, native_abi or the android
  libc stub. It is AOSP's linker, and route A has none.
- As in AOSP, the reference is weak, so loading succeeds (the replay is green). But **a call resolves to address 0 and
  crashes**.
- The deployed libbionic_compat's own `android_dlopen_ext` (disassembled) uses the same forward **when the symbol
  exists**. Otherwise:
  - empty extinfo or `extinfo->flags == 0` → plain `dlopen`;
  - else an error path.
- Per the instruction this build keeps the pure AOSP forward. Whether libxul calls `android_dlopen_ext` before t20 is
  not determined statically.
- If the outer wants the bionic_compat behaviour, it is a 1-function change and a rebuild ×2; the exports gate is
  unchanged.

## Deployment scope: which native_abi copy, and can the two meet in one process? (added after the outer's 03:5x note)

The board has two copies of `libwestlake_native_abi.so`, both **d2053066** (outer's read on 61b):
`westlake_native/` and `westlake_flutter/`.

- **This build (86882caf) replaces only `/system/android/lib64/westlake_native/libwestlake_native_abi.so`.**
  - firefox (`org.mozilla.firefox`) and fd-fennec_fdroid (`org.mozilla.fennec_fdroid`) are in the native-cluster list
    (`app_native_loader.c:62-66`, 13 packages).
  - `westlake_stock_host_main.c:330-340` `dlopen_ns`es `westlake_native/libwestlake_native_abi.so` RTLD_GLOBAL for
    native domains, and `westlake_flutter/libwestlake_native_abi.so` for Flutter domains.
- **`westlake_flutter/libwestlake_native_abi.so` stays d2053066.** No Flutter package needs these 10 symbols; the
  Flutter EGL fix is in the Flutter-private libandroid (`2026-10-03-u14-flutter-libandroid`).
- **The two copies are never in the same app namespace.**
  - Each app domain loads exactly one ABI path (the host's ternary above).
  - Selection is exclusive: `ANL_Dlopen` sets `flutter_selected` first and `native_selected` only if not
    flutter-selected (`app_native_loader.c:449-452`).
  - The two package lists are disjoint (6 Flutter: fluffychat, immich, kitchenowl, aves.libre, saber, localsend;
    13 native: anki, unciv, organicmaps, nextcloud, mcdonalds, mindustry, emn8, element, firefox, fennec, vlc, ppsspp,
    shatteredpixeldungeon; intersection empty).
  - So a Gecko process only ever sees the `westlake_native/` copy, and a Flutter process only the `westlake_flutter/`
    copy.
- **Standard.** This build already followed the outer's (A′) route: hw248, frozen clang feef13a3, faithful
  554bf6bc first. The two outer items above (A emutls, B `android_dlopen_ext` target) are still open.

## Prediction (first fatal)

| key | with 86882caf |
|---|---|
| firefox, fd-fennec_fdroid | **The libmozglue relocation wall goes (high).** libxul's relocation is also clean statically. Next first fatal: unknown Gecko init. If libxul calls `android_dlopen_ext` early, the next first fatal is a SIGSEGV at address 0 from `android_dlopen_ext` (item B). Lit: low. |
| the other native-cluster packages (anki, unciv, organicmaps, nextcloud, mcdonalds, mindustry, …) | 0 expected. Watch: they now find these 10 symbols in the GLOBAL ABI DSO. |
| everything else | 0 (native_abi is only GLOBAL in the native/flutter domains) |

## Files

- `build_hw248.sh` (the recipe on hw248, optional extra objects + map); `src/gecko_abi.c`, `src/native_abi_gecko.map`.
- Checks:
  - `path_equal.py` (placeholder + build-id byte compare, offset list by section);
  - `dwarf_equal.py` (string multisets + resolved dwarfdump);
  - `elf_sections.py`, `elf_load_and_symtab.py`;
  - `replay_with_abi.py` (musl-order replay against a real build + version check).
- History: `repro_d2053066.sh`, `mac_attempt.sh`.
- `evidence/`:
  - `faithful-*` (554bf6bc vs d2053066);
  - `exports-imports-*`, `equiv-*`, `strings-*`, `open-sites-*`, `replay-with-86882caf.txt` (86882caf gates);
  - `hw248-*.log` (teed build logs ×4);
  - `aosp14r1-bionic/`, `dwarf-producers.txt`, `toolchains.txt`, the Mac-attempt evidence.
- Artifacts: `$WORKSPACES/westlake-inputs/generations/u14-native-abi-gecko/` (`hw248-repro-{a,b}`, `hw248-gecko-{a,b}`,
  `mac-{a,b}`, `SHA256SUMS`, `logs/`). The hw248 mirror is kept at `$HW248_HOME/cc-t3-nabi-2026103/`.
