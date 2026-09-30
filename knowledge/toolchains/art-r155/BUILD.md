# art-r155 构建记录(T3,2026-09-30 oc-t4)

## T3b(读屏障关 + GC=CMS,2026-09-30 22:21,oc-t4)

背景:板上 R155 libart 是**关读屏障**编的(`ART_USE_READ_BARRIER=false`),`XGcOption` 空选项分支把 collector_type 写 2 = CMS(cx-bms 二进制实锤,板 ACK(91) 21:38/21:56)。T3 在 r1 树按默认开了读屏障 ⇒ 生成物 kv `concurrent-copying=true` vs R155 参考 `false`,`.text` 实质不同。本批重编对齐编译期总开关。

编译期开关 + 构建环境(共 6 项,原样记录;前 5 项 soong `art/build/art.go` 读取):

```sh
export ART_USE_READ_BARRIER=false \
       ART_DEFAULT_GC_TYPE=CMS \
       ART_USE_GENERATIONAL_CC=false \
       ART_HEAP_POISONING=false \
       ART_TEST_DEBUG_GC=false
export ALLOW_MISSING_DEPENDENCIES=true
source build/envsetup.sh && lunch aosp_arm64-userdebug
m -j32 build-art-host libart
```

**构建配方注意(诚实记录)**:首轮仅设 5 开关于 22:03 失败 2:54——kati `platform_availability_check` 拒 9 模块(dexoptanalyzer / libart-disassembler±32 / libartbase±32 / libdt_fd_forward±32 / libprofile±32),与 T3 首败(19:58)清单逐字相同,尽管 #21 已在树(dexoptanalyzer/Android.bp 有 `//apex_available:platform`,但生成的 mk 仍 `LOCAL_NOT_AVAILABLE_FOR_PLATFORM := true`)。取证:T3 成功的 r2(`t3-build2.log`)含 `Environment variable ALLOW_MISSING_DEPENDENCIES was set, regenerating...`——r2 过检查是靠该变量旁路(check mk 对 `ifndef ALLOW_MISSING_DEPENDENCIES` 门控),非 #21 解了检查本身。故本批同 r2 加 `ALLOW_MISSING_DEPENDENCIES=true`(上方第 6 项)。**#21 未根治检查**的根因(soong apex_available 传递)未解,留待外环定夺是否追查。

**生效证据(ninja 级,非仅字节差)**:`out/soong/build*.ninja` 中 `ART_USE_READ_BARRIER=1` 出现 **0** 次、`ART_DEFAULT_GC_TYPE_IS_CMS` **1199** 次、`ART_HEAP_POISONING=1` 0 次(off)。dex2oat64 体积 204,735,528 B vs rb-on 211,517,928 B(−6.8 MB,读屏障代码编出),与开关方向一致。

log:hw248 `/home/alvin/aosp-14.0.0_r1-art/t3b-build2.log`(误启 2 开关本 `t3b-build.log` 已杀;首轮 5 开关缺 ALLOW_MISSING_DEPENDENCIES 败本同名,已覆写)。

### 产物(2026-09-30 22:21,read barrier OFF + GC=CMS)

| 文件 | 大小 | sha256 前 16 |
|---|---|---|
| `out/host/linux-x86/bin/dex2oat64` | 204,735,528 | `89b8b3d40e0e807d` |
| `out/target/product/generic_arm64/apex/com.android.art/lib64/libart.so` | 10,283,888(ARM aarch64) | `30f196c04a99e06b` |
| `out/host/linux-x86/lib/libart.so`(host 对照) | — | `6f9b4a1e4a5d79f7` |

### 对照(rb-on,T3 原产物,已存档 `/home/alvin/aosp-14.0.0_r1-art-rb-on/`)

| 文件 | sha256 前 16 |
|---|---|
| dex2oat64 | `8a125a256a743820` |
| target libart.so | `65d8058f518cd22f` |
| host libart.so | `940580332e578783` |

---

## T3(原始,读屏障开,2026-09-30 20:33)

树:hw248 `/home/alvin/aosp-14.0.0_r1-art`(T2 同步,钉版见 `../aosp-14.0.0_r1-pinned-manifest.xml`)。
补丁:art/ 上 21 件序列(#01-20 = T1 定版 R155 差异文件 patch;#21 = 构建层 `21-apex_available_platform.patch` 适配版,源自 cc-wiki `f880cd746`,sha16 `ce34ce8725307bf3`,490 行)。注:首轮逐字用 HanBingChen 原版 #21 与 #01-19 冲突(kati platform_availability_check 失败 03:01);逐字版 `git apply -R` 干净回退后换适配版,`--check` 过再打。

## 构建命令与结果

```sh
source build/envsetup.sh && lunch aosp_arm64-userdebug
m -j32 build-art-host libart   # r2: build completed successfully (19:58), FAILED=0
```

log:hw248 `/home/alvin/aosp-14.0.0_r1-art/t3-build2.log`(首轮败本 `t3-build.log`)。

## 产物(2026-09-30 20:33)

| 文件 | 大小 | sha256 前 16 |
|---|---|---|
| `out/host/linux-x86/bin/dex2oat64` | 211,517,928 | `8a125a256a743820` |
| `out/target/product/generic_arm64/apex/com.android.art/lib64/libart.so` | 10,304,888(ARM aarch64) | `65d8058f518cd22f` |

ldd(dex2oat64,仅 glibc 面 8 项):ld-linux-x86-64 / libc.so.6 / libdl.so.2 / libgcc_s.so.1 / libm.so.6 / libpthread.so.0 / librt.so.1 / linux-vdso.so.1 —— hw248 原生可跑。

源码版本(T2 已验):kImageVersion=108、kOatVersion=230(与板一致)。

## 下一步(T5)

用本 dex2oat64 对 9 jar(payload v3a-r8b)按板上 cmdline 原样(fn03 同形路径 + dex-location=/system/android/framework/*)生成 27 文件,对照 `boot-image-inputs.sha256`(L1/L2),kv 补 bootclasspath-checksums/compilation-reason。
