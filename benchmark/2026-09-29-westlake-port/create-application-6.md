# r17a 排名⑩「走深族」Unable-to-create-application 6 个 —— 逐 app 定因(30 分钟限时)

证据:r17a hilog 一手(最深 Caused by,穿透 Koin/包装层)。**重要塌缩:6 个里 2 个(k9/fd-android)同根于 null-service 桩表已覆盖的 AlarmManager 族;x@61b 根本不是 create-application(是 activity 实例化)。实际新缺口只有 3 类。**

## 逐 app

| app | 最深根因(一手原文) | 归类 | 修法/并入 |
|---|---|---|---|
| **fd-k9@5cd** | Koin 7 层链穿透到底:`NullPointerException getClass() on null` @ `com.fsck.k9.backends.AndroidAlarmManager.<init>` | **缺系统服务(AlarmManager null-cast)** | **并入桩表 #2 族**:AppSpawnXInit L2058-2110 fetcher 替换语义——alarm 也要 LocalServiceBinders case(L61-64 已有 alarm!)确认 fetcher 路径覆盖 getSystemService(ALARM_SERVICE) 的类查找。#75 r16 同款(k9 当时也死这) |
| **fd-android@5cd**(Thunderbird) | 与 k9 完全同栈:同一 `AndroidAlarmManager.<init>` getClass-null(同一代码库) | **同上,一段修救 2 个** | 同上 |
| **fd-libretube@5cd** | `IllegalArgumentException: size must be > 0.`(createApplication 直下) | **其它:构造参数 0**(媒体/ExoPlayer 缓冲 size 类构造,疑 DisplayInfo 或 AudioAttributes 数组为 0) | 需上板定位是哪个构造的 0 源(30min 内静态不可判);嫌疑=display metrics 0(#91 vis=0 族的 relayout r4 缺失会给 0 尺寸)→ r4 修完免费复测 |
| **fd-musicplayer@61b** | `IllegalArgumentException: Failed to resolve SessionToken for ComponentInfo{org.fossify.musicplayer/...MediaSessionService}` | **缺系统服务:MediaSessionService 解析** | Westlake 有整件:**framework/hwui-shim 同目录 `adapter/compat/WlMediaSession.java`**(MediaSession 桥)+ OhServiceManager media.session 路由;照 LocalServiceBinders 模式给 "media_session" 一个可解析 service/token(返回非 null SessionToken 桩) |
| **fd-tasks@61b** | `java.security.KeyStoreException: AndroidKeyStore not found` | **缺 JCA Provider(AndroidKeyStore)** | Westlake 对应:**framework/appspawn-x/java/adapter/security/OhTrustBridge.java**(install 时 `Security.getProvider("BC")` 基础上补注册;L31 起)——加 "AndroidKeyStore" KeyStore 条目(`provider.put("KeyStore.AndroidKeyStore", <桩类>)`),load/store 返回空 KeyStore(类型正确非 null) |
| **x@61b**(twitter) | 实为 `Unable to instantiate activity`(非 create-application;auto_triage 归桶误差) | **Dagger/对象图**(外环 r17a 前判 x=application graph not defined 同族) | #82 段 10 appClassName 投影核查 + Activity 实例化走 AppComponentFactory(需 factory 链路)——cc-t3 核 r13 的 appComponentFactory 投影 |

## 归并结论

- **并入既有表/gapfill**:k9+fd-android → null-service 桩表 #2 族(AlarmManager fetcher;一段修共救 4+:feeder/calendar/wifianalyzer/k9/fd-android)
- **新桩 2 件**(LocalServiceBinders/OhTrustBridge 模式):MediaSession token(音乐类通用)、AndroidKeyStore KeyStore 条目(加密类 app 通用)
- **复测型 1 件**:libretube(size>0 疑 relayout r4 尺寸 0 的下游,先修 r4)
- **归档修正 1 件**:x@61b 不是 create-application 族(分诊规则加 "Unable to instantiate activity" 单列)
