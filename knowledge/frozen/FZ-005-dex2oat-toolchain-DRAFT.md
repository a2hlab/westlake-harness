# FZ-005 草稿(未登记):dex2oat 工具链冻结(dex2oat-once T7)

> **状态:草稿。T6c 与 T7c 板上验证都过了才登记进 frozen.json。** 本文件只是预备稿,
> `verified_apps` 留占位;登记时按板上截图/facts 填实。

## 冻结对象(what)

dex2oat-once 工具链:从 ART 源码到板上 boot 镜像的完整生成路径。

| 件 | 身份 | sha256 |
|---|---|---|
| host dex2oat64(T3c,r1+22 补丁,显式挂起轮询) | hw248 `/home/alvin/aosp-14.0.0_r1-art/out/host/linux-x86/bin/dex2oat64` | `ae865ddd6a7e4b25a18b7c07402920c69e5599b329778eff647a08803948322b` |
| 生成器脚本 | hw248 `/home/alvin/cc-wiki-t5/tool/t5_gen_image.sh` | `14b1f709cbeae35c2e606ee923d26a9f59e92dd827da84bdf5126de79a675d46` |
| 部署参照(不进部署,仅门) | 板上 R155 libart(device, cross_compile_arm64.sh 编) | `59e1bb45294b9dd587dc9b81bad719b60675aa98c9c6cfced426449bcad0fe5f` |
| T5c boot.oat(纯镜像线) | hw248 `/home/alvin/oc-t4-t5c/boot.oat` | `0e7dc0e457463b3d991e589c727e0f6bae19e11eedb6ac6fb7ee28ffcdde21b3` |
| T7c boot.oat(stubs 合一版镜像) | hw248 `/home/alvin/oc-t4-t7c/boot.oat` | `3a2737cd4430f2369807fd1db4aad1ffa0f00bc2a2efa4ae76e26079d204b6f4` |
| adapter-mainline-stubs.jar(T7c 用,合一版) | hw248 `/home/alvin/oc-t4-t7-jars/adapter-mainline-stubs.jar` | `366acc276a39e4fc17dc6911f4151093c1ec1a1640053733b0b26fc536f169c6` |

## 补丁序列(22 件,knowledge/toolchains/art-r155/{patches,series},逐个 sha256)

| # | patch | sha256 |
|---|---|---|
| 01 | `01-compiler__optimizing__code_generator.cc.patch` | `60a4aff7a46241b24fd38fef9633024484fdc27970689af06862b2d7ce2d5b11` |
| 02 | `02-compiler__optimizing__graph_visualizer.cc.patch` | `4dc1569c3b797f2918ba6cfb17dcca678d4e67ac3833c1f09c65be80af72dfeb` |
| 03 | `03-compiler__optimizing__nodes.h.patch` | `f49cd8659853573b94628c5be557ced5bed8c85bf861e51e33e60f72c611f688` |
| 04 | `04-dexoptanalyzer__Android.bp.patch` | `7cacb0fa756bfd66f3e2a1507985f739b99aecb961ffce9fdbc23a130d1ec3dc` |
| 05 | `05-libartbase__base__metrics__metrics.h.patch` | `5e0f5b8890e244dc0cf3c4739687f17f30508aa9e401c259795a2c8f2772c3a1` |
| 06 | `06-libartservice__service__Android.bp.patch` | `beed829d322ba798ecac6cab0bceade533e8e1c41edba843db77f0bf5efe8184` |
| 07 | `07-profman__Android.bp.patch` | `9f833e2afada287bd5a47ae688e5ea9755a1ff40a3a49b039e5ce1ee52ff9b29` |
| 08 | `08-runtime__class_linker.cc.patch` | `be96c5d367c4618c60fa66508c2aed34b0603d9fe329a1e51d8862d0aef1a2bb` |
| 09 | `09-runtime__elf_file.cc.patch` | `6bf15eead30a18633ab04ee85f305a08b7a777396e1935a6fa7bdd00a6987610` |
| 10 | `10-runtime__gc__collector__mark_compact.cc.patch` | `45fc8c81ae2bfdef0dcc363c4169c89e617d0e72ff9f62e3069c199dbf25bb20` |
| 11 | `11-runtime__gc__heap-inl.h.patch` | `83c353ce14e56a1a15587317d7321e064f5836be8284a332cf38fed7f0d6b122` |
| 12 | `12-runtime__gc__heap.cc.patch` | `a50b61adcd5e0cbc6808e75f97bd706950e74fe1d3395c3d459713d6dc83769f` |
| 13 | `13-runtime__gc__space__image_space.cc.patch` | `147a83db77bc80cf1867cc6aaf1819e73be181437c67ad38fc67aa9fe44dc65c` |
| 14 | `14-runtime__jit__debugger_interface.cc.patch` | `17bb523d161f607da7504b0bdf075155aaeb294a6a1864dfdbc56656dde63aac` |
| 15 | `15-runtime__jni__jni_id_manager.cc.patch` | `bfd91df56f222965204046940a0e5b0665d720be75936339012e1be91413406e` |
| 16 | `16-runtime__oat_file.cc.patch` | `a2f155188365ddf67297425be804bfe28dfdff83b54a51e9195773bc4014166b` |
| 17 | `17-runtime__runtime.cc.patch` | `74306d25355585464a89fab3425b5dd4e9791a1501229d0c0dc46e5523ac65fe` |
| 18 | `18-runtime__thread.cc.patch` | `02a7dc13353fc55bbfef1323b7f159e7721156c2d6e949924b3b8956ef30083c` |
| 19 | `19-runtime__thread.h.patch` | `b7f95cf832b62d8e0f5e7d3e026803beb97e8bed6b5b6ec845dbf9d4c1a44902` |
| 20 | `20-runtime__mirror__dex_cache-inl.h.patch` | `31e8ecf25e786cf269fb23ef0b2f6aa939f0d661b07629773265d0bc15c4c2b2` |
| 21 | `21-apex_available_platform.patch` | `ce34ce8725307bf30b45c980f6c973545ca3fd006265c46a67969fdd960c913c` |
| 22 | `22-dex2oat__implicit-suspend-checks-off.patch` | `b984703ac676703491ab857f2c968f38947a3d4bee396b27070bc2dbd4acf3dd` |

## 构建环境(T3c,BUILD.md §T3c,6 项)

```sh
export ART_USE_READ_BARRIER=false \
       ART_DEFAULT_GC_TYPE=CMS \
       ART_USE_GENERATIONAL_CC=false \
       ART_HEAP_POISONING=false \
       ART_TEST_DEBUG_GC=false
export ALLOW_MISSING_DEPENDENCIES=true
source build/envsetup.sh && lunch aosp_arm64-userdebug
m -j32 dex2oat   # T3c 增量 04:19 绿(log t3c-build.log);全量 m -j32 build-art-host libart 亦可
```

t4b 回执(程序生成,schema 1):T5c `benchmark/2026-09-30-t4b-build-switch-gate/evidence/T3c-T5c-BUILD-snapshot.md`;T7c `…/T7c-BUILD-snapshot.md`。均 `evidence_kind=build_receipt`,绑 libart=R155 部署件 + 各自 boot.oat。

## 生成器与参数(t5_gen_image.sh,板上 boot.oat kv 实录同形)

```
dex2oat64 --android-root=/system --instruction-set=arm64 --base=0x70000000 --compiler-filter=speed \
  --runtime-arg -Xms64m --runtime-arg -Xmx512m --runtime-arg -Xverify:none \
  --image=<out>/boot.art --oat-file=<out>/boot.oat \
  --dex-file=<work>/incoming/<jar> --dex-location=/system/android/framework/<jar> ×9
```
9 jar 顺序:core-oj core-libart core-icu4j okhttp bouncycastle apache-xml adapter-mainline-stubs framework oh-adapter-framework。

## 验证过的 app 与证据(占位,等板上 T6c/T7c 结果填)

| app | 板 | 证据 | 截图/facts 路径 |
|---|---|---|---|
| (T6c:HW/ZZ own-UI 判据,占位) | 5cd | 待填 | 待填 |
| wikipedia(tagsoup 桩) | 待定 | 待填 | 待填 |
| fd-libretube(tagsoup 桩) | 待定 | 待填 | 待填 |
| fd-feeder(getNetworkSpecifier) | 待定 | 待填 | 待填 |
| fd-gallery(MediaStore URI) | 待定 | 待填 | 待填 |
| fd-plus(NetworkInfo.State) | 待定 | 待填 | 待填 |
| x(getLinkUpstreamBandwidthKbps) | 待定 | 待填 | 待填 |

## 重现说明(一条命令)

见同目录 `reproduce-dex2oat-toolchain.sh`(说明稿,非自动跑):从 hw248 r1 树 + series 22 补丁
重编 dex2oat64 → t5_gen_image.sh 出镜像 → check_boot_oat_rb.py + t4b_build_switch_gate.py 过门。

## 登记规则提醒(冻结门槛)

按 frozen.json rule:T6c(HW/ZZ own-UI)与 T7c 板上 app 验完、截图/facts 落入上表后,
才由外环把本稿登记为 frozen.json 的 FZ-005(或下一个空闲 id),version 1,status frozen。
