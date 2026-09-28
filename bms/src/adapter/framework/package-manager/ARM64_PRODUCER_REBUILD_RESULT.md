# libapk_installer.so ARM64 producer rebuild — result

> Executes the plan in `02d.APK_Flow/L02.package-inspect/handoff/ARM64_PRODUCER_REBUILD_PLAN.md`.
> That plan assumed execution required "AlexPC or an equivalent OH_ROOT+clang15 machine" because
> 02d itself has no OH source tree. Gz02 (`ssh gz02`, already used for `liboh_adapter_bridge.so`
> and `install_plan` arm64 builds this same session) has `/data/source/oh-p7885-wukong100/out/wukong100`
> — a real, already-built arm64 (wukong100) OH platform tree — so it satisfies that requirement
> and was used directly instead of AlexPC.

## Changes
`build/inner/compile_apk_installer.sh` retargeted per the plan's diff:
- `arm-linux-ohos -march=armv7-a` → `aarch64-linux-ohos` (compile, minizip-C, and link steps)
- `OH_OUT=$OH/out/rk3568` → `$OH/out/wukong100`
- `ML=$SR/lib/arm-linux-ohos` → `$SR/lib/aarch64-linux-ohos`
- `libclang_rt.builtins.a` path: `.../lib/arm-linux-ohos/...` → `.../lib/aarch64-linux-ohos/...`
- Dropped `-Wl,--unresolved-symbols=ignore-all` (strict link, per plan's 验收判据 #2)
- **One correction beyond the plan's own diff**: `SYS_LIB` is `$OH_OUT/packages/phone/system/lib**64**`
  on the arm64 product, not `.../system/lib` (that's the arm32/rk3568 layout). The plan flagged
  "本地是否已有 arm64 product 的 OH ninja 构建输出" as the biggest unknown — confirmed present on
  gz02, and this `lib` vs `lib64` split was the one real surprise the recon turned up.

## Result (all 3 of the plan's 验收判据 met, on real hardware)
1. `file libapk_installer.so` → `ELF 64-bit LSB shared object, ARM aarch64` (12/12 sources compiled, 401K).
2. Strict link succeeded with `--unresolved-symbols=ignore-all` removed — every `NEEDED` (`libc.so`,
   `libshared_libz.z.so`, `libutils.z.so`, `libhilog.so`, `libcrypto_openssl.z.so`, `libssl_openssl.z.so`,
   `libc++.so`) resolved at link time, not deferred to runtime. SHA256
   `2091e64632875265b32ba02769e7753a2542231fbddf2610baf26c6a8543e1ae`.
3. Pushed to D600-B `5eab586000000000000000001123012c`, dlopen/dlsym probe (`src/tools/dlopen_probe.c`,
   cross-compiled the same way) confirmed on-device: `dlopen OK` / `dlsym OK:
   oh_adapter_install_apk_with_manifest @ 0x7f17b32b20`. Device artifacts cleaned up after the
   probe (no residue).

## Still not proven (out of scope for this plan)
- This `.so` is not yet the one deployed at `/system/lib64/libapk_installer.so` (current deployed
  SHA `4a51ac91e5...`, a different — likely arm32-shimmed or earlier-generation — build). Swapping
  it into the live BMS install path on a device is a separate, higher-risk `/system` staging
  operation (see `DEPLOY_SOP.md`) not attempted here.
- The `install_plan.c` judgment oracle (`install_plan/DEVICE_VERIFICATION.md`, same session) is
  still not wired into this library's `apk_installer.cpp`/`apk_manifest_parser.cpp` — they remain
  two independently device-verified components, not yet one production install pipeline.
- No BMS/installd patch-side arm64 rebuild (`base_bundle_installer.cpp.patch` etc.) attempted —
  plan explicitly scoped this rebuild to the installer producer only.
