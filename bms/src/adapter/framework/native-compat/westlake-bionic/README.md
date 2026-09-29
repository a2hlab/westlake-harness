# westlake-bionic — bionic ABI 供给库(照抄自 Westlake,#84 方案 A)

来源(Mac 副本 `/Users/zhaoyue/orca/workspaces/vm-copies/westlake-current/`,原树 `~/a2hlab/westlake-current`,#84 定案):**原样拷贝,未改动一行**。

## 文件 → 解的符号(对照 #84 符号清单)

| 文件 | 解什么 | 关键行 |
|---|---|---|
| `bionic-abi.map` | **版本脚本是关键**:LIBC version node,让 `__errno@LIBC` 这类版本化查找命中(musl 本体无此节点) | 全文件(Android 15 libc.map.txt 摘录) |
| `bionic_assert_compat.c` | `__errno`(→桥 musl `__errno_location`,fd-netguard 的 `s=__errno use_vna_hash=1` 直接解)、`__open_2`、`__assert2`、`__system_property_get`(anki UND 之一) | L23-24 `__errno`、L29+ `__open_2` |
| `bionic_stdio_compat.c` | `__sF[3]`(anki UND;注释明言覆盖 versioned `__sF@LIBC`) | L24 |
| `liblog_android_supplement.cpp` | `__android_log_print/__android_log_buf_write/__android_log_security` —— **anki 的 DT_NEEDED `liblog.so` 的内容** | L26-33 |
| `malloc_compat.cpp` | bionic malloc 族(`malloc_debug` 边界等) | 全文件 |
| `misc_compat.cpp` | 零散 bionic 专有符号 | 全文件 |
| `system_properties.cpp` | `__system_property_get` 完整实现(assert_compat 里引用) | 全文件 |
| `android_native_network_compat.c` | NDK 网络族(与早前 `ndk-libandroid` 16 缺符号面部分重合,可并入) | 全文件 |
| `fdsan_stubs.cpp` | fdsan(8 字节弱桩族,#48 时代 fdsan 崩溃的预防面) | 全文件 |
| `libstdcxx_compat.c` | libstdc++ 零星符号 | 全文件 |
| `android_view_VelocityTracker.cpp` | `VelocityTracker.nativeInitialize/nativeAddMovement/...`(#78 fd-auxio 的 UnsatisfiedLinkError;文件头注释即原因与中性值策略) | L54-77 注册表 + `register_android_view_VelocityTracker` |

## 产物与接线(cx-t0)

`build.sh`(dockbuild 内跑,`OHOS_SYSROOT` 由环境给;**11 个源文件缺一即失败**,符合 #86 契约):

- `libc.so` — soname libc.so,**`--version-script=bionic-abi.map` 必须保留**(不带节点的方案 B 会让 netguard 的版本化查找仍失败,#84 已注)
- `liblog.so` — soname liblog.so(anki DT_NEEDED 直接可解)
- `libfdsan_shim.so` / `libstdcxx_compat.so` — 伴随件
- `android_view_VelocityTracker.o` — **对象文件**,链进 runtime 的 native 库后由启动注册(参照 Westlake `AndroidRuntime.cpp` L265 注册表项;本目录无 AndroidRuntime.h,build.sh 在缺 include 时 exit 2 并提示,由 cx-t0 接线)

## 原样拷贝清单(vm-copies 路径)

- `native/bionic-abi.map` → 本目录
- `framework/appspawn-x/bionic_compat/src/{bionic_assert_compat,bionic_stdio_compat,liblog_android_supplement,malloc_compat,fdsan_stubs,libstdcxx_compat,misc_compat,system_properties,android_native_network_compat}` → 本目录
- `framework/android-runtime/src/android_view_VelocityTracker.cpp` → 本目录

## 未拷(有理由,如需再拿)

- `art_runtime_stubs.cpp`(1458 行,ART 内部桩,属 runtime 库不属 ABI 供给)
- `sanitize_android_elf.c`(DT_INIT_ARRAY 修剪器,是构建期工具非运行库——若后续仍见 header-failed 再引)
- `android_native_namespace_bootstrap.c`(namespace 引导,与 v3a 部署器职责重叠,由 cx-t0 决定)
