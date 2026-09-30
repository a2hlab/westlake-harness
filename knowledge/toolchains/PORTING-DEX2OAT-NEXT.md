# PORTING-DEX2OAT-NEXT.md — 换 AOSP/鸿蒙版本时 dex2oat-once 检查清单

> 目的:下次换 AOSP 版本(或鸿蒙大版本)时,把今晚(2026-09-30)踩过的坑一次处理好。
> 按今晚实证顺序排,每条给「怎么查」的命令,不给「大概应该」。

## ① 板上 libart 编译开关:从二进制取证,不猜

**教训**:T5 生成物 kv `concurrent-copying=true` vs 板上 R155 `false`,`.text` 实质不同——板上 ART 是关读屏障编的,我们按默认开了。

**怎么查**(cx-bms T5 归因法,全部离线):
```bash
# 板上 libart(部署件,不是 Soong 对照件)的反汇编特征点:
# ValidateOatFile 读 IsConcurrentCopying 的位点(读屏障期望)
# XGcOption 空选项分支写 collector_type(GC 类型)
# heap-reference 是否过 poison(堆中毒开关)
# VMRuntime_vmLibrary 返回串(debug build)
# 全部落进 t4b_build_switch_gate.py 的 ANCHORS 表,程序化核
python3 knowledge/toolchains/art-r155/t4b_build_switch_gate.py \
  --libart <板上 libart.so> --oat <参考 boot.oat>
```

**写进构建环境**(T3c 实证值,换版本时逐项重核):
```bash
export ART_USE_READ_BARRIER=false   # 关读屏障(板上 R155 实测)
export ART_DEFAULT_GC_TYPE=CMS      # CMS 回收器(XGcOption 空选项分支 collector_type=2)
export ART_USE_GENERATIONAL_CC=false
export ART_HEAP_POISONING=false
export ART_TEST_DEBUG_GC=false
export ALLOW_MISSING_DEPENDENCIES=true  # 裁剪树绕过 platform_availability_check(见 BUILD.md 披露)
```

## ② 编译器侧补丁:逐项核 dex2oat.cc 的 implicit_*_checks

**教训**:T5b 在板上 abort(isOHEnvironment() 入口隐式挂起检查 `ldr x21,[x21]` 读地址 0)。21 补丁全是运行时侧,编译器侧(dex2oat.cc)没覆盖。

**怎么查**(oatdump 比入口指令,从能用的旧镜像出发):
```bash
# 对新镜像与参考镜像(能跑的旧版)分别 dump 同一个方法的入口机器码
OATDUMP=<host oatdump 路径>
export LD_LIBRARY_PATH=<host lib64>
$OATDUMP --oat-file=<new>/boot-oh-adapter-framework.oat 2>/dev/null | \
  grep -A60 "isOHEnvironment" | grep -E "code_offset|sub x16, sp|ldr wzr|ldr w16, \[tr\]|ldr x21|tst w16"
$OATDUMP --oat-file=<ref>/boot-oh-adapter-framework.oat 2>/dev/null | \
  grep -A60 "isOHEnvironment" | grep -E "code_offset|sub x16, sp|ldr wzr|ldr w16, \[tr\]|ldr x21|tst w16"
# 对照:入口应有显式挂起检查(sub x16,sp,#0x2000 + ldr wzr,[x16] + ldr w16,[tr]+tst #0x7)
# 隐式版(ldr x21,[x21])= 挂起触发页未装 → abort
```

**重点核的 dex2oat.cc 位点**(r1 实证):
```
dex2oat.cc:859  switch (GetInstructionSet()) {
                  case kArm64: implicit_suspend_checks_ = true;  // ← 必须 false
                  case kArm/kThumb2/kX86/kX86_64: implicit_null_checks_ = true; implicit_so_checks_ = true;
```
补丁 #22 只动 `implicit_suspend_checks_ = false`(空检查两版已一致,不动)。

## ③ 镜像与 BCP jar 的 dex checksum 一致

**教训**:T7 镜像用旧 stubs jar 出,vdex 与参考逐字节同;T7c 换新 jar,vdex 不同——jar 内容变了,镜像必须重出。

**怎么查**:
```bash
# 9 个 jar 的 sha256 与 boot-image-inputs.sha256 参考表逐项对
for j in core-oj core-libart core-icu4j okhttp bouncycastle apache-xml adapter-mainline-stubs framework oh-adapter-framework; do
  sha256sum $JARS_DIR/$j.jar | awk '{print $1}'  # vs 参考表
done
# 出件后:9 个 vdex 逐字节同参考(jar 没变的话),stubs 变则 8/9
```

## ④ 构建非确定性:只剩输出路径串

**教训**:强制重编 dex2oat64 逐字节复现 T3c 产物;镜像唯一差异 = `boot.art`/`boot.oat` 两件(OatHeader 嵌入 `dex2oat-cmdline` 的输出路径串)。

**结论**:同树同补丁同环境重编,dex2oat64 sha256 逐字节复现;镜像同路径出件则逐字节一致,不同路径则仅 boot.art/boot.oat 差(嵌路径串),vdex 不受影响。

## ⑤ 必过门清单

| 门 | 工具 | 判据 |
|---|---|---|
| rb 门 | `check_boot_oat_rb.py <boot.oat>` | kv `concurrent-copying=false`,oat230/image108 |
| t4b 门 | `t4b_build_switch_gate.py --libart <板上 libart> --oat <boot.oat> --build <回执>` | pass exit 0, deploy_allowed=true;回执程序生成(不手抄哈希) |
| G1 | `check_frozen.py --package <generation dir>` | 冻结件 SHA 不变 |
| G2 | 板上 T6/T7 实测(HW/ZZ own-UI + 已亮 app t20 一致) | 截图/facts 落盘 |

**一条命令重现**:`scripts/lab/reproduce_dex2oat_toolchain.sh`(全环境变量,路径不写死)。

## ⑥ 22 补丁逐个分类(换版本时哪些要重做)

| # | patch | 分类 | 换版本时 |
|---|---|---|---|
| 01 | compiler/optimizing/code_generator.cc | R155 特有(编译器行为) | 重做:对照新版是否已含 |
| 02 | compiler/optimizing/graph_visualizer.cc | R155 特有(调试输出) | 可跳(不影响功能) |
| 03 | compiler/optimizing/nodes.h | R155 特有(节点定义) | 重做:对照新版 |
| 04 | dexoptanalyzer/Android.bp | 构建系统修补(apex_available) | 重做:新版可能已修 |
| 05 | libartbase/base/metrics/metrics.h | R155 特有 | 重做 |
| 06 | libartservice/service/Android.bp | 构建系统修补 | 重做 |
| 07 | profman/Android.bp | 构建系统修补 | 重做 |
| 08 | runtime/class_linker.cc([CLI_CP] 调试串) | R155 特有(调试/诊断) | 可跳(不影响功能,但 abort 定位用) |
| 09 | runtime/elf_file.cc | R155 特有 | 重做 |
| 10 | runtime/gc/collector/mark_compact.cc | R155 特有(GC) | 重做:对照新版 GC 实现 |
| 11 | runtime/gc/heap-inl.h | R155 特有(GC) | 重做 |
| 12 | runtime/gc/heap.cc | R155 特有(GC) | 重做 |
| 13 | runtime/gc/space/image_space.cc([AIS_CP]) | R155 特有(镜像空间) | 重做 |
| 14 | runtime/jit/debugger_interface.cc([DBG_IFACE]) | R155 特有(调试) | 可跳 |
| 15 | runtime/jni/jni_id_manager.cc | R155 特有(JNI) | 重做 |
| 16 | runtime/oat_file.cc([OAT_CP]) | R155 特有(oat 加载) | 重做 |
| 17 | runtime/runtime.cc([AIST_CP]) | R155 特有(运行时初始化) | 重做 |
| 18 | runtime/thread.cc | R155 特有(线程) | 重做 |
| 19 | runtime/thread.h | R155 特有(线程) | 重做 |
| 20 | runtime/mirror/dex_cache-inl.h(PRIMCLASS-GUARD) | R155 特有(反汇编补回) | 重做 |
| 21 | apex_available_platform.patch | 构建系统修补(kati platform 检查) | 重做:新版可能已修 |
| 22 | dex2oat/implicit-suspend-checks-off | **OH 平台必需**(隐式挂起检查→abort) | **必做**:新版默认仍是 true,必须显式关 |

**分类汇总**:
- **OH 平台必需**(换版本必须重做):#22(隐式挂起检查)
- **构建系统修补**(新版可能已修,先核再定):#04/06/07/21
- **R155 特有**(功能/行为差异,逐项对照新版是否已含):#01/03/05/09/10/11/12/13/15/16/17/18/19/20
- **调试/诊断**(可跳,但 abort 定位用):#02/08/14

---

*2026-10-01 oc-t4,基于 T3b/T3c/T5b/T5c/T7/T7c 实证。细节见 BUILD.md、OATDUMP-DIFF.md、FZ-005-dex2oat-toolchain-DRAFT.md。*
