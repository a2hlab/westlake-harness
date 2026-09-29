# r17 Java 批照抄清单 —— provider-install 9 + null-service 4(30 分钟限时,交 cc-t3 r17)

证据:r16 全量(5cd/61b)各 app hilog 的 ensureBindApplication FAILED 后首个/最深 Caused by(一手);Westlake 锚:vm-copies/westlake-current @ `532633d`。**先读分组结论:13 个 app 实际只塌缩成 6 段修复,其中 3 段已有包。**

## 分组 A —— CommonEvent JNI 缺(4 app:burgerking@5cd / fd-minetest@5cd / termux@61b / +r16 墙③的 etar/vlc/wikipedia/netguard)

- 致命点原文(同型):`Unable to get provider <app provider>: UnsatisfiedLinkError: No implementation found for int adapter.activity.ActivityManagerAdapter.nativeSubscribeCommonEvent(...)`
- route-A 出错点:provider 安装期(installContentProviders→attachInfo→app onCreate 里 subscribeCommonEvent)调到**未注册的 CommonEvent native**
- Westlake 对应:`framework/activity/jni/activity_manager_adapter.cpp` L196-234 注册表(nativeSubscribe/Publish/Finish/GetSticky,5 项)+ `framework/broadcast/jni/oh_common_event_client.{cpp,h}` 后端
- 改法:**已建包直接用**——`bms/src/adapter/framework/native-compat/westlake-commonevent/`(commit f6a60fc0,7 文件原样 cmp+build.sh),链进 runtime native 库 + 启动调 `register_ActivityManagerAdapter(env)`。一段救 4+4。

## 分组 B —— provider 权限未投影(3 app:fd-client / fd-minetest 同因叠 CommonEvent / termux 同因叠 CommonEvent)

- 外环样例对齐:fd-client `DocumentsStorageProvider: Provider must be protected by MANAGE_DOCUMENTS`(SecurityException)
- route-A 出错点:合成 ProviderInfo 时**没从 manifest 带 readPermission/writePermission**(manifest 投影只填了 authority/name)
- Westlake 对应:`framework/package-manager/java/PackageManagerAdapter.java` **L1403-1406**(`pi.authority` / `pi.readPermission=nullIfEmpty(...)` / `pi.writePermission`)+ native 侧解析 `apk_manifest_parser.cpp` **L525/L528**(ATTR_READ_PERMISSION/ATTR_WRITE_PERMISSION)+ 序列化 `apk_manifest_jni.cpp` **L111**
- 改法:r17 的 ManifestJsonFallback/collectProviders 投影加这三行字段(readPermission/writePermission 按 nullIfEmpty 语义)。**修完这组,fd-client 过 provider 门;minetest/termux 还需 A 的 CommonEvent 包**(两者叠加)。

## 分组 C —— Kotlin coroutines 类缺失(3 app:fd-calendar@5cd / fd-feeder@5cd / fd-wifianalyzer@61b,+ r15c 的 filemanager)

- 致命点原文:`ClassNotFoundException: kotlinx.coroutines.CoroutineStart`,栈:`Class.classForName ← Class.forName(:536)` 由 `[COROUTINE-FIX] primeCoroutineStart` 调起(r16 的 runtime JAR 自带这个 fix,但**用 Class.forName 查、找不到就 CNFE**)
- **外环问的"哪条查找路径漏了"定案**:primeCoroutineStart 用的是 `Class.forName`(bootstrap classloader 视角),而 app 的 `kotlinx-coroutines-android` 在 **APK 的 PathClassLoader** 里;Class.forName 不走 caller-classloader 回退 → 必 CNFE。Westlake **没有** COROUTINE-FIX 这段(它不需要——完整 BCP 下 app 类加载器天然可达),树内无对应实现可抄
- 改法(cc-t3,r17 一行级):COROUTINE-FIX 的 `Class.forName("kotlinx.coroutines.CoroutineStart")` 改为**用 appCl 变量**(同一行日志里现成有 `appCl=PathClassLoader[...]`)做 `Class.forName(name, false, appCl)`;失败保持 non-fatal。这解三个 app 的 CNFE。
- **fd-calendar 特别注**:CNFE 是 non-fatal;它的真死因是其后 `JobScheduler.cancel(int) on a null object reference`(r16 `OnlineJobScheduler` 装了但 `getSystemService(JobScheduler.class)` 返回 null——**类查找路径**:`SystemServiceRegistry` 的 fetcher 走 ServiceManager("jobscheduler") binder 名,r16 的 Online 装置若只挂在 IActivityManager 代理上、没替换 SYSTEM_SERVICE_FETCHERS,类路径就拿不到)。Westlake 对应:`AppSpawnXInit.java` **L2058-2110 `installJobSchedulerStub()`**(反射换 SYSTEM_SERVICE_FETCHERS 条目,构造 JobSchedulerImpl(ctx, noopBinder),L1086 调用)——**照抄这段**(fetcher 替换,不是服务代理),cancel 永远打在非 null 上。

## 分组 D —— app 自身初始化序(3 app:fd-tasks / mcdonalds / x)

- fd-tasks:`TaskProvider: kotlin.UninitializedPropertyAccessException: lateinit property workerFactory has not been initialized`——WorkManager on-demand 模式要求 Application 实现 Configuration.Provider 且先 initialize;与 ooniprobe 同根(jobscheduler null → WorkManager 走默认初始化路径失败)。**修 C 的 installJobSchedulerStub 后重测**,大概率连过。
- mcdonalds:`InitializationProvider: StartupException` 深因 NPE(`Ord[erService?]` 接口 null)——null-service cast 族,修 C 的非 null fetcher 语义后重测。
- x:`MerchantProcessInit: IllegalStateException: The application object graph is not defined. Is your Application class calling se[tContenxt]?`——Dagger ObjectGraph 由自定义 Application 建;**appClassName 未被应用**(#82 段 10:AppSchedulerBridge L1568-1571 `appClassName→ai.className`)。核对 r13/r15 ManifestJsonFallback 是否含 appClassName 字段;缺则补一行投影。

## 分组 E —— Firebase UndeclaredThrowable(2 app:burgerking@5cd / firefox@61b)

- 原文:`FirebaseInitProvider: java.lang.reflect.UndeclaredThrowableException`(burgerking 后续即 CommonEvent A 组;firefox 是 JNA `libjnidispatch.so not found in resource path`——**Firefox 实际不是 Firebase 问题**)
- burgerking:先修 A,再看 FirebaseInitProvider 是否还有残余(其最深层 cause 是 nativeSubscribeCommonEvent,已在 A)。
- firefox 单列:JNA 从 APK resource 释放 native 库失败(`com/sun/jna/android-aarch64/libjnidispatch.so not found in resource path (.)`)。route-A 差异点:JNA 用 context.getClassLoader().getResourceAsStream 从 APK 提取;Westlake 走完整 ZipFile 资源路径。**改法(r17 可选)**:在 COROUTINE-FIX 同层的 runtime 启动处,或投影 ApplicationInfo 时保证 `sourceDir` 指向真 APK 并给 JNA 传 `jna.boot.library.path` env 指向已解压 lib 目录;最小实验先行(30 分钟内无法给出 Westlake 直接行号——树内 grep JNA 零命中,Westlake 没解过它,标注为新墙)。

## 分组 F —— 单例残墙(2 app:fd-immich@5cd / newpipe@61b)

- fd-immich:`InitializationProvider: E7.d: VerifyError` 最深层 `UnsatisfiedLinkError: current thread is not READY for guest dlopen`——**Flutter 门**,#91 log-and-allow(cx-t0 移植中)直接救,勿在 r17 重复做。
- newpipe:`Unable to start activity … NPE: BatteryManager.getIntProperty(int)` ——`getSystemService(BATTERY_SERVICE)` null(同 C 的 fetcher 语义)。Westlake 对应:`LocalServiceBinders.java` L49+ 的 proxy 注册表(power/thermalservice/alarm/clipboard/account/uimode 各 case)——**照 LocalServiceBinders 语义给 battery 项加 proxy**(IBatteryManager→status/int 默认值),或最简:同文件 default 分支返回可 cast 的空 Binder proxy。

## 执行序建议(r17 = C(3 行+fetcher 抄段)→ B(3 行投影)→ A(已建包接入)→ F(battery proxy)→ D 重测 → E 的 JNA 另案)

- C+B 是纯 Java 小改,C 解 3、B 解 1(独立)+2(与 A 叠)、A 解 4+4、F 解 1-2、D 随 C 免费解 1-2、E(firefox JNA)标注新墙不进 r17。
- 全部 Westlake 行号一手;唯一无源可抄处(JNA、COROUTINE-FIX 的 caller-classloader)已按实际差异写明改法。
