# Fixed dex2oat for the OH 6.1 BMS route boot image

**Status: the most promising path, not yet confirmed.** It becomes the confirmed, final path only
when the reproduction below passes and the recipe, hashes and command line are recorded and frozen.
Until then nothing downstream (tagsoup, Gallery's MediaStore field) may be declared solved by it.

## Why this page exists

The board's boot image (9 segments) was produced by a dex2oat whose recipe was never recorded. Every
boot-class fix (tagsoup `Parser.setProperty`, Gallery's `MediaStore.Images.Media.EXTERNAL_CONTENT_URI`)
then turned into hours of archaeology: a static cross-built dex2oat from a branch commit, patched
exemptions, qemu runs. That broke the AGENTS.md rule that every runtime artifact keeps its source,
patches, toolchain hashes and build script.

## Target versions (measured)

- Board `libart.so` 59e1bb45: image version 108, oat version 230 (oc-t4, 2026-09-30).
- AOSP `android-14.0.0_r1`, `_r10`, `_r16`: `kImageVersion` 108, `kOatVersion` 230 (read from the
  art trees on hw248). `_r29` is 239 and `_r50` is 241, so they do not match.
- Chosen: **android-14.0.0_r16**, the newest tag with oat 230 found on hw248.

## Inputs (measured 2026-09-30 10:50)

The boot image is **9 segments over 9 jars**, in this order of files under
`/system/android/framework/`: core-oj (boot.*), core-libart, core-icu4j, bouncycastle, apache-xml,
okhttp, framework, oh-adapter-framework, adapter-mainline-stubs. The 9 jars and all 27 image files
(`arm64/boot*.{art,oat,vdex}`) are **byte-identical on 5cd, 5ea and 61b**; the SHA-256 list is in
`boot-image-inputs.sha256`. Earlier reproduction attempts fed 5 jars, which is not the board's input
set. The 715/723 String sizes that suggested the boards differ were garbage reads.

## Risks, and how each is closed

1. **The board libart carries our own patches.** `libart.so` 59e1bb45 is the R155 build (route-a,
   from pr03-74e6-portable); its source and patch series were never archived, and rebuilding from the
   frozen inputs produced a different libart (be688d0f, DIGEST E.7). If those patches change object
   layout or the image format, an official dex2oat's image will be rejected. Checks, in order:
   (a) compare the layout-defining constants of the board libart with an official android-14.0.0_r16
   arm64 libart built from the same tree (Thread offsets used by the asm entrypoints, mirror class and
   object sizes, ImageHeader/OatHeader layout); the String layout already matches (oc-t4);
   (b) the board test in step 2 of the acceptance levels. If either fails, recover the R155 patch set
   (hw248 Westlake build archives, real-work) and build dex2oat with the same patches.
2. **Byte-identical reproduction may not be possible** (different tag or flags in the original run).
   Acceptance has two levels:
   - L1 (ideal): all 27 files byte-identical to `boot-image-inputs.sha256`.
   - L2 (minimum): oat version 230 / image version 108, the boot-image checksum and header fields that
     libart validates match, and in a short board window (overlay the 27 files, then roll back) HW,
     ZigZag and at least five currently lit apps still show their own UI at t20.
3. **Input jars might differ between boards**: checked, they do not (see Inputs).

## Recipe

Machine: hw248 (32 cores, 62 GB). Tree: `/home/alvin/aosp-14.0.0_r16-dex2oat`.

```sh
export REPO_URL=https://mirrors.tuna.tsinghua.edu.cn/git/git-repo
repo init --repo-rev=stable -u https://mirrors.tuna.tsinghua.edu.cn/git/AOSP/platform/manifest \
  -b android-14.0.0_r16 --depth=1 --no-clone-bundle
repo sync -c -j16 --no-tags --no-clone-bundle --fail-fast
# sync finished 2026-09-30 10:55, 111 GB
repo manifest -r -o pinned-manifest.xml     # pinned project revisions, copy kept next to this page
source build/envsetup.sh && lunch aosp_arm64-userdebug
m -j32 build-art-host libart                 # host dex2oat set + arm64 libart for the R155 layout check
```

## Build result (2026-09-30 11:12, 20 min on hw248)

`#### build completed successfully (20:11 (mm:ss)) ####`, 0 FAILED lines.

| artifact | sha256 (first 16) | notes |
|---|---|---|
| `out/host/linux-x86/bin/dex2oat64` | `1a2f5a22ebe1a722` | x86-64 PIE, only glibc deps (libdl, libpthread, libm, librt, libgcc_s, libc); runs natively on hw248 |
| `out/target/product/generic_arm64/apex/com.android.art/lib64/libart.so` | `adf4da23e3093b1d` | official arm64 libart for the R155 layout comparison; contains the `230` oat version string |

## To record when done

- Pinned manifest (`repo manifest -r`) committed next to this page.
- SHA-256 of `dex2oat64` and every host library it loads (`ldd`), and of the prebuilt clang used.
- The exact dex2oat command line that reproduces the board's 9 segments, taken from the board
  `boot.oat` key-value store (`dex2oat-cmdline`), and the per-segment checksum comparison.
- Once the 9 segments reproduce, register the tool in `knowledge/frozen/` so it cannot drift.

## OatHeader key-value(板上 boot.oat 实测,2026-09-30 oc-t4)

来源:5ea `/system/android/framework/arm64/boot.oat`(sha16 25d92cf7df9c86ca,= 清单 arm64/boot.oat 行),ELF 内 oat 段 @0x1000,`oat\n230\0`。

- `[dex2oat-cmdline]`(逐字节抄录):
  `/opt/build-trees/aosp-arm64-d600/out/host/linux-x86/bin/dex2oat64 --android-root=/system --instruction-set=arm64 --base=0x70000000 --compiler-filter=speed --runtime-arg -Xms64m --runtime-arg -Xmx512m --runtime-arg -Xverify:none --image=<work>/products/arm64/boot.art --oat-file=<work>/products/arm64/boot.oat --dex-file=<work>/incoming/core-oj.jar --dex-location=/system/android/framework/core-oj.jar --dex-file=…core-libart… --dex-file=…core-icu4j… --dex-file=…okhttp… --dex-file=…bouncycastle… --dex-file=…apache-xml… --dex-file=…adapter-mainline-stubs… --dex-file=…framework… --dex-file=…oh-adapter-framework…`(每个 jar 同款 dex-file/dex-location 对;work = `/opt/build-trees/.work/fn03-r29-boot-20260728T0635Z`,原产物路径)
- `[compiler-filter]=speed`、`[concurrent-copying]=false`、`[debuggable]=false`、`[native-debuggable]=false`、`[requires-image]=true`、`[apex-versions]=`(空)
- 9 jar 顺序(bootclasspath 与 cmdline 一致):**core-oj → core-libart → core-icu4j → okhttp → bouncycastle → apache-xml → adapter-mainline-stubs → framework → oh-adapter-framework**
- isa features:OatHeader bitmap = 0x3(arm64);dex2oat.cmdline 无显式 `--instruction-set-features`(即默认/detected)
- 其余头字段:oat_checksum 0xd369f830、dex_file_count=1(boot.oat 自身,其余 jar 各在 boot-<name>.oat)、executable_offset 0x1e6000、bcp_bss_info_offset 0

注:此前 5-jar 顺序(core-oj/core-libart/core-icu4j/stubs/framework)缺 4 jar 且顺序不同(okhttp/bouncycastle/apache-xml 在 stubs 前)——一切复现以本节 9-jar 顺序为准。
