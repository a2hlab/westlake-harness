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
