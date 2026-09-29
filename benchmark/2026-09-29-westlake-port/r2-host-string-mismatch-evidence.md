# R2 host 线 String mismatch 证据链(2026-09-30,Option A 收口)

目标:用 VM 上的 host dex2oat(art-108-e6af1cd8)原样复现板上 9 段 boot 镜像,失败死点与证据如下。

## 已达成

- **host 工具链**:art-108-e6af1cd8(LineageOS codeload 直拉,img108+oat230 双验,与板上 libart 59e1bb45 同版本对)+ art-build Makefile.host 适配(c++17/include 路径/弃 15-API patch 族/entrypoint 桩)。最终 108ac = 457 OK/0 错(VM commit 5d501a2)。
- **Option A 移植**:delta 量化证伪"五件移植"——runtime_intrinsics/mirror/class 的 patch 与 A15 原生逐字节相同(+0)、well_known_classes 仅 1 行 include、var_handles 为删除性 delta(108 原生本无 PFCut);唯一实质件 = art_method 的 +27 行 bridge_needs_interpreter 块,以 108 原生为基移植(IsStub→ContainsPc),编译零错。

## 死点(两轮 shim 复跑一致)

`ClassLinker::InitWithoutImage: Class mismatch for Ljava/lang/String;`

- dump1(from-mirror)objectSize=779 vs dump2(from-dex)723,两组均 `cl=(nil)`
- **779 非对齐**(ART 对象 4/8 对齐,779 为垃圾值)+ `cl=(nil)` = mirror 读已坏,不是真实的字段差
- 触发点:map32bit shim(LOW_START 0x10000000 原版与 0x70000000 对齐版各一)+ LD_PRELOAD sigchain,5-jar(core-oj/core-libart/core-icu4j/stubs/framework)与单 jar(core-oj / core-libart)均同死
- hw248 原生 x86_64(无 Rosetta,MAP_32BIT 天然生效,ld-linux 直调)复现**同错同值 779** → 排除 Rosetta/shim 环境伪影

## 关键对照(A15/118 线)

- 同一 Makefile 家族、未做 108 适配的 A15 host dex2oat(/tmp/host-dex2oat-108)**通过 String 检查**,死于更后 `runtime.cc:5483 Failed to return pre-allocated NoClassDefFoundError` → `thread.cc:4934 Check failed: new_exception != nullptr`
- 即:墙在 108-vs-A15 runtime 的其它差异(候选:InitWithoutImage 路径的堆/cage 布局、mirror 对象构造次序),**不在五件 patch**(四件已还原 108 原生、art_method delta 已移植,墙不动)

## libcore 版本事实(一手)

- 板上/payload 的 core-oj.jar、core-libart.jar dex **无 hashIsZero 字段**(strings 亲验),String 含 count/hash/coder/value(13/14 代 libcore)
- 108 树(2023-07 U-dev)mirror String 含 count_/hash_code_;A15(2024)同——mirror 侧两者都有,故 String 检查的差异不在字段集本身
- 板上 jar 与 payload jar md5 逐字节一致(core-oj 679d10b7 / core-libart 49c9de70)

## 产物与日志(VM)

- 产物:/tmp/host-dex2oat-108ac(24,141,328B);对照 /tmp/host-dex2oat-108(25,652,008B,A15 误编件)
- shim:/tmp/libmap32bit.so(LOW_START 0x10000000)/ /tmp/libmap32bit7.so(0x70000000)
- 日志:/tmp/r2am.log、/tmp/r2am7.log(108 两轮)、/tmp/r2ctrl2.log(A15 对照)、hw248 /tmp/native-run.log(原生复现)
- jars:~/a2hlab/ws/bootimg-repro/jars(payload 直拷,5 件)
- 原配方:bms/src/tools/experiments/d600/fn01_provenance/build_current_boot_generation.py L437-459(AlexPC,单次调用产 9 段)

## 失误记档

约 20 轮手搓 flags(memcpy 级联真因 = port5 规则 `-I mirror` 毒化 `<string.h>`,改 `-iquote` 解决)、heredoc 引号冲突 ×1、`__config_site` 缺 isystem ×1、mirror/class 排除行尾反斜杠漏 ×1——均纠正,过程见 VM art-build 仓 git log。

## 下一步

C 案(板上 device-side dex2oat64,5cd ~08:15 空,等外环黑板放行):①板上找与 libart 59e1bb45 同源的 dex2oat64(build-id/SHA 证据),找不到即停;②产物只写 /data/local/tmp/oc-t4-boot/;③原 5 jar 原样重编→拉回逐段比 checksum;④复现通过才做 tagsoup 1.2.1 替换版;⑤现役镜像替换为另一笔事务(外环批+回滚),不在本单。oat247 toutiao 线的 host 配方(LD_PRELOAD libmap32bit,DIGEST L165)仅对照,不混用。
