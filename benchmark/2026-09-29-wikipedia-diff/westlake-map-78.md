# #82: route-A 死点 → Westlake 实现对照(前 5 段,按「一段救几个」排序)

输入:#78 triage-summary(#78 里 Westlake 曾亮、route-A v3a 死)。源:`~/a2hlab/westlake-current`(一手行号)。排序依据:每段实现直接救的 app 数 + 间接收益。

## 1. bindService 桥(直接救 termux;间接:一切绑定型 app)

- **route-A 死点**:termux `RuntimeException: bindService() failed`(`J_invokeStaticMain_main_threw`,Unable to start activity TermuxActivity)
- **Westlake 实现**:`framework/activity/java/ActivityManagerAdapter.java` **L355-375 `[BRIDGED] bindService`**:双路——① `isInAppService(comp)` → 进程内服务(`ServiceConnectionRegistry.registerConnection` + `bindInProcessService`,L362-367,Handler 异步 post 匹配 AOSP 契约);② 否则 `IntentWantConverter.intentToWant` → `nativeConnectAbility(bundle, ability, connId)`(L368-372)。`bindServiceInstance` L377+ 同型。
- **照抄建议**:整体搬(bindInProcessService + ServiceConnectionRegistry + InProcessServiceBinder + ConnectAbility native 路径);Connection 回调经 registry 反查。
- **受益面**:termux 直接;所有在 Activity 启动路径调 bindService 的 app(计分器按 #78 后续跑分)。

## 2. VelocityTracker 运行期注册(直接救 fd-auxio;间接:mcdonalds 等 CoordinatorLayout/BottomSheet 系)

- **route-A 死点**:fd-auxio `UnsatisfiedLinkError: android.view.VelocityTracker.nativeInitialize`
- **Westlake 实现**:`framework/android-runtime/src/android_view_VelocityTracker.cpp`(文件头注释即原因:oh_input_bridge 的同款桩只在触控注入时注册,而 app 在首次 view attach 就 `obtain()`;McDonald's 死例与 #78 fd-auxio 同型)+ `AndroidRuntime.cpp` L162/L265 运行期注册表。
- **照抄建议**:整文件 + 注册表项;中性值策略(handle 非零、velocity 恒 0,fling 退化为 position-only——注释明言这是诚实行为)。
- **受益面**:fd-auxio 直接;任何在 attach 期 obtain VelocityTracker 的 CoordinatorLayout 系 app。

## 3. JobScheduler 存根(直接救 ooniprobe;间接:一切 WorkManager/JobInfo 系)

- **route-A 死点**:ooniprobe `IllegalStateException: WorkManager is not initialized properly`(manifest 里 disabled WorkManagerInitializer,pinned APK 证实 `nr2.a line10 dereferences getSystemService(jobscheduler)`)
- **Westlake 实现**:`framework/appspawn-x/java/com/android/internal/os/AppSpawnXInit.java` **L2058-2110 `installJobSchedulerStub()`**(L1086 调用,J_after_installJobSchedulerStub):反射替换 `SystemServiceRegistry.SYSTEM_SERVICE_FETCHERS["jobscheduler"]` 为 no-op 调度器(接受/查询/取消自洽、永不触发);配 `mainline-stubs/.../JobSchedulerFrameworkInitializer.registerServiceWrappers() no-op`(文件头注释:OH 无 APEX,真实注册器会炸 clinit)。
- **照抄建议**:两件一起搬(stub fetcher + mainline initializer no-op);WorkManager 的 on-demand 初始化需要 jobscheduler 非 null 才走通。
- **受益面**:ooniprobe 直接(WorkManager on-demand 路径);#73 里 mindustry/burgerking 的 jobscheduler 计数族。

## 4. addToDisplay 窗口类型桥(直接救 aegis)

- **route-A 死点**:aegis `InvalidDisplayException: the specified window type 1 is not valid`(ViewRootImpl.setView 前的类型白名单拒绝)
- **Westlake 实现**:`framework/window/java/WindowSessionAdapter.java` **L593-660 `addToDisplay`**:不做 Android 类型白名单拒绝——直接把 `attrs.type` 映射进 OH `ISceneSessionManager.CreateAndConnectSpecificSession`(L601-604 logBridged),MATCH_PARENT/WRAP_CONTENT 就地解析为真实分辨率(L609-620 G2.14ak 注释),token 经 `OhTokenRegistry.findOhToken` 反查(L637-641)。
- **照抄建议**:route-A 的窗口添加路径改走 addToDisplay 桥;关键是**不预校验 Android window type**,交给 OH 侧。若 route-A 是 ViewRootImpl 内 AOSP 白名单拒绝,需在 runtime jar 侧 patch 该校验或 hook WindowManagerGlobal。
- **受益面**:aegis 直接;任何加非应用窗口(type 1=APPLICATION)以外类型的 app。

## 5. 主题两件套(直接救 fd-fitness、fd-noice;wikipedia 已由 r13 对上)

- **route-A 死点**:fd-fitness `You need to use a Theme.AppCompat theme`;fd-noice `InflateException: Binary XML line #26`
- **Westlake 实现**:已完整交付 #81 `activity-theme-segment.md`(五步链+ASX_KEEP_THEME);r13 `resolveActivityTheme` 已对上,cc-t3 5cd 实测 minetest/opencamera 越过。
- **照抄建议**:r13 已做,无需重抄;此处仅登记 fd-fitness/fd-noice 归入该修复的受益表。
- **受益面**:fd-fitness、fd-noice(+#75 的 fd-minetest、noice;#78 的 wikipedia)。

## 未进前 5(记录在案)

- antennapod `SharedPreferences.getString` NPE:Westlake 树无独立 SharedPreferences 实现(由完整 BCP 的 ContextImpl 提供);需查 route-A 侧谁返回 null prefs(疑 dex/ContextImpl 桥缺口),不属"照抄一段"可救。
- fd-com-amaze `NoClassDefFoundError AppConfig`:疑多 dex/classloader 次序,待 route-A 侧日志深挖。
- fd-com-kunzisoft `Cannot create instance of DatabaseViewModel`:ViewModel 工厂链,同上待挖。
- fd-netguard `MUSL-LDSO __errno relocating failed`:bionic/musl 符号兼容层(非 Java 段),另案。
- fd-AppManager / fd-droidify:#78 标 alive_at_samples(无死点),不列。

---

# 续:#78 余下 4 个定案 + #73 的 12 个早死 app 对照(按「一段救几个」排序)

## #78 余下 4 个(定案:均无「照抄一段」解)

| app | 死点 | 定案 |
|---|---|---|
| antennapod | `SharedPreferences.getString` NPE | Westlake 无独立 prefs 实现(由完整 BCP 的 AOSP ContextImpl/SharedPreferencesImpl 提供,全树仅 preloaded-classes 清单提及);**非可抄段**——需在 route-A 侧查谁返回 null prefs(疑 ContextImpl 桥缺口)。已知同类:#48/#60 时代 `ContextImpl.getSharedPreferences SIGSEGV`(B6 族),指向同一运行时缺口 |
| fd-com-amaze | `NoClassDefFoundError: AppConfig` | 多 dex/类加载次序疑;Westlake 无 multi-dex 特殊处理段(AppSchedulerBridge 只保证 APK 入 DexPathList L1540s)。需 route-A 侧 logcat 的完整异常栈定位 |
| fd-com-kunzisoft | `Cannot create instance of DatabaseViewModel` | ViewModel 工厂链(缺 SavedStateFactory/ArgumentListModel?);Westlake framework 无 ViewModel 处理段。需 route-A 栈 |
| fd-netguard | `MUSL-LDSO __errno relocating failed` | musl↔bionic 符号兼容层,**非 Java 段**,另案(Westlake 用自带 bionic 桥/自带库路径避开) |

## #73 12 app → Westlake 段(总排序,与前 5 合并)

**6. native 库路径域(新段王:直接救 6 个)** —— `PackageInfoBuilder.java` L205-242:`nativeLibraryDir` 先取 OH 值,否则 APK 相邻探测(`sourceDir/../lib/<abi>`、`lib/arm`、APK 根,逐个 isDirectory),兜底 dataDir;`mapAbi` L309-313 强制 arm64-v8a 映射;配 spawn_server L194-195(`ASX_NATIVE_LIB_DIR` env 直指自家 lib)。**关键语义:Westlake 从不把 app 库加载路由进 OH namespace 域检查**(它有自己的 runtime root + LD_LIBRARY_PATH),所以 `path is outside app domain` 与 `dlopen_ns failed` 在 Westlake 路线不存在。
- 救:fd-fluffychat、fd-immich、fd-kitchenowl、localsend(Flutter 路径域外 ×4)+ mindustry、burgerking(dlopen_ns ×2)= **6 个**
- 照抄:①PackageInfoBuilder 的探测+mapAbi(B8 INVENTORY 第 4 项已列);②Flutter 特例:外环已批的 Impeller 回退 + 把 OH native loader 的域检查改为白名单放行 app data 路径(Westlake 语义)

**7. 主题两件套(r13 已做)** —— fd-minetest、fd-noice(+#78 wikipedia/fd-fitness)。#81 五步链已交付。

**8. JobScheduler 存根(#82 第 3 段同源)** —— ooniprobe。

**9. addToDisplay 窗口桥(#82 第 4 段同源)** —— fd-stk(InvalidDisplayException 同 aegis 型)。

**10. manifest className 应用** —— fd-mobile(KoinApplication not started = 自定义 Application 未实例化):Westlake `AppSchedulerBridge` L1568-1571 `m.optString("appClassName") → ai.className`(native 侧 apk_manifest_jni 已序列化 appClassName L343-344)。r8b 已有投影但 #73 实测 Koin 未跑——疑 route-A 投影缺 appClassName 字段或 bind 时序,需 cc-t3 核 r13 的 ManifestJsonFallback 是否含它。

**11. notification(无 Westlake 段,r13 已带)** —— fd-etar(NPE `INotificationManager.createNotificationChannelGroups`):Westlake framework **无 notification adapter**(全树仅 setServiceForeground stub,ActivityManagerAdapter L460-466;LocalServiceBinders 无 notification 项)——Westlake 亮过 etar 说明它走的别处(或当时容忍了)。r13 已含 notification 空桩(cc-t3 提交记档),直接验证即可,无需抄。

## 合并后的 r15 建议包(一段救几个,降序)

1. **native 库路径域**(6)+ 主题(4,#78+#73 合计)→ r15 主体
2. addToDisplay 桥(2:aegis+fd-stk)
3. JobScheduler 存根(2:ooniprobe+termux 族)、bindService(1+族)
4. appClassName 应用(1:fd-mobile,核 r13 是否已含)
5. VelocityTracker(1+族)
6. notification(r13 已带,验证 fd-etar)
