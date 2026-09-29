# libhwui EGL-retry TU 重编配方 + 重链卡点报告(45 分钟项,2026-09-30)

**结论：TU 编译配方已固化并实证(零 error);完整重链卡在对象谱系不匹配,交 cx-t0 的 v3c 构建系合成。** 按外环指令如实报卡点,不硬凑。

## 已完成(可复现)

### ① 真实链接入口(定位闭环)

`westlake-harness/bms/src/adapter/build/inner/compile_libhwui_arm64.sh` 三段流水:
- Phase 1:编 189 个 hwui 上游 .o(`hwui15/objects/`)
- **Phase 2a(L1127-1140):编 shim .o(hwui_oh_abi_patch + hwui_register_stubs)** ← 我的目标 TU
- Phase 3(L1335-1406):链 libhwui.so(对象 + LIBS 表)

外层 `compile_libhwui.sh`/`compile_libhwui_arm64.sh` 的 "deprecated" 注记只是包装层提示,**内层链是活的**;be59260f(payload 带 hijack 的 libhwui)的原始构建机(GZ05 谱系,`/home/HanBingChen/{oh,aosp}`)不在本地/VM/hw248 三层内——只能重建等效物。

### ② TU 编译配方(实证,零 error)

```bash
CXX=~/ws/toolchains/ohos-sdk/native/llvm/bin/clang-15   # OHOS clang 15.0.4
SR=$SDK/native/sysroot
AOSP=~/ws/android-source                                 # VM 等价树
BC=<adapter>/framework/appspawn-x/bionic_compat/include

$CXX --target=aarch64-linux-ohos --sysroot=$SR \
  -I$SR/include/aarch64-linux-ohos \
  -fPIC -O2 -std=c++17 \
  -Wno-unused-parameter -Wno-unused-private-field \
  -I$BC -I$AOSP/libnativehelper/include_jni -I$AOSP/libnativehelper/include \
  -c hwui_oh_abi_patch.cpp -o hwui_oh_abi_patch.o
```

**与原配方的唯一差异**：去掉 `-include $BC/libcxx_compat.h`(它与 SDK sysroot 的 `isinf/isnan` 双定义冲突;TU 自含头不依赖它——**这是本机差异,原 GZ05 的 wukong100 musl sysroot 无此冲突,若 cx-t0 构建机有 wukong100 请保留原样**)。EGL 局部声明(extern eglGetError + kEglAttribNone=0x3038)已落源码,无需 EGL 头。

**产物**:`/tmp/hwui-tu/hwui_oh_abi_patch.o` = 35,920 字节,sha16 `371928c2f4eebf1e`,T eglCreateWindowSurface 亲证在列(32 个 T/W 符号)。

### ③ Phase 3 LIBS 表(从 L1338-1388 提取,VM 路径已代换)

```
-loh_hwui_shim -lskia_canvaskit.z -landroidfw -lEGL -lGLESv3 -lminikin
-lharfbuzz_ng -lft2 -licuuc -licui18n -lutils -lcutils -lbase -llog -lhilog
-lnative_display_manager -ldl -lc++ -lm -lc -lpthread -lnativehelper
```
VM 等价来源:native-imports/ + native-runtime/ + sysroot(全部亲验存在)。LDFLAGS:`-fuse-ld=lld -Wl,--gc-sections --as-needed -Bsymbolic-functions --allow-shlib-undefined -z,lazy --unresolved-symbols=ignore-all --error-limit=0 -Wl,-soname=libhwui.so`。

## 卡点(两跑两败,根因定案)

用 out.75d82d5 的 189 对象 + 新 .o 重链,系统性符号冲突:
- 第一跑(误含 shims 对象):`AHardwareBuffer_getDataSpace` 重复——对象集划分错(shims 属 liboh_hwui_shim.so)
- 第二跑(191=189+registration+新 .o):`SkImages::DeferredFromAHardwareBuffer` 重复(oh-skia 对象 vs abi_patch §AHardwareBuffer 段)
- 系统性枚举:我的 .o 32 符号与 **80+ 个上游对象冲突**

**根因**:a11c 线的 189 对象是**未打 patch 的上游源**编译的(a11c 的 libhwui 是 `U eglCreateWindowSurface` 导入——hijack 不在里面);原始 be59260f 链路的对象是**先套 51 个 per-file patch(aosp_patches/libs/hwui/patches/)再编译**的——上游实现被 patch 替换,符号才不冲突(L115 注释"HWUI_PATCH 优先级机制=stub 替上游"正是此意)。

**因此**:在 VM 重建 be59260f 等效物 = 重跑 Phase 1(套 51 patch 编 189 源,需完整 AOSP frameworks-base 树 + wukong100 sysroot,VM 无 `$HOME/oh`),超出 45 分钟窗口且与 R1 同病(原构建机不在此三层)。

## 给 cx-t0(合成路线)

1. 用②配方重编 TU(或直接取 `/tmp/hwui-tu/hwui_oh_abi_patch.o`,sha16 371928c2)——**唯一注意**:若其构建机保留 `-include libcxx_compat.h` 且不冲突,用原样;
2. 在其 v3c 构建系(有 wukong100/原对象谱系)以③的 LIBS 表重链——它 patches/ 目录已有 AutoBackendTextureRelease.cpp.patch 等 51 patch 同族先例,对象谱系天然匹配;
3. 验收:`nm -D` 见 `T eglCreateWindowSurface`(强符号)且 `[OH_EglHijack]` 串在二进制内;diff 原 be59260f 的符号面应只多 retry 分支相关改动。
