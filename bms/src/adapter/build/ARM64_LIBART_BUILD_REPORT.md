# musl 版 arm64 libart.so 构建报告

日期: 2026-08-03 (AlexPC, /opt/build-trees/adapter)

## 1. musl 版 libart.so 编出来了吗? → 编出来了

由包装器实跑(`bash build/build_aosp_lib_arm64.sh --target=libart.so`,退出码 0)产出,
全量从 AOSP 源码(/opt/build-trees/aosp-arm64-d600)新编,245/245 源文件,strict -z defs 链接,
未复制任何现成 .so(对象目录 out/.obj_aosp_lib64 为本次新建)。

- 路径: `/opt/build-trees/adapter/out/aosp_lib64/libart.so`
- 大小: 11761032 字节 (12M)
- md5sum: `15fa67d66f28b9fe9991d9b339554201`
- file 输出:
  `ELF 64-bit LSB shared object, ARM aarch64, version 1 (SYSV), dynamically linked, BuildID[sha1]=d3ca90452375750d916b7144a37264ac60682f96, with debug_info, not stripped`
- readelf: Class=ELF64, Type=DYN, Machine=AArch64, SONAME=libart.so
- musl 证据(共享库本身无 PT_INTERP 段,/lib/ld-musl-aarch64.so.1 解释器只出现在可执行文件上;
  对 .so 的 musl 判定如下):
  - DT_NEEDED 首项 `libc.so`(OH musl,来自 sysroot
    `out/wukong100/obj/third_party/musl/usr/lib/aarch64-linux-ohos/libc.so`),无 libc.so.6;
  - `--dyn-syms | grep -c GLIBC` = 0(零 glibc 版本引用);
  - strings 可见 OH musl crt 对象烘焙痕迹
    `obj/third_party/musl/intermidiates/linux/musl_src_ported/crt/aarch64/crti.s|crtn.s`。
- 冒烟门全过: smoke[libart.so] 10733 sym lines 全导出在; Profile B gate 过;
  build_errors 0 条; 23/23 库 ✅(含 libbionic_compat、libart-compiler)。
- 可复现性: 另一次独立目录(out/aosp_lib64_verify)+ 独立对象目录的全量构建,
  md5 与 BuildID 逐字节相同(15fa67d6… / d3ca9045…),构建是确定性的。

## 2. 包装脚本 → 已写出

- 路径: `/opt/build-trees/adapter/build/build_aosp_lib_arm64.sh`
- 用法: `bash build/build_aosp_lib_arm64.sh --target=libart.so`(已实跑验证,exit 0)
- 模式: 照 build/build_aosp_lib.sh 的 target 分发;`--target=`(逗号分隔)、`--clean`、
  `-j N`、`--dry-run`、`--oh-root=`、`--aosp-root=`、`--help`。
- Phase 1 限制(与 arm32 一致): cross_compile_arm64.sh 无库内选择,选任何成员触发
  23 库整栈;out/.obj_aosp_lib64 增量 .o 缓存使重跑便宜。
- 分发两阶段: ① compile_app_native_loader_arm64.sh → libapp_native_loader.so
  (strict 下 libnativeloader 的链接边 + Profile B 门需要,自动先编);
  ② inner/cross_compile_arm64.sh → 23 个 musl arm64 .so。

## 3. 最小 env 集合

cross_compile_arm64.sh 直跑(不设 L03_A12_GENERATION_ID 即不触发 generation 强制项):

| env | 值 | 说明 |
|---|---|---|
| BUILD_INNER_INVOKED | 1 | guard 解锁(唯一硬门槛) |
| OH_ROOT | /opt/build-trees/oh610_lts_source | 默认 $HOME/oh 不存在,必须显式 |
| AOSP_ROOT | /opt/build-trees/aosp-arm64-d600 | 默认 $HOME/aosp 不存在,必须显式 |
| L03_A12_LIBCXX_INCLUDE | $OH/prebuilts/clang/ohos/linux-x86_64/llvm/include/libcxx-ohos/include/c++/v1 | **必须**:脚本内置默认 include/c++/v1 缺 `__config_site`,asm_defines 契约编译即失败 |
| L03_A12_STRICT_BUILD | 1 | 可选;generation 验证过的配置(-z defs + soname + Profile B 门) |
| AOSP_OUT_DIR / AOSP_OBJ_DIR / AOSP_BUILD_ERROR_LOG | out/ 下自属路径 | 可选;建议设,避免共享 /tmp/cc100 |
| BUILD_NJOBS | 32 | 可选,编译并发 |

其余 L03_A12_CXX/CC/AS/READELF/BUILTINS/PYTHON 的脚本内置默认
($OH_ROOT/prebuilts/clang/ohos/linux-x86_64/llvm/...)在本树全部存在,无需设置。
strict=1 时另需 libapp_native_loader.so 先落进 $AOSP_OUT_DIR(包装器自动处理;
手动直跑需先跑 compile_app_native_loader_arm64.sh,注意它的 OH_SYSROOT 要指 musl 根
`.../musl` 而非 `.../musl/usr`)。

## 4. 卡住记录(均已解决,无未决阻塞)

- 第一次直跑失败(原样错误):
  `ERROR: failed to compile exact ARM64 asm_defines contract`
  底层: `libc++/v1/__config:13:10: fatal error: '__config_site' file not found`
  根因: 脚本内置 LIBCXX_INCLUDE 默认(include/c++/v1)在本 OH 版本不含生成的
  __config_site;完整目标树在 libcxx-ohos 子树(generation 脚本强制校验这一点,
  直跑路径无校验)。修: 显式传 L03_A12_LIBCXX_INCLUDE(见上表),已并入包装器默认值。
- compile_app_native_loader_arm64.sh 首跑失败: `test -d $SYSROOT/usr/include` 不过,
  因 OH_SYSROOT 传成了 `.../musl/usr`;该脚本按 DevEco 布局拼 usr/include,
  应传 musl 根 `.../musl`(与 generation 的 OH_SYSROOT 语义一致)。
