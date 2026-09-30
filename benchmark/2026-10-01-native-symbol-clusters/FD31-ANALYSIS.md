# mcdonalds fd 31 误关分析(2026-10-01,oc-t4,离线)

派单(板 ACK(95) 03:47):读 61b 那轮 faultlogs 的 fdsan 报告,查谁关了谁的 fd、关闭栈、属 app/westlake shim/OH 哪侧。

## fdsan 报告原文(faultlogs/fdsan-appspawn-x-20010663-20261001031006122.log)

```
Reason:Signal:DEBUG SIGNAL(FDSAN)
LastFatalMessage:attempted to close file descriptor 31, expected to be unowned, actually owned by FILE* 0x0000007f999206e8
Fault thread info:
Tid:2277, Name:com.mcdonalds.a
#00 pc 00000000000bfbc4 /system/lib/ld-musl-aarch64.so.1(fdsan_error+768)
#01 pc 00000000000bfee8 /system/lib/ld-musl-aarch64.so.1(fdsan_close_with_tag+688)
#02 pc 00000000000c005c /system/lib/ld-musl-aarch64.so.1(close+16)
#03 pc 00000000000871a8 /system/lib/ld-musl-aarch64.so.1(load_library_header+1192)
#04 pc 000000000009040c /system/lib/ld-musl-aarch64.so.1(preload_direct_deps+792)
#05 pc 0000000000083b9c /system/lib/ld-musl-aarch64.so.1(preload_deps+152)
#06 pc 0000000000086554 /system/lib/ld-musl-aarch64.so.1(dlopen_impl+2396)
#07 pc 000000000000d098 /system/bin/appspawn-x(StockOpenNamespace+208)
#08 pc 00000000000040bc /system/lib64/westlake/route-a/[redacted]/libapp_native_loader.so(ANL_Dlopen+1104)
#09 pc 0000000000006984 /system/lib64/westlake/route-a/[redacted]/libnativeloader.so(westlake::nativeloader::Registry::Open+1732)
#10 pc 0000000000003c98 /system/lib64/westlake/route-a/[redacted]/libnativeloader.so(OpenNativeLibrary+548)
#11 pc 00000000004f52c4 /system/lib64/westlake/route-a/[redacted]/libart.so(art::JavaVMExt::LoadNativeLibrary+2112)
#12 pc 00000000000070e8 /system/lib64/westlake/route-a/[redacted]/libopenjdkjvm.so(JVM_NativeLoad+348)
#13 pc 00000000001fcaa8 /system/android/framework/arm64/boot.oat(art_jni_trampoline+152)
#14 pc 00000000004e7b69 /system/android/framework/core-oj.jar
```

## 关闭栈解读

**谁关了谁的 fd**:appspawn-x 的 com.mcdonalds.a 线程(Tid 2277)在 `LoadNativeLibrary` → `JVM_NativeLoad` → `libnativeloader::Registry::Open` → `ANL_Dlopen` → `StockOpenNamespace` → `dlopen_impl` → `preload_deps` → `preload_direct_deps` → `load_library_header` → `close` 路径上,试图 close fd 31。

**fd 31 的归属**:fdsan 报 `expected to be unowned, actually owned by FILE* 0x0000007f999206e8`——fd 31 被一个 `FILE*`(musl stdio)持有,但关闭者(appspawn-x 的 dlopen 路径)不知道这个 FILE* 的归属,直接 close 了它。这是**双重关闭**(double-close)或**跨层关闭**(FILE* 层与 raw fd 层不同步)。

**关闭栈归属**:
- **app 侧**:`com.mcdonalds.a` 线程是 app 自己的线程(Java 线程名),但关闭动作在 native 层。
- **westlake shim 侧**:`libapp_native_loader.so`(ANL_Dlopen)、`libnativeloader.so`(Registry::Open/OpenNativeLibrary)、`libart.so`(LoadNativeLibrary)、`libopenjdkjvm.so`(JVM_NativeLoad)——**关闭发生在 westlake 的 native 加载路径**(appspawn-x 的 dlopen 链)。
- **OH 侧**:`ld-musl-aarch64.so.1`(fdsan_error/fdsan_close_with_tag/close/load_library_header/preload_direct_deps/preload_deps/dlopen_impl)——**fdsan 检测在 OH musl libc 层**,但触发关闭的是 westlake 的 dlopen 调用。

**结论**:fd 31 误关发生在 **westlake shim 的 native 加载路径**(appspawn-x 的 `StockOpenNamespace` → `ANL_Dlopen` → `libnativeloader::Registry::Open` → `dlopen_impl` → `load_library_header` → `close`),关闭了一个被 musl `FILE*` 持有的 fd。这是 **westlake 的 native 加载器在 dlopen 预加载依赖时,误关了 stdio 层的 fd**——属于 **westlake shim 侧**(`libapp_native_loader.so`/`libnativeloader.so`)的 fd 管理缺陷。

## subwaysurfers/firefox CoroutineStart 行号(给 cc-wiki)

**subwaysurfers**(hilog.txt):
- L60688: `10-01 03:12:51.207 6383 6409 I C00f00/AppSpawnXJava: [stderr] [COROUTINE-FIX] appCl=dalvik.system.PathClassLoader[...]`
- L60689: `10-01 03:12:51.208 6383 6409 I C00f00/AppSpawnXJava: [stderr] [COROUTINE-FIX] primeCoroutineStart FAILED (non-fatal): java.lang.ClassNotFoundException: kotlinx.coroutines.CoroutineStart`
- L42799-42803: `10-01 03:12:50.393 6383 6409 E C00f00/appspawn-x: [class_linker.cc:8419/8487/8648/8653] [VTLEN/IFACE-RAW/IFACE-BITS] klass=kotlinx.coroutines.r0 ...`

**firefox**(hilog.txt):
- L35573: `10-01 03:14:11.505 8149 8172 E C00f00/appspawn-x: [class_linker.cc:8653] [IFACE-BITS]   m[4]=void kotlinx.coroutines.DispatchedTask.handleFatalException$kotlinx_coroutines_core(java.lang.Throwable) curIdx=0 willSkipAppend(IsBitSet)=0`
- L30743-30755: `10-01 03:14:10.131 8149 8149 E C00f00/appspawn-x: [class_linker.cc:8648/8653] [IFACE-BITS] klass=com.android.internal.os.AppSpawnXInit$BackgroundTolerantUncaughtHandler / $2 / $1 ...`

**写入路径更正**:benchmark/2026-10-01-native-symbol-clusters/ 在 master 工作树(未跟踪,外环 03:47 已采纳入库 commit a3474d758)。本文件(FD31-ANALYSIS.md)写在同目录,属 master 工作树——外环已采认该目录,后续文件应写在自己 worktree(westlake-harness-t4)的 benchmark/ 下,待外环代提交。

## 外环批注(2026-10-01 03:52)

归属「westlake shim 侧误关」不采认,改记为假设。fdsan 报的是「fd 31 应无主,实际归 FILE* 0x7f999206e8 所有」:加载器在 load_library_header 里 close 自己刚 open 到的 31 本身合法,fdsan 在这里只是**发现**了不一致。元凶是更早一次绕过 FILE* 直接 close 了那个 FILE 的 fd 31 的调用(号被复用后 fdsan 表里还记着旧主)。待查:同 PID 更早的 fdsan 告警、那个 FILE* 由谁 fopen、是否有走 bionic 兼容层或裸 syscall 的 close 绕过了 fdsan。
