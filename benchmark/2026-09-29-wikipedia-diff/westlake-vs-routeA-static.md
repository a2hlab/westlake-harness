# #81: Westlake vs route-A — Wikipedia 启动路径静态对照(全段)

限时首段「Activity 主题」已单独交付(`activity-theme-segment.md`,黑板 17:2x);本文件是全段汇总。来源:`~/a2hlab/westlake-current`(VM,一手行号)vs route-A(`bms/src/adapter/framework/**` + r8b JAR d5000c4e)。离线,未上板。

## 段 1 — Application(容忍式未捕获处理)

| | Westlake | route-A 现状 |
|---|---|---|
| 父进程(zygote) | `AppSpawnXInit.preload()` L209:setDefaultUncaughtExceptionHandler,只打日志不杀进程("background thread 死不能拖死 appspawn-x") | — |
| 子进程 | `initCommonRuntime()` L2421 同款 handler:明确注释「**不 System.exit(1)**——后台/daemon 线程的未捕获异常曾把整个 fork 子进程杀在 init 中途;主线程异常由 initChild 的 try/catch 兜住;handler 只 LOG + printUncaughtFrames + cause 链,让单个线程死、进程活」 | #76 实测:同一 NPE 经 provider 安装主线程传播 → `ensureBindApplication FAILED` → exit 1。#76 的分叉点即此处 |

**route-A 缺**:bind/install 路径的容忍语义(r13 已并入?需 cc-wiki 在 5ea 验证;若未并入,照 AppSpawnXInit L2421 的 handler + ensureBindApplication 外层 try/catch-继续抄)。

## 段 2 — provider(B8 第 1/2 项,Wikipedia 死点)

Westlake `PackageManagerAdapter.java`(framework/package-manager):
- **getProviderInfo L1123-1133** `[BRIDGED]`:先 `SourcePackageRegistry.contains(pkg)` → `packageInfo(pkg, GET_PROVIDERS)`(PackageParser 产物,带 metaData)→ 按 className 匹配返回;否则回退 `ProviderInfoResolver.resolve`
- **queryContentProviders L1301+** `[BRIDGED]`:uid → 遍历 `nativeGetAllBundleInfos` 反解 packageName → `collectProvidersForPackage`
- **collectProvidersForPackage L1357+**:SourcePackageRegistry 有则取 PackageParser 结果(带 GET_META_DATA);否则 `getApkManifestJson(pkg)` → manifest JSON 的 `providers[]` 逐个构造 ProviderInfo(共享 ApplicationInfo)
- **getProvidersForPackage L1351**(public static):AppSchedulerBridge 在 bindApplication 时填 `AppBindData.providers` 用
- **resolveContentProvider L1289:在 westlake-current 源码树里是 logStub+return null**——与 B8 INVENTORY 所述「smali :5274 authority 匹配」不符,说明 **INVENTORY 描述的实现在 smali 层(打了补丁的产物),Java 源码树这一项未同步**。给 cc-wiki 的注意项:抄的时候以 smali 为准,或确认 Java 树的 resolveContentProvider 是否在上板构建里被 smali 补丁覆盖。

route-A 现状:r8b 有 manifest 投影(`providers populated: N`,#73 实测计数与 #69 静态表吻合),但 own-package `getProviderInfo` 桥接(B8 第 1 项)缺——#76 Westlake 侧 `[BRIDGED] getProviderInfo: androidx.startup.InitializationProvider` 有调用记录,route-A 侧无。

## 段 3 — Activity.attach / 派发事务

Westlake `AppSchedulerBridge.java`:
- L1643-1756:构造 ClientTransaction + `LaunchActivityItem.obtain(...)`,L360/1748 `scheduleTransaction(tx)` → stock `ActivityThread.handleLaunchActivity()`
- 每窗 LayoutParams 记忆:WindowSessionAdapter L200-214(`mWindowAttrs`,ViewRootImpl 只在变化时传 attrs,gravity/x/y/flags 靠这里保活)
- `WL_SYNC_TRANSACTION=1` 时同步 executeTransaction(L1865 附近)——边界 worker 无 Looper 唤醒集成的兜底

route-A:r13 已含同类 SLA 桥(#73 实测 `[B47-SLA]` 到达);分叉不在派发本身。

## 段 4 — Activity 主题(见 activity-theme-segment.md,摘要)

解析(apk_manifest_parser.cpp L368/L467)→ 序列化只带应用主题(jni L345;activity 条目 L134-141 不带)→ bind 富化(L1574)→ buildActivityInfoFromAbility 回退 appInfo.theme(L1075)→ SLA 开关 ASX_KEEP_THEME(L1817-1860:默认双清零,KEEP 时保留+app 主题回落=stock 行为)。route-A 的 SLA 早于 bind 富化 → ActivityInfo.theme 恒 0 → 默认 framework 主题 → `0x7f04032a` 解析不到。r13 `resolveActivityTheme` 补的正是这一段。

## 段 5 — 包查询

- `getActivityInfo` L801-805 `[BRIDGED]` → BMS.QueryAbilityInfo(#76 两板都见 `[BRIDGED] getActivityInfo: org.wikipedia/.main.MainActivity`)
- `getPackagesForUid/getNameForUid` L1145-1157:SourcePackageRegistry.packageForUid 反解

## 段 6 — 首帧

- VSync/Choreographer 源:`framework/android-runtime/src/android_view_DisplayEventReceiver.cpp` + `android_os_MessageQueue.cpp`(native 层 fd/回调桥)
- relayout:WindowSessionAdapter(宽度 clamp 的 CLAMP48 在 smali/产物层,Java 树见 relayout 相关注释 L109-143「避免无限 relayout 环」)
- 首帧监听:activity/java 侧 first-frame listener(#76 Westlake 侧 `LaunchActivity transaction scheduled` 后直接到 onboarding)

## 给 #80(cc-wiki)的行动序(按此对照)

1. r13 主题修复先上(段 4,r13 已做);验证 Wikipedia 过 `Attribute not found 0x7f04032a`
2. 段 1 容忍 handler 若 r13 未含,照 AppSpawnXInit L2421 抄(bind 路径 try/catch)
3. 段 2 的 own-package getProviderInfo(B8 第 1 项)照 Java 树 L1123-1133 + ProviderInfoResolver
4. 段 2 的 resolveContentProvider 以 smali 为准(INVENTORY :5274),Java 树是 stub——两者不一致,勿盲抄 Java
5. 段 6 CLAMP48/Impeller 回退见 INVENTORY(外环已列)
