# ART_DEFS diff: recipe device libart vs T3b Soong host dex2oat (why T5b still aborts)

Offline follow-up to the formal-T6 FAIL (T5b, board ACK 2026-09-30). The T5b boot image is RB-off
(`concurrent-copying=false`) yet HelloWorld's app process aborts on the board R155 libart with
`Invalid address for an implicit NullPointerException check: 0x0` at `const-string` / `new-instance`
in AOT-compiled boot-image code (`boot-oh-adapter-framework.vdex`), cppcrash-13606 / -14186. Operational
side ruled out on-board (v3c resident image + identical restart/socket procedure → HW lights;
`t6-formal-t5b/`). So the difference is the boot image. This compares the `-D` flags.

## Sources compared
- **recipe device libart** = `recipe/adapter/build/inner/cross_compile_arm64.sh:201` `ART_DEFS` (what the
  board R155 device libart `8c2796fc`/`59e1bb45` was built with).
- **T3b Soong host dex2oat** = hw248 `aosp-14.0.0_r1-art/out/soong/build.ninja`, module
  `m.libart_linux_glibc_x86_64_static.cFlags1` (line 9165556) and `libart-compiler…cFlags1` (9254348) —
  the host `dex2oat64` (204,735,528 B, oc-t4 T3b `89b8b3d4`) that produced T5b.

## Diff table (arm64-codegen relevance)

| define | recipe device | T3b Soong host | codegen-relevant? | verdict |
|---|---|---|---|---|
| ART_DEFAULT_GC_TYPE_IS_CMS | set | set | yes (GC/collector) | **same** |
| (read barrier) | not defined = off | not defined = off | yes | **same** (T5b kv concurrent-copying=false) |
| ART_FRAME_SIZE_LIMIT | 1736 | 1736 | yes (frame layout) | **same** |
| ART_STACK_OVERFLOW_GAP_* | 8192 | 8192 | yes (stack) | **same** |
| ART_ENABLE_CODEGEN_arm64 | set | set | yes | **same** (host also has arm/x86/riscv64 backends — does not change arm64 output) |
| IMT_SIZE | =43 (redundant) | not -D'd | yes (Class IMT layout) | **same** — `art/runtime/imtable.h:37 static constexpr size_t kSize = 43` is hardcoded in the source, not `#define IMT_SIZE`; both build with 43 |
| ART_BASE_ADDRESS | 0x70000000 | 0x60000000 | image base default | **not the cause** — `gen_boot_image.sh` passes `--base=0x70000000` (overrides), and v3c's working image was made by a host dex2oat the same way (host default base + --base) |
| ART_DEFAULT_COMPACT_DEX_LEVEL | not set | =fast | dex layout | **not the cause** — T5b `.vdex` are 9/9 byte-identical to the board reference (oc-t4), i.e. the dex output is identical, so compact-dex level changed nothing |
| ART_BASE_ADDRESS_MAX/MIN_DELTA | not set | ±0x1000000 | ASLR relocation clamp | host-only; not codegen output |
| ART_TARGET / ART_TARGET_LINUX / ANDROID_HOST_MUSL / NDEBUG | set (device) | (host build; NDEBUG set globally by Soong for release) | host-vs-target normal | expected |
| ANDROID_STRICT / _LIBCPP_… / USE_D8_DESUGAR / ART_STATIC_LIBART_COMPILER | — | set | host build hygiene | not codegen output |

## Verdict: the arm64-codegen `-D` are effectively IDENTICAL

Every define that changes the arm64 code / image layout the board R155 libart consumes — GC type, read
barrier, frame-size limit, stack gap, IMT size, codegen backend — matches. The remaining differences are
host-vs-target normals, `--base`-overridden, no-ops (vdex identical), or host build hygiene.

**Per the outer-ring branch (diff empty ⇒ check the ART source version):** the T5b incompatibility is NOT
the `-D` flags. It is the **ART source** the host dex2oat was built from. T5b's dex2oat is
`r1 + 21 T1 patches` (Soong); the board R155 was built from the b6-r155 recipe's ART source. The failure
signature — a spurious implicit-NPE check at 0x0 on `const-string` / `new-instance` in AOT boot-image code,
i.e. a resolved-string/type the compiler emitted as "present" that the board R155 libart reads as null —
is a **codegen / boot-image-reference difference between the two ART sources**, not a `-D` difference.

### Recommended next step (offline)
1. `check_series.py` proved r1+21 is byte-identical to art-hanbin on 16 of the 19 diff files — but the
   crash is in AOT-compiled code, so diff the **codegen + image-writer + implicit-null-check** sources
   between r1+21-patches and the recipe's R155 ART source:
   `art/compiler/optimizing/code_generator_arm64.cc`, `.../nodes.*` (null-check / bounds), 
   `art/dex2oat/linker/image_writer.cc` (resolved strings/types), `art/runtime/oat_file.cc` /
   `class_linker.cc` (DexCache resolved arrays), and how boot-image string/type references are patched.
2. If art-hanbin ≠ the true R155 source, the fix is to build the host dex2oat from the **exact** R155 ART
   source the recipe used (or add the missing codegen patches to the T1 series), then regenerate + retry.
3. T4 verified `art_quick` Thread/mirror offsets match between r1+21 libart and board R155, but did NOT
   cover how AOT code loads boot-image-resolved strings/types — that is the uncovered surface here.
