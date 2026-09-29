# #76: Wikipedia — Westlake 路线(成功)vs route-A(r8b+6cb 代,exit 1)第一个分叉点

采集:61b,2026-09-29。Westlake 侧复用板上 `a2hlab-source-0033a17c…` 运行时(run.sh 重写指向 runtime root,原样备份 .orig),`HOST_SPAWN result=0 pid=6592`,16M hilog(9.4 万行)全量落 `board/p76-westlake/wl-hilog.txt`,截图 136290B(YAVG=148.18)——**外环改判(R2,2026-09-29 17:5x):四张截图实为 61b 桌面而非 Wikipedia,YAVG 只能排除黑/白空,不能证明内容;本条'上屏'结论作废,Westlake 侧唯一可靠证据是 hilog 生命周期链**。route-A 侧 master `bms_batch.py`(r8b d5000c4e + 6cb40cd6 代),run 目录 `board/b4-76-wiki-routeA/…`,facts.txt:`keys=1 screenshots_captured=0/2 alive_t5=0 alive_t20=0`。

## 逐段对照(两边原文)

| 段 | Westlake(pid 6592,存活上屏) | route-A(pid 10604,exit code:1 @ ~2.3s) |
|---|---|---|
| attach/直接启动 | `[B32-J] J_direct_launch_armed pkg=org.wikipedia apk=…`(10:56:10.963) | `[OH_AMAdapter] attachApplication ENTRY pid=10604`(17:08:56.633),无 direct_launch(走 BMS 常规链) |
| provider 元数据 | `OH_PMAdapter [BRIDGED] getProviderInfo: ComponentInfo{org.wikipedia/androidx.startup.InitializationProvider}`(10:56:11.313)——**own-package provider 查询有实现** | `[B43-BIND] providers populated: 3`(17:08:56.703)——列表来自 r8b manifest 投影,无 per-provider 查询桥接记录 |
| androidx.startup / coil3 | coil3 `MemoryCacheService.open`/`RealImageLoader$execute$2` 的 NPE 栈出现在**后台线程 6618**(W/E 级,10:56:11.621-.625),未进主线程 bind 路径 | **主线程 provider 安装路径炸死**:`Unable to get provider androidx.startup.InitializationProvider` → `Caused by: coil3.network.HttpException: java.lang.NullPointerException: Attempt to invoke … getClass() on a null object reference` at `androidx.startup.AppInitializer.doInitialize(:110)`(17:08:57.458) |
| 主线程异常处置 | 主线程也有 NPE(`org.wikipedia.WikipediaApp.onCreate(:538)`,10:56:11.671,栈含 `AppSchedulerBridge.ensureBindApplication(:1328)`)——**被打印但容忍**(AppSpawnXInit$BackgroundTolerantUncaughtHandler),bind 继续 | `[B43-BIND] ensureBindApplication FAILED: java.lang.reflect.InvocationTargetException`(17:08:57.457)——同一 hook 位置(:311)直接失败 |
| Activity 派发 | `nativeOnScheduleLaunchAbility v2`(10:56:11.678)→ `LaunchActivity transaction scheduled: org.wikipedia.main.MainActivity`(10:56:11.679)→ `Intent -> Want: …onboarding.InitialOnboardingActivity`(10:56:11.870)→ 上屏 | SLA/MainActivity/InitialOnboardingActivity 的类链接都走到了(17:08:56.638-.487),但 bind 已死,17:08:58.327 `AppMS kill reason=OnRemoteDied` → 17:08:58.331 `exit with code:1` |

## 第一个分叉点

**provider 安装阶段的 androidx.startup → coil3 NPE 的处置差异。** 两边遇到同一个 NPE(`getClass() on a null object reference`,coil3 链);Westlake 侧它落在后台协程 + 主线程同类异常被 `BackgroundTolerantUncaughtHandler` 吞掉、bind 完成并继续到 onboarding;route-A 侧同一 NPE 经 `InitializationProvider.onCreate → AppInitializer.doInitialize(:110) → installContentProviders → handleBindApplication → ensureBindApplication(:311)` 变成 RuntimeException,进程退出,**从未到达 WikipediaApp.onCreate/MainActivity**。

## route-A 缺什么(给 cc-t3 #70 照抄的指引)

1. **容忍式 uncaught 处理器**:Westlake 有 `com.android.internal.os.AppSpawnXInit$BackgroundTolerantUncaughtHandler`(两边 hilog 均见该类链接;Westlake 打印栈不死,route-A 直接 FAILED)。候选来源:Westlake smali `AppSpawnXInit`( BackgroundTolerant 分支)——route-A 的 `AppSchedulerBridge.ensureBindApplication`(Java :311 一带)缺同款 try/catch-继续。
2. **own-package `getProviderInfo` 桥接**(B8 INVENTORY 第 1 项,Westlake `WL/packagemanager/PackageManagerAdapter.smali:3408` 经 SourcePackageRegistry/ProviderInfoResolver):Westlake 的 provider 查询走 BRIDGED 实现;route-A 只有 manifest 投影的静态列表,androidx.startup 运行期查询路径不同,coil3 初始化落点(主线程 provider vs 后台协程)随之不同。
3. 次要:Westlake 的 coil3 初始化不在主线程 bind 关键路径上(观察性结论,未穷证)。

## 诚实限界

- 两侧是不同运行时目录/不同代(Westlake 09-27 staged vs route-A 6cb+r8b),时间戳域不同(01-01 vs 09-29),对照只按事件序不按钟。
- `getClass() on a null` 的**根因对象**(哪个服务/资源为 null)未在两侧日志里显形;修容忍层后 app 可能仍缺该对象(下一步实验点)。
- Westlake 侧未重装 APK(复用既有安装);route-A 侧 --reinstall。
