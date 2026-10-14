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

```t4b-build-json
{
  "schema": 1,
  "evidence_kind": "build_receipt",
  "artifacts": {
    "libart_sha256": "59e1bb45294b9dd587dc9b81bad719b60675aa98c9c6cfced426449bcad0fe5f",
    "boot_oat_sha256": "90f827190482b849f71bceb9ab3d2482c8b42adf70b8b084af887728cb43f248"
  },
  "environment": {
    "ART_USE_READ_BARRIER": "false",
    "ART_DEFAULT_GC_TYPE": "CMS",
    "ART_USE_GENERATIONAL_CC": "false",
    "ART_HEAP_POISONING": "false",
    "ART_TEST_DEBUG_GC": "false",
    "ALLOW_MISSING_DEPENDENCIES": "true"
  },
  "native_debug_build": false
}
```

注:`libart_sha256` 为**部署件**——板上 R155 libart.so(`59e1bb45…`,cross_compile_arm64.sh 手工交叉编译,非 Soong 产物);Soong target libart `30f196c04a99e06b` 仅对照件不进部署。`boot_oat_sha256` 为 T5b `/home/alvin/oc-t4-t5b/boot.oat`(`90f82719…`)。`native_debug_build=false` 据 cc-wiki 配方归档(R155 cross_compile_arm64.sh ART_DEFS 有 `-DNDEBUG`)。

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

## T7(mainline-stubs 合一版镜像,2026-09-30 22:59,oc-t4)

派单(板 ACK(91) 22:57):合一版 `adapter-mainline-stubs.jar`(tagsoup Parser `5094f8459` + cc-t3 J4-boot-api 桩 `44ab7862e`)→ 用 T3b dex2oat64 `89b8b3d4`(读屏障关)出镜像到 `/home/alvin/oc-t4-t7/`,核 kv `concurrent-copying=false`。

### jar 构建(dockbuild,本机)

源树:westlake-harness-t3 `44ab7862e` 的 `bms/src/adapter/framework/mainline-stubs/java`(111 个 `.java` + 4 个 `.pre-wlconn-bak` 备份不参编,与 VM westlake 树基线一致)。编译(dockbuild `a2hlab-b5-java:24.04` 镜像,`t7-stubs-build/`):

```sh
CP=out/core-java/java/core-all-compile-only.jar:out/core-java/java/core-libart.classes.jar:\
   out/framework-runtime/core-compile-only.jar:out/framework-runtime/framework.classes.jar
javac -encoding UTF-8 -classpath $CP -d classes @srcs.txt   # 190 类
d8 --classpath <4 jar 各一 --classpath> --output dex classes/*.class   # classes.dex 181,944 B
jar(META-INF/MANIFEST.MF + classes.dex 薄壳)
```

注:`compile_mainline_real.sh` 路径已死(FWK_TURBINE / bcp_gap_report.txt / mainline-stubs-handwritten 三处依赖均不存在,脚本标 DEPRECATED),以上为实测等效配方旁路。

| 产物 | sha256 前 32 | 大小 |
|---|---|---|
| `adapter-mainline-stubs.jar` | `366acc276a39e4fc17dc6911f4151093` | 52,609 B |
| 内 `classes.dex` | `55cfe5894bfcbd367b186ebbf0a2bdc0` | 181,944 B |

**逐类比对(vs 板上基线 jar `beb369a1` = VM `bootimg-repro/jars/` 同件,dexdump 结构 diff)**:类清单 base 190 / new 191,唯一新增 `Landroid/net/NetworkInfo$State;`(fd-plus 桩自带嵌套枚举),无类删除。方法/字段新增全部落在派单两项内:tagsoup `setProperty/getProperty`+4 属性常量、`NetworkRequest.getNetworkSpecifier`、`NetworkInfo.getState`+State 6 值、`NetworkCapabilities.getLinkUp/DownstreamBandwidthKbps`、`MediaStore.{Images,Video,Audio}.Media.EXTERNAL/INTERNAL_CONTENT_URI`。无意外改动。

### T7 镜像(hw248,`/home/alvin/oc-t4-t7/`)

t4b-build-json 结构化回执:gate 限定一文件一围栏,T7 回执在 `benchmark/2026-09-30-t4b-build-switch-gate/evidence/T7-BUILD-snapshot.md`(6 项环境与 T3b 相同,boot_oat 绑本节 T7 `4a46e40f…`,libart 同绑部署件 R155 `59e1bb45…`,native_debug_build=false);T5b/T7 gate 均 exit 0(pass,deploy_allowed=true)。

9 输入 = T5 原 8 件 + 新 stubs jar(`366acc27` 替换 `beb369a1`,其余 8 件哈希不变);dex2oat64 = T3b `89b8b3d4`。22:57:36 起,22:59 完成,27/27 生成。boot.oat oat230 / boot.art image108 OK。**kv `concurrent-copying=false`**(另 compiler-filter=speed、debuggable=false、native-debuggable=false、requires-image=true,8 键集与 R155 一致)。

**L1 判读(重要,勿误读为失败)**:vdex **8/9**——`boot-adapter-mainline-stubs.{vdex,oat,art}` 三件差是**预期**(jar 内容本身变了,vdex 不可能再逐字节同);其余 8 个 vdex 与参考逐字节同。t5_gen_image.sh 的 exit 6 是其 L1 判据针对"jar 不变"场景,不适用于 T7(jar 变更场景)。

27 件哈希(hw248 `/home/alvin/oc-t4-t7/SHA256SUMS.txt`,前 16):

```
bfb7137e5468cff9 boot-adapter-mainline-stubs.art   ┐
674f0863c73a129d boot-adapter-mainline-stubs.oat   ├ 预期差(jar 变)
93a9d32744c9d608 boot-adapter-mainline-stubs.vdex  ┘
74546feb1927aef1 boot-apache-xml.art      d3c26179a19e574b boot-apache-xml.oat   5cdf56053f7118ec boot-apache-xml.vdex
04c6a15c3f6484cc boot-bouncycastle.art    9f9d4f55bc4aa3b4 boot-bouncycastle.oat 51d42e85675ee724 boot-bouncycastle.vdex
264991613fe20395 boot-core-icu4j.art      049d09d04f46519e boot-core-icu4j.oat   8da239f3c7c297f0 boot-core-icu4j.vdex
e242165991fc86cc boot-core-libart.art     22576fc77430d7d8 boot-core-libart.oat  a5a90304c7b06136 boot-core-libart.vdex
b67b2c08d08acc08 boot-framework.art       6bf57954c60389d6 boot-framework.oat    531de30496b0780d boot-framework.vdex
5a1a1ea70a4cf199 boot-oh-adapter-framework.art 449055b533e386ed boot-oh-adapter-framework.oat 5e0557427f19acd3 boot-oh-adapter-framework.vdex
023ff69965bc4eb6 boot-okhttp.art          6cadc570b07cfd42 boot-okhttp.oat       bfad17177cb49196 boot-okhttp.vdex
15c9f7b792377db0 boot.art   4a46e40fa7ffb1d1 boot.oat   23c1f5b05f1b103f boot.vdex
```

### T7c(T7 用 T3c dex2oat64 重出,2026-10-01 00:30,oc-t4)

派单(板 ACK(91) 00:28):同一版 stubs jar(`366acc27`),其余 8 jar 与 T5c 相同;dex2oat64 = T3c `ae865ddd6a7e4b25`(补丁 #22 显式挂起轮询)。27/27 出件到 `/home/alvin/oc-t4-t7c/`,oat230/image108 OK,kv `concurrent-copying=false`(rb 门 PASS)。oatdump 抽查 isOHEnvironment() 入口仍为显式挂起轮询(`sub x16,sp,#0x2000`+`ldr wzr,[x16]`+`ldr w16,[tr]`+`tst #0x7`,code_offset 0x4c9f0,size 316,与 v3c/T5c 同型)。

与 T5c 差异件清单:`boot-adapter-mainline-stubs.{art,oat,vdex}`(jar 内容变了,预期)+ 其余 8 jar 的 `.oat`/`.art` 与 `boot.{art,oat}`(嵌 cmdline 路径串,预期);全部 9 个 `.vdex` 除 adapter-mainline-stubs 外逐字节同。t4b 回执 `evidence/T7c-BUILD-snapshot.md`(gate pass exit 0)。T7c boot.oat 拷本机 `_hw248-t7c/arm64/`。等 T6c 板上过后接着上板验 wikipedia/tagsoup 与 4 个 boot-api app。

---

## T3c(补丁 #22:arm64 关隐式挂起检查,2026-10-01 00:20,oc-t4)

派单(板 ACK(91) 00:13):oatdump 对照(OATDUMP-DIFF.md)证 T5b 在板上 abort 的强假设是**隐式挂起检查**——isOHEnvironment() 入口 v3c=显式「ldr w16,[tr];tst #0x7;b.ne」vs T5b=隐式「ldr x21,[x21]」(R155 运行时未给 x21 装挂起触发页指针,入口读地址 0 被当首条 dex 指令的隐式空检查 → 「Invalid address for an implicit NullPointerException check: 0x0, at const-string」)。r1+21 dex2oat.cc:859 对 arm64 写死 implicit_suspend_checks_=true ⇒ 21 补丁缺编译器侧这一项。

补丁 #22 `22-dex2oat__implicit-suspend-checks-off.patch`(sha16 b984703ac6767034):dex2oat.cc:859 `true→false`,**只动挂起检查**(空检查两版已一致,不动)。先例:Westlake aosp-art-15 dex2oat.cc 在 `WESTLAKE_EXPLICIT_NULL_CHECKS=1` 时同关 `implicit_suspend_checks_`(westlake-harness-aot42 source-excerpts.txt:886-891)。已入 series(现 22 补丁)。

构建(增量,同 T3b 六环境变量):

```sh
export ART_USE_READ_BARRIER=false ART_DEFAULT_GC_TYPE=CMS ART_USE_GENERATIONAL_CC=false ART_HEAP_POISONING=false ART_TEST_DEBUG_GC=false
export ALLOW_MISSING_DEPENDENCIES=true
source build/envsetup.sh && lunch aosp_arm64-userdebug
m -j32 dex2oat   # 增量 04:19 绿,log t3c-build.log
```

产物(host dex2oat64,T3c):

| 文件 | sha256 前 16 |
|---|---|
| `out/host/linux-x86/bin/dex2oat64` | `ae865ddd6a7e4b25` |

### T5c 镜像(2026-10-01 00:23,hw248 `/home/alvin/oc-t4-t5c/`)

同 T5b 9 jar(原 adapter-mainline-stubs.jar,非 T7 合一版)+ 同参数,T3c dex2oat64。27/27 出件,vdex 9/9 逐字节同,oat230/image108 OK,kv `concurrent-copying=false`(rb 门 check_boot_oat_rb.py PASS)。boot.oat sha16 `0e7dc0e457463b3d`,boot.art sha16 `6e909d6c4930bd32`。

**oatdump 验证(派单验收点)**:isOHEnvironment() 入口已变显式挂起检查,与 v3c 同型——`sub x16,sp,#0x2000`+`ldr wzr,[x16]`(显式栈探测)、`ldr w16,[tr];state_and_flags`+`tst w16,#0x7`(显式挂起轮询),CodeSize 回 316、code_offset 回 0x4c9f0(与 v3c 同)。T5b 的隐式 `ldr x21,[x21]` 已消除。

t4b 回执:gate 限一文件一围栏,T3c/T5c 回执在 `benchmark/2026-09-30-t4b-build-switch-gate/evidence/T3c-T5c-BUILD-snapshot.md`(6 项环境同 T3b,boot_oat 绑 T5c `0e7dc0e457463b3d991e589c727e0f6bae19e11eedb6ac6fb7ee28ffcdde21b3`,libart 同绑部署件 R155 59e1bb45…,native_debug_build=false);t4b_build_switch_gate.py 对 T5c **pass exit 0**(mismatches=0,exceptions=0,deploy_allowed=true)。

出件后等外环排板做 T6c。

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
