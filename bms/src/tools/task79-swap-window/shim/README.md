# Noice 点亮 —— 板上 shim（板 5ce2dcee，OpenHarmony-6.1.0.31）

这里是**跑在板子上的东西**，不是 substrate 源码。substrate（`src/adapter/`）在这块板上
是只读的：`BOARDS.toml` 把 `原 substrate 覆盖` 列进禁止项，所以所有修补都只能从
`LD_PRELOAD` 这一侧做。

## 是什么

`appspawn-x` 起来时预加载两个 .so：

| 件 | 作用 |
|---|---|
| `libwl_stackgrow.so`（`wl_stackgrow.c`） | 在 ART 读主栈边界之前把栈先撑开，免得被冻在 128 KB 并把 guard page 放在那儿 |
| `libwl_sqlite_jni.so`（`wl_sqlite_jni.cpp`） | 这套 substrate 没带的 SQLite JNI，外加下面一串修补 |

`wl_sqlite_jni.cpp` 里现在做这些事（按重要性，不按代码顺序）：

1. **WLTG 放行**（`WLTG_VerifyCurrentThreadReady`）—— 全场最关键的一处，见下。
2. **`ApplicationInfo` 补字段** —— `theme` / `className` / `targetSdkVersion`，
   补 substrate 的 AXML 解析器漏掉的 `<application>` 属性。
3. `<clinit>` 修复 —— imageless runtime 把一批 boot classpath 类标成 kInitialized
   但没跑过 `<clinit>`；逐个 `CallStaticVoidMethod(<clinit>)` 补回来。
4. `ResumeActivityItem` 注入 —— substrate 排的 launch transaction 的
   `mLifecycleStateRequest` 是 null，activity 会停在 onCreate。
5. 拆掉 substrate 的默认 uncaught-exception handler —— 它会杀进程，
   而这套环境里后台线程抛异常是常态（见下面 java.security 那条）。
6. 主窗复用注入（`OhTokenRegistry.setMainSessionId`）—— 绕开这块板上不存在的 legacy WMS。
7. `ScopedJniAttachment` ABI 错位垫片 —— 板上两个 .so 对这个类的大小差 24 字节
   （bridge 认 160、runtime 认 136），OH 的 vsync 回调每次都因此堆越界，
   紧跟的 `free` 撞 musl 堆断言变成无限 SIGSEGV 循环，屏幕就永远出不来。
   拦下构造/析构，用够大的影子对象跑真实现，再把字段按老布局投影回去。
   详见 `docs/noice-lightup/07-deploy-lessons.md` 第二十二节。

## 怎么用

```sh
# mac-server 上编（板子在 mac-server 上；本机不接 hdc 设备）
bash build_sqlite_jni.sh          # 需要同目录下的 sqlite3.c（SQLite 官方 amalgamation）

# 推到板上
hdc -t $B file send libwl_sqlite_jni.so /data/local/tmp/libwl_sqlite_jni.so
hdc -t $B file send start-a13-sql.sh    /data/local/tmp/start-a13-sql.sh

# 板上重起 daemon 再拉起应用
hdc -t $B shell sh /data/local/tmp/start-a13-sql.sh
hdc -t $B shell aa start -b com.github.ashutoshgngwr.noice \
    -a com.github.ashutoshgngwr.noice.activity.MainActivity -m entry
```

`hdcenv.sh` 只是 `$HDC` 和 `$B` 两个变量。`run5.sh` 是一把梭的跑一轮＋抓日志。
`axmldump.py` / `dexmethods.py` 是离线读 APK 的：前者把二进制 AndroidManifest.xml
打出来（`android:name` / `android:theme` 就是这么查到的），后者列 dex 里某个类的
全部方法字段签名。

## 关掉某项修补

全部走环境变量，默认都是开的：

| 变量 | 效果 |
|---|---|
| `WL_NO_WLTG_OVERRIDE` | 不放行线程守卫，回到原状（应用会卡在 looper 里不动） |
| `WL_NO_MAIN_REUSE` | 不做主窗复用，走原来的 `CreateWindow` 路（会 1005 然后死） |
| `WL_KEEP_KILL_HANDLER` | 保留 substrate 的杀进程 handler |
| `WL_REPAIR_SECURITY` | 尝试修 `java.security`（**别开**，见下） |
| `WL_ZERO_OH_TOKEN` | 把 OH ability token 清零（死路一条，留着只为复现） |
| `WL_NO_SJA_ABI_SHIM` | 不修 `ScopedJniAttachment` 的 24 字节 ABI 错位（vsync 线程会满核空转，应用被生命周期超时打死） |
| `WL_NO_MQ_DUMP` | 不再定时打印主线程消息队列 |
| `WL_NO_PC_PROBE` | 不再对 `DER-vsync-oh` 做 SIGPROF 栈采样 |
| `WL_NO_RP_PROBE` | 不再打印渲染链路（`ViewRootImpl.mSurface` / `ThreadedRenderer` / OH surface bridge） |
| `WL_FORCE_BLAST` | 把活的 `ViewRootImpl.mUseBLASTAdapter` 翻成 true（默认关；见下） |
| `WL_FORCE_SOFTWARE_RENDER` | 清掉 `ApplicationInfo.FLAG_HARDWARE_ACCELERATED`，逼 ViewRootImpl 走软件绘制（默认关） |

## 白屏诊断：这三个开关是怎么用的

2026-08-03 用它们把白屏定到了根上，结论见
`docs/discussions/2026-08-03-blank-screen-root-cause-window-protocol.md`。要点：

- `WL_NO_RP_PROBE` 不设时，fixer 线程在 t=10/18/26s 各打一次渲染链路快照。
  最有用的三行是 `mSurface isValid/mNativeObject`、`ThreadedRenderer` 的
  `mEnabled/mInitialized`，以及 `oh_wm_get_last_session` / `oh_wm_get_native_window`。
  最后那两个是 `dlsym(RTLD_DEFAULT, ...)` 直接调 bridge 的导出符号——**必须这么问**，
  因为 bridge 自己的 `HiLogPrint(LOG_CORE, ...)` 在 app uid 进程里会被 hilogd 全部丢掉。
- `WL_FORCE_BLAST` 和 `WL_FORCE_SOFTWARE_RENDER` 是当时的两条备选修法，
  **实测都救不了**：Surface 本身就是空的（`mNativeObject=0`），
  换哪条绘制路径都没有画布。留着是因为它们把"不是绘制路径选错"这件事证死了。

`WL_APP_THEME` / `WL_APP_CLASS` / `WL_APP_TARGET_SDK` 在 `start-a13-sql.sh` 里给值。

## 三条别人踩了会再疼一次的

**一、`java.security` 是坏的，但千万别修。**
imageless runtime 让 `java.security.Security` 没跑 `<clinit>`，`spiMap` 是 null，
`MessageDigest.getInstance` 必 NPE。看着像该修，一修就更糟：强跑
`Security.<clinit>` / `Providers.<clinit>` 会让 JCA 去实例化 conscrypt 的
`OpenSSLProvider`，那要 `libjavacrypto.so` —— **这块板上没有这个文件**。
`ProviderConfig.doLoadProvider` 只 catch `Exception`，`UnsatisfiedLinkError` 是
`Error`，直接穿出去打死 `handleBindApplication`，`mInstrumentation` 留成 null，
最后现场变成 `performLaunchActivity` 里一个跟真凶毫无关系的 NPE。
**正确处理是放着不修**，靠第 5 项（拆掉杀进程 handler）让它只是个后台异常。

**二、这块板没有 legacy WindowManagerService。**
`/system` `/vendor` 下**没有 `libwms.z.so`**。SA 4606 是 SceneBoard 那套在服务
（foundation pid 里加载的是 `libscene_session.z.so` / `libsession_manager.z.so`），
它答的是 `OHOS.ISceneSessionManager`；而 substrate 的
`oh_window_manager_client.cpp` 写的 interface token 是 `OHOS.IWindowManager`。
token 对不上 → stub 拒收 → `WMError 1005` → `addToDisplay` 返回 -9 →
`InvalidDisplayException`。
**和 ability token 无关**：拿真 token（`ohTokenAddr=0x7f7fe8d1a0`）跑，一模一样的 1005。
substrate 那条 legacy 路是在还带 libwms 的 OH 7.0.0.18 镜像上验的。

**三、板上 `grep -c` 对二进制不可信。**
toybox 的 grep 在 .so 上会返回 0，据此得出的"这个库里没有某某符号"是假的。
要查符号就把 .so 拉下来用 `llvm-nm -D` / `llvm-readelf`。
（macOS 这边 `strings -el` 也不支持，用 python 正则扫 utf-16-le。）
