# #84: musl dlopen 家族——anki/droidify/noice/netguard 的实因、符号清单与 Westlake 做法

输入:r14 全量(5cd)r14full-20260929T173852 hilog + APK arm64 .so(llvm-readelf 一手)。源:`~/a2hlab/westlake-current`(一手行号)。30 分钟第一版,转 cx-t0。

## 一、重要修正:auto_triage 的 musl-reloc 归类是宽匹配伪影

逐 app 核对 r14 hilog 后:**4 个里只有 2 个有真正的 app 库失败**。

| app | r14 实测 | 定性 |
|---|---|---|
| **anki**(死) | `Error loading shared library liblog.so: (needed by /data/app/.../com.ichi2.anki/android/lib/arm64-v8a/librsdroid.so)` → `dlopen_ns failed for .../librsdroid.so` | **DT_NEEDED 解析失败**:`liblog.so` 在 app 的 musl namespace 根本不存在——不是符号问题,是库缺失 |
| **fd-netguard**(死) | `relocating failed: symbol not found. dso=.../libnetguard.so s=__errno use_vna_hash=1 van_hash=50d63…` | **版本化符号失败**:`__errno@LIBC`(bionic 专有;musl 真名是 `__errno_location`) |
| **fd-droidify**(存活) | app 自带 4 个 .so **全部加载成功**;其 "MUSL-LDSO" 命中行全是系统库 | 归类伪影,剔除本族 |
| **fd-noice**(存活) | APK **0 个 arm64 .so**;同上,命中的是系统库 | 归类伪影,剔除本族 |

三家的 `dlopen_impl load library header failed for libmmi_knuckle.z.so / libsecurity_component_client_enhance.z.so / libartbased.so / libhwui.so` 行,库路径均在系统侧、部分来自 launcher 进程(pid 564)——**是每轮都出现的系统噪声,不是 app 墙**。auto_triage 规则需收窄(已顺手修:命中的 MUSL 行必须含 `/data/app` 或 app 自身 pid,否则不判 musl-reloc)。

## 二、符号清单(llvm-readelf,一手)

**anki `librsdroid.so`**(146 UND,138 带 `@LIBC` 版本标签):
- DT_NEEDED:`liblog.so`、`libdl.so`、`libc.so`、`libm.so`
- bionic 专有 UND:**`__errno@LIBC`**、**`__sF`**、`__system_property_get@LIBC`;liblog 侧:`__android_log_buf_write`、`__android_log_write`
- 其余为常规 POSIX(malloc/dlsym/clock_gettime/bind/cos…),musl 都有

**fd-netguard `libnetguard.so`**(66 UND):
- DT_NEEDED 同上四件
- bionic 专有 UND:**`__errno@LIBC`**(正是 r14 失败日志里的 `s=__errno`)
- 其余常规

**fd-droidify**(4 .so:libandroidx.graphics.path / libdatastore_shared_counter / libimage_processing_util_jni / libsurface_util_jni):
- UND 全为常规 `@LIBC`(`__cxa_atexit/__cxa_finalize/__stack_chk_fail/__register_atexit/malloc…`),无 bionic 专有——**与其"加载成功"一致**

**fd-noice**:无 arm64 .so。

## 三、Westlake 怎么让 bionic 链接的库加载成功(file:line 一手)

Westlake 不把 Android 库直接丢给 musl 裸解析——它**自带一套 bionic ABI 供给**:

1. **版本脚本**:`native/bionic-abi.map` ——照 Android 15 `bionic/libc/libc.map.txt` 写的 linker version script,`LIBC { global: __errno; __sF; android_set_abort_message; __open_2; … }`。用它链出 soname=`libc.so` 的库,app DSO 的**版本化查找 `__errno@LIBC` 才能命中**(musl 本体不提供 LIBC version node,这是 netguard 型失败的直接解)。
2. **符号真身**:`framework/appspawn-x/bionic_compat/src/bionic_assert_compat.c` **L23-24**:`int* __errno(void) { return __errno_location(); }`(桥到 musl 真身);`bionic_stdio_compat.c` **L24**:`__sF[3]`(visibility default,文件头注释明言"cover both ordinary stderr and APK DSOs importing **versioned __sF@LIBC**")。
3. **liblog 供给**:`bionic_compat/src/liblog_android_supplement.cpp` **L26-33**:`__android_log_print/__android_log_buf_write/__android_log_security`——**这正是 anki 缺的 liblog.so 的核心内容**(Westlake 自带 liblog.so,anki 的 DT_NEEDED 直接可解)。
4. 同族供给:`malloc_compat.cpp`、`fdsan_stubs.cpp`、`libstdcxx_compat.c`、`android_native_network_compat.c`、`android_native_namespace_bootstrap.c`(目录 `framework/appspawn-x/bionic_compat/src/`)。
5. **ELF 清洗器**:`bionic_compat/tools/sanitize_android_elf.c` ——修 `DT_INIT_ARRAY/DT_FINI_ARRAY` 尾部 null/-1 哨兵:Android linker 跳过、旧 OH musl loader 逐项调用会跳 0。这是"load library header failed"的已知诱因类别之一(若清洗后仍 header failed 再查 ELF 头/段)。
6. 先例:webview-shim 的 LD_PRELOAD 垫片(`webview-shim/webview_bionic_shim.c` + .map;#76 Westlake 成功跑的 run.sh 里就有 `LD_PRELOAD=…/libwebview_bionic_shim.so`)。

## 四、照抄建议(cx-t0,native 活)

- **方案 A(Westlake 语义,推荐)**:给 v3a 的 app namespace 造"bionic ABI 供给库"——直接搬 `bionic_compat/src/*.c(pp)` + `native/bionic-abi.map` 版本脚本,链出 `libc.so`(带 LIBC version node)与 `liblog.so`,置入 route-a 代(payload 或 LD_PRELOAD)。一次解决 anki(liblog DT_NEEDED)+ netguard(`__errno@LIBC`)并预防所有 NDK app 同族(与本会话早前 `benchmark/2026-09-28-ndk-libandroid` 测得的 16 缺符号是同一 ABI 面,可并入同一供给库)。
- **方案 B(最小)**:在现有 native-runtime 库里追加 `__errno`/`__sF`/`__android_log_*` 三组源(不带 version node 时 netguard 的 `use_vna_hash` 版本化查找仍可能失败——所以 A 的 version script 是关键,不是可选)。
- **不修**:系统库 header failed 行(mmi_knuckle/security_component/artbased/hwui)。
- 诚实限界:`bionic-abi.map` 在 westlake-current 树内**未找到构建引用**(仅 git index 命中)——确切接线(哪个 CMake/脚本用它链 libc.so)需 cx-t0 在 `historical/` 或 build 记录里补;fd-droidify/fd-noice 已从本族剔除。
