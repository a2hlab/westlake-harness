# U14 native_abi v2 = 7605812c + one `_ctype_` data export = `f8619ad5` (x2): exports exactly +1, 44/44 old functions instruction-equal, Realm replay 0 missing for mcdonalds and Element (calibrated: the deployed d2053066 reproduces both boards' `_ctype_`)

#90, native, offline. No board touched. Built on hw248 with the frozen clang feef13a3 in the same 58-char mirror root
as 7605812c. a2hlab not used.

## Why (from `2026-10-03-u13-first-fatal-clusters`, cluster C2b)

mcdonalds (`com.mcdonalds.app`) and Element (`im.vector.app`) both die at bind on
`relocating failed: symbol not found ... s=_ctype_ use_vna_hash=1 van_hash=50d63`, from librealmc.so and
librealm-jni.so respectively. Both packages are in the deployed 13-package native cluster (libapp_native_loader
eebd62f2).

**What the earlier model got wrong.** It said "compat not in scope + 7605812c has no `_ctype_`". That is still true,
but it was not the whole provider picture. This round's calibration (§3) finds the real providers in scope:
- the **RTLD_GLOBAL native_abi**;
- the libraries' own **NEEDED `liblog.so`** → `android/lib64/liblog.so` 8c81a937, which exports `__open_2`,
  `__strncpy_chk2`, `strtoll_l`, `strtoull_l` @@LIBC;
- **NEEDED `libandroid.so`** → `westlake_native/libandroid.so` ee2fb82c, which exports `__cmsg_nxthdr` @@LIBC.

None of them defines `_ctype_`. Both Realm libraries are `BIND_NOW`, so OH musl does not defer anything:
`dynlink.c` defers PLT/GOT only for `dso->lazy`, and `prepare_lazy` returns early on `DF_BIND_NOW`.

## 1. What changed (`src/`, `build_v2_hw248.sh`)

**Source.**
- `src/ctype_compat.c` is **byte-identical** to U13 compat's reviewed source (`2026-10-03-u13-compat-ctype/ctype_compat.c`,
  sha `2908c8c0…`, = its `sources.json` `candidate_source_sha256`).
- It `#include`s **AOSP android-14.0.0_r1 bionic e4df46f2 `upstream-openbsd/lib/libc/gen/ctype_.c` unmodified**:
  the 257-byte `_C_ctype_` table plus `const char *_ctype_ = _C_ctype_;`.
- The six AOSP inputs and the empty shim `ctype.h` are copied with their `sources.json` sha256 checked (all match).

**Version script.** `src/native_abi_v2.map` = the Gecko map `native_abi_gecko.map` with `_ctype_;` added to the
`LIBC { global: … }` node. That is the only change (`/usr/bin/diff`: one line).

**Recipe.**
- `build_v2_hw248.sh` = `2026-10-03-u14-native-abi-gecko/build_hw248.sh` (29303e3c, the 7605812c recipe) plus **one
  compile line**: `ctype_compat.c` with the same COMMON flags plus compat's two include dirs (the shim and openbsd
  `libc/include`).
- Only that object sees those `-I` flags, so no other object's header resolution changes.
- Linked after `gecko_abi.o android_dlopen_ext.o`. The hw248 sources `gecko_abi.c 09aef138`,
  `android_dlopen_ext.c 7337a393` and `native_abi_gecko.map 14bb2fbb` equal the repo's.

**Build ×2: `f8619ad5571c92cb3e9da3b8265ee41c17fa67db0a6aabeb9bfb89903e2a2239` both, rc 0, no compiler output**
(`evidence/nabi-v2-{a,b}.log`, teed on hw248).

## 2. Gates vs 7605812c (`gates.py` → `evidence/gates.txt`, `evidence/equiv-7605812c-vs-f8619ad5.txt`)

| gate | result |
|---|---|
| exports | 37 → 38: **added exactly `_ctype_@@LIBC`, removed 0** |
| old functions (`equiv.py`, address operands resolved) | **44/44 instruction-equal, 0 differ**, no new function; `.text` size identical (0x184c) |
| imports / NEEDED | unchanged / `libc.so` only |
| `_ctype_` ABI | 8-byte GLOBAL OBJECT, `R_AARCH64_RELATIVE` → LOCAL 257-byte `_C_ctype_` |
| table bytes | **equal to compat b8a87f6f's table and to the table parsed from AOSP ctype_.c (257/257)** |
| strings | 0 removed; added: the table's printable projection, `_ctype_`, `_C_ctype_`, the ctype source/debug path strings (same kind 7605812c already has for its own sources) |
| open sites | unchanged (no new function; equiv covers all code) |

## 3. Realm replay (`replay_v2.py` → `evidence/replay-realm.txt`)

**Model.** musl order (JMPREL, REL, RELA), with these providers:
- musl;
- RTLD_GLOBAL native_abi;
- the app's own libraries;
- the NDK API names;
- the **libz each app gets**:
  - Element: the private zlib `westlake_native/libz.so` 50b9ab6a (U11ZlibRoot, LOCAL_NS_PREFERED);
  - McDonald's: the platform libz shared by the bridge inherit, platform-pool `platformsdk/libz.so` 3c025525;
- the full exports of the two NEEDED libraries above.

**Inputs.** librealmc `b7efab75` (the board's McDonald's arm64 split; compat-ctype's consumer).
librealm-jni `7693a9d2` (extracted from the board APK; the same bytes in both apps).

| native_abi | mcdonalds librealmc | Element librealm-jni |
|---|---|---|
| **d2053066 (deployed in U12/U13), control** | **`_ctype_` [.rela.dyn]**: the boards' line | **`_ctype_` [.rela.dyn]**: the boards' line |
| 7605812c (U14 v1) | `_ctype_` | `_ctype_` |
| **f8619ad5 (v2)** | **0 missing** | **0 missing** |

- **Without the NEEDED libraries the model is wrong.** It would put `__open_2` / `__strncpy_chk2` first. The calibration
  row is what makes the v2 row credible.
- Every `@LIBC` import that resolves to native_abi is defined there at version LIBC: 21 for librealmc, 23 for
  librealm-jni, 0 mismatches. `_ctype_`'s `use_vna_hash=1 van_hash=50d63` is matched by `_ctype_@@LIBC`.

## 4. Prediction (first fatal)

| key | with v2 |
|---|---|
| mcdonalds | **first fatal moves past `_ctype_` (high)**: librealmc relocates, bind continues. Next wall unknown (Realm init, then the app's DI; its U12 terminal was the DI NPE caused by this bind failure). |
| fd-im-vector-app | **moves past `_ctype_` (high)**, same. Next unknown. |
| fd-meet (`__register_atfork`, normal domain) | 0. Left for U15 per the outer. |
| other native-cluster packages | 0 expected. Watch: `_ctype_` is now GLOBAL in their domain too; any library importing it now binds here. |

## Release (for cx-bms, slot swap)

- `$WORKSPACES/westlake-inputs/generations/u14-native-abi-v2/payload/android/lib64/westlake_native/libwestlake_native_abi.so`
  = **`f8619ad5571c92cb3e9da3b8265ee41c17fa67db0a6aabeb9bfb89903e2a2239`**.
- It replaces 7605812c in the **westlake_native/** slot only; westlake_flutter/ d2053066 is unchanged, as in v1.
- `builds/` (a, b) and `logs/` (teed) are there too, with `SHA256SUMS`.
- The hw248 build tree is kept under `$HW248_HOME/cc-t3-nabi-2026103/` (`out/nabi-v2-{a,b}`, `out/logs/nabi-v2-*.log`).

## Rules this round sets

- **A relocation replay must include the library's NEEDED closure as the domain resolves it**, not only the GLOBAL
  provider. Calibrate on the deployed build against the board's first-fatal line before predicting.
  - Realm's NEEDED liblog / libandroid supply 5 bionic symbols the GLOBAL native_abi lacks.
  - That is why the boards report only `_ctype_`.

## Files

- `src/`: `ctype_compat.c` (verbatim compat), `native_abi_v2.map`, `inputs/` (AOSP + shim, verbatim).
- `build_v2_hw248.sh`, `gates.py`, `replay_v2.py`.
- `evidence/`: `nabi-v2-{a,b}.log`, `gates.txt`, `equiv-7605812c-vs-f8619ad5.txt`, `replay-realm.txt`.
- `results.json`.
