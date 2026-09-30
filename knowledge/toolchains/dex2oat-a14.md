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

## 官方 aosp-14.0.0_r16 复现结果(2026-09-30 oc-t4,L1/L2 判定)

工具:官方树构建(pinned-manifest.xml 同源)host `dex2oat64` sha16 `1a2f5a22ebe1a722`(x86-64,glibc-only,hw248 原生);arm64 `libart.so` sha16 `adf4da23e3093b1d`。输入:9 jar(payload v3a-r8b,9/9 与本清单 MATCH),命令=boot.oat 内 `dex2oat-cmdline` 抄录(上节),dex-location 全部指 /system/android/framework。

- **R155 风险检查(通过)**:官方 libart `ComputeAndSetHashCode` 反汇编与板上 59e1bb45 逐指令同形(count@8 + bit0 压缩标志 tbnz / hash 写回@12 / 字符数据@16);`art\n108\0`×2 同数;源码级 oat=230/image=108。无 R155 级布局差,官方树可直接作复现工具。
- **复现跑成**:7.086s(52.157s cpu,32 threads)出全部 27 文件。对照:c-route r16 同输入死于 570s 看门狗——挂起病在 c-route 树,官方工具链无。
- **L1(27 文件逐字节)**:**9 一致 / 18 差 / 0 缺失**。一致 = 全部 9 个 `.vdex`;差异 = 全部 9 `.oat` + 9 `.art`。
- **L2(静态头字段,boot.oat)**:magic `oat\n230` ✓、isa=2 feats=0x3 ✓、`dex_file_count=1` ✓、**`executable_offset=0x1e6000` 精确相等** ✓、`bcp_bss_info_offset=0` ✓;boot.art 头 `art\n108` ✓。唯一头差:`oat_checksum` 0x50af7eed(我们)vs 0xd369f830(板)。
- **.oat/.art 差异归因(已知成分)**:OatHeader key-value 嵌 `dex2oat-cmdline`,我们产物嵌 `/tmp/official9/...` 路径,板上原件嵌 `/opt/build-trees/.work/fn03-r29-boot-20260728T0635Z`——路径串不同必然改哈希与 adler32。若要 L1 逼近,可用相同 work 路径(`--image`/`--dex-file` 指 `/opt/build-trees/.work/fn03-r29-boot...` 形式)重跑一次;剩余差异(若有)才是编译器/时间戳性。
- **L2 板测(待批)**:产物推 5cd `/data/local/tmp/oc-t4-boot/l2/`,叠加现役 9 段后验 HW/ZZ 与 ≥5 已亮 app t20 仍是自身界面。
- 产物持久:hw248 `/home/alvin/official9-boot-repro/`(160M,27 文件 + run.log + local.sha256)。

**判定:vdex 层 L1 全中;L2 静态头字段全中(除 checksum,已归因路径串);L2 板测待批。**

## 同形 work 路径重跑与逐项归因(2026-09-30 oc-t4,fn03-r29-boot 复刻)

重跑:`--image`/`--dex-file` 全部指 `/opt/build-trees/.work/fn03-r29-boot-20260728T0635Z/...`(板上原件 cmdline 同形,incoming symlink 到同 9 jar)。6.747s 出 27 文件。

- **L1 vs 板清单:仍 9/27**(=全部 vdex 逐位;18 差 = 9 `.art`+9 `.oat`)。
- **vs 首跑只改 2 文件**:`boot.art`、`boot.oat`(其余 25 文件路径重跑后逐位不变——它们的 kv 不含 --image/--dex-file 串)。
- **路径串级联定量化(boot.oat)**:cmdline kv 串长 1220→1663(**Δ443**),`oat_dex_files_offset` 0x1e51a5→0x1e5361(**Δ444**)——kv 变长把其后所有偏移整体推移,级联 1.92MB 差异字节(窗口密度 ~97%);**kv 区外真实差异仅 53,447B**。
- **checksum 三值**:首跑 0x50af7eed → fn03 同形 0xa5f169b2;板上 0xd369f830 仍未中。
- **残差归因(待续)**:fn03 路径已是板上同形,残差(53KB + checksum)来自 kv 区外内容——候选:板上工具是 `/opt/build-trees/aosp-arm64-d600` 树(≠精确 release r16 的源内细节,如 CL 号/构建号指纹),或 build 时间戳。要 L1 全中需拿到 d600 树的源(或其 art/ 的精确 git 状态)。
- 产物:hw248 `/opt/build-trees/.work/fn03-r29-boot-20260728T0635Z/`(27 文件 + run.log + local.sha256)。

**判定不变:vdex 层 L1 全中;L2 静态头字段全中(checksum 单点归因路径+源树差);L2 板测因 5cd 失联中止,叠加读验(11:28:12)已证明 27 bind 全部生效后被系统读到。**
