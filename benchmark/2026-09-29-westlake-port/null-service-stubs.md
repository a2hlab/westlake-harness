# r17a 排名② null-service NPE 7 个 —— 服务桩表(30 分钟限时,交 cc-t3)

证据:r17a hilog 一手(最深 Caused by + 栈顶 + NPE 前最近的 `getService(...)→null` 行)。**共塌缩为 6 个服务缺口 + 1 个 PendingIntent 面。**

## 表(按挡住 app 数排序;机器可读版见 null-service-stubs.json)

| # | 服务/接口 | 挡住 app | NPE 原文(一手) | 缺的方法 → 类型正确返回 | Westlake 对应(路径:行) |
|---|---|---|---|---|---|
| 1 | **`IActivityManager` 代理上的 `setServiceForeground`** | fd-droidify(+r16 已知同型) | `invoke interface method 'void android.app.IActivityManager.setServiceForeground(...)' on a null object reference` @ `Service.startForeground(Service.java:775)` ← coil3 `startForegroundSafe` ← SyncService | `setServiceForeground(ComponentName,IBinder,int,Notification,int,int)V` → **no-op**(前景服务无 OH 概念) | **ActivityManagerAdapter.java L460-466 已有**:`[STUB] setServiceForeground — OH has no foreground service concept`(route-A 的代理没把它暴露到 getInterface 的对象上——修代理装配,不是新桩) |
| 2 | **jobscheduler / WorkManager 路径(null→cast getClass)** | fd-feeder(+fd-calendar/wifianalyzer 同族) | `schedulePeriodicRssSync` lambda 里 `getClass() on a null`(WorkManager enqueue 内对 null service 的 cast) | `getSystemService(JOB_SCHEDULER_SERVICE)` 须返回可 cast 非 null 的 JobScheduler 实例 | **AppSpawnXInit.java L2058-2110 `installJobSchedulerStub()`**:反射换 SYSTEM_SERVICE_FETCHERS 条目,构造 `JobSchedulerImpl(ctx, noopBinder)`(L1086 调用)——**整段照抄**(fetcher 替换,不是服务代理) |
| 3 | **`PowerExemptionManager`** | fd-etar | `invoke virtual method 'boolean android.os.PowerExemptionManager.isAllow...(...)'` (thermalservice 已 real-routed,此管理器未跟) | `isApplicationExempted/isAllowLowerPowerProcess` 类查询 → **false** | 无同名类;同族语义在 **LocalServiceBinders.java L49+**(power case)——按 power proxy 模式给 powerexemption 加 case,默认 false |
| 4 | **`BatteryManager` / batterystats** | newpipe | `invoke 'int android.os.BatteryManager.getIntProperty(int)' on null`;前一行 `getService("batterystats") → null` | `getIntProperty(int)I` → **0**(BATTERY_PROPERTY_* 无数据语义);batterystats binder 给可 cast proxy | **LocalServiceBinders.java L49+ proxy 表加 battery/batterystats case**(power/thermalservice/alarm/clipboard/account/uimode 同模式,默认值=类型零值) |
| 5 | **vibrator_manager 族(数组 null)** | fd-reader | `get length of null array`;前一行 `getService("vibrator_manager") → adapter(real-routed)` 但后续 API 返回 null 数组 | 该 manager 的数组返回(vibratorIdList 等)→ **空数组非 null** | LocalServiceBinders 模式:**返回类型零值语义**(数组=空,newpipe 教训:绝不 null) |
| 6 | **PendingIntent.getBroadcast null** | fd-uhabits(与 noice@61b 回退同型,外环已注 PendingIntent null) | `getBroadcast(...) must not be null` @ `PendingIntentFactory.updateWidgets(:150)`(Kotlin 非空断言) | `PendingIntent.getBroadcast(...)` → **非 null PendingIntent 桩**(target=WrappedIntent 桩,send no-op) | Westlake:**WlShortcutService/PendingIntent 相关在 framework/appspawn-x/java/adapter/compat/**;getBroadcast 空桩返回 PendingIntent 子类实例(target 字段 null-safe),send 不做事——**非 null 是硬要求** |
| 7 | connectivity/network_management(已 stub→null,未致死首因但排雷) | fd-wifianalyzer 之前 3 行 null 服务:`network_management`/`connectivity`/`game` | 死因是 MainActivity.onCreate getClass-null(同 #2 jobscheduler 族);connectivity 族顺手补 | NetworkInfo/ConnectivityManager → 已有 WESTLAKE_CONNECTIVITY_HELPER 路线(#76 run.sh) | LocalServiceBinders connectivity case(basic NetworkInfo 默认值)+ AppSpawnXInit WESTLAKE_NET_HELPER_PATH env |

## 执行建议(cc-t3 r17c)

1. **先抄两段现成**:①ActivityManagerAdapter L460-466(修代理装配暴露)；②AppSpawnXInit L2058-2110 fetcher 替换——这两段解 droidify + feeder/calendar/wifianalyzer 4 个；
2. LocalServiceBinders 增 3 case:powerexemption(false)/battery+batterystats(0/可 cast)/vibrator_manager(空数组)——解 etar/newpipe/reader;
3. PendingIntent.getBroadcast 非 null 桩——解 uhabits(+noice@61b 同型回退);
4. 通用铁则(记入 gapfill 惯例):**空桩返回值=类型零值语义(0/false/空数组/非 null 对象),绝不 null**。
