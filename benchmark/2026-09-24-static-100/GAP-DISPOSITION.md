# 全量分组处置表（分析口径 v1）

`静态/硬` 是唯一 app 数。动态到达、首阻塞与阶段跃迁全部未测。工日按本行小契约估计，不能把各行相加；共享修复见 README。Java 分组不是规范 §12 的 canonical gap。

| ID | 静态/硬 | 队列 | 修复路径与证据要求 | 工日 | 风险 |
|---|---:|---|---|---|---|
| `java:App framework` | 100/59 | apk-dependency-candidate | 逐签名核对 API 版本和 SDK_INT 分支；移植已有 AOSP 实现，底层 ability_runtime 另做适配；C1/C4/C9 须重分，不能按分组首行推断。 | 3–10 | medium |
| `java:Java library` | 100/51 | apk-dependency-candidate | 逐签名核对 API 版本和 SDK_INT 分支；移植已有 AOSP 实现，底层 none (library code inside Westlake) 另做适配；C1/C4/C9 须重分，不能按分组首行推断。 | 3–10 | medium |
| `load:runtime-silent-success` | 100/100 | integrity | 核对 staged JNI 与内建注册表逐签名差集；验证 JNI_OnLoad/失败传播，不以每 app 复制行计 APK 缺口。 | 2–5 | medium |
| `java:Other` | 99/41 | apk-dependency-candidate | 逐签名核对 API 版本和 SDK_INT 分支；移植已有 AOSP 实现，底层 unmapped 另做适配；C1/C4/C9 须重分，不能按分组首行推断。 | 3–10 | medium |
| `java:Views & windows` | 99/72 | apk-dependency-candidate | 逐签名核对 API 版本和 SDK_INT 分支；移植已有 AOSP 实现，底层 window_manager / render_service 另做适配；C1/C4/C9 须重分，不能按分组首行推断。 | 3–10 | medium |
| `java:Content & intents` | 97/1 | apk-dependency-candidate | 逐签名核对 API 版本和 SDK_INT 分支；移植已有 AOSP 实现，底层 ability_runtime 另做适配；C1/C4/C9 须重分，不能按分组首行推断。 | 3–10 | medium |
| `java:Graphics` | 97/17 | apk-dependency-candidate | 逐签名核对 API 版本和 SDK_INT 分支；移植已有 AOSP 实现，底层 render_service / graphic_2d 另做适配；C1/C4/C9 须重分，不能按分组首行推断。 | 3–10 | medium |
| `java:Other Android` | 97/52 | apk-dependency-candidate | 逐签名核对 API 版本和 SDK_INT 分支；移植已有 AOSP 实现，底层 unmapped 另做适配；C1/C4/C9 须重分，不能按分组首行推断。 | 3–10 | medium |
| `pm:call:resolveContentProvider` | 97/97 | apk-dependency-candidate | 按 AOSP PackageManager 语义实现 resolveContentProvider；解析冻结 APK 的组件/IntentFilter/flags/权限，涉及其他包与 UID 时接 OH bundle 身份映射。 | 1–3 | medium |
| `pm:providers` | 97/0 | candidate | 核对 provider 安装次序、initOrder、authority 和 onCreate；unverified 不是 missing，先做契约探针。 | 1–2 | medium |
| `svc:accessibility` | 97/0 | candidate | 验证 AOSP manager 无服务降级路径；真无设备/能力则暴露真实 feature/异常；需要时接 unmapped，不可把 inert 自动当启动阻塞。 | 1–3 | medium |
| `java:Widgets` | 96/0 | candidate | 对照同 API 级 AOSP 逐成员检查：合法空回调不修；C8 需调用/反射/动态 DEX 证明；确认 C9 才移植。 | 1–3 | low |
| `svc:notification` | 96/96 | apk-dependency-candidate | 恢复 notification 的状态、回调、取消及错误语义；适配 notification (ANS)，用启动初始化与生命周期契约验证，不能返回默认成功。 | 3–7 | medium |
| `svc:audio` | 93/93 | apk-dependency-candidate | 恢复 audio 的状态、回调、取消及错误语义；适配 audio_framework，用启动初始化与生命周期契约验证，不能返回默认成功。 | 5–15 | medium |
| `pm:call:getPackagesForUid` | 92/92 | apk-dependency-candidate | 按 AOSP PackageManager 语义实现 getPackagesForUid；解析冻结 APK 的组件/IntentFilter/flags/权限，涉及其他包与 UID 时接 OH bundle 身份映射。 | 1–3 | medium |
| `pm:call:queryIntentActivityOptions` | 92/92 | apk-dependency-candidate | 按 AOSP PackageManager 语义实现 queryIntentActivityOptions；解析冻结 APK 的组件/IntentFilter/flags/权限，涉及其他包与 UID 时接 OH bundle 身份映射。 | 1–3 | medium |
| `pm:call:setComponentEnabledSetting` | 91/91 | apk-dependency-candidate | 按 AOSP PackageManager 语义实现 setComponentEnabledSetting；解析冻结 APK 的组件/IntentFilter/flags/权限，涉及其他包与 UID 时接 OH bundle 身份映射。 | 1–3 | medium |
| `pm:call:getComponentEnabledSetting` | 89/89 | apk-dependency-candidate | 按 AOSP PackageManager 语义实现 getComponentEnabledSetting；解析冻结 APK 的组件/IntentFilter/flags/权限，涉及其他包与 UID 时接 OH bundle 身份映射。 | 1–3 | medium |
| `pm:call:queryIntentContentProviders` | 88/88 | apk-dependency-candidate | 按 AOSP PackageManager 语义实现 queryIntentContentProviders；解析冻结 APK 的组件/IntentFilter/flags/权限，涉及其他包与 UID 时接 OH bundle 身份映射。 | 1–3 | medium |
| `svc:textclassification` | 86/86 | candidate | 沿 AOSP fetcher/helper 找到真实 Binder，验证 textclassification 的实际实现和启动调用，再选择适配；不把未知当缺失。 | 1–3 | low |
| `java:OS services` | 81/40 | apk-dependency-candidate | 逐签名核对 API 版本和 SDK_INT 分支；移植已有 AOSP 实现，底层 various system abilities 另做适配；C1/C4/C9 须重分，不能按分组首行推断。 | 3–10 | medium |
| `pm:call:queryIntentServices` | 81/81 | apk-dependency-candidate | 按 AOSP PackageManager 语义实现 queryIntentServices；解析冻结 APK 的组件/IntentFilter/flags/权限，涉及其他包与 UID 时接 OH bundle 身份映射。 | 1–3 | medium |
| `svc:jobscheduler` | 80/80 | apk-dependency-candidate | 恢复 jobscheduler 的状态、回调、取消及错误语义；适配 resourceschedule/work_scheduler，用启动初始化与生命周期契约验证，不能返回默认成功。 | 3–7 | medium |
| `svc:user` | 79/79 | apk-dependency-candidate | UserManager 的用户/解锁/限制查询返回当前宿主真实状态；保留权限与失败语义，消除 strict 代理无条件抛异常。 | 1–3 | low |
| `svc:vibrator` | 78/0 | apk-dependency-candidate | 提供 Android manager/失败语义并映射 sensors/miscdevice；逐设备确认能力/授权，不可由 OH 有对应子系统推断可用；缺硬件用真实 unavailable。 | 3–10 | medium |
| `pm:call:queryBroadcastReceivers` | 71/71 | apk-dependency-candidate | 按 AOSP PackageManager 语义实现 queryBroadcastReceivers；解析冻结 APK 的组件/IntentFilter/flags/权限，涉及其他包与 UID 时接 OH bundle 身份映射。 | 1–3 | medium |
| `svc:keyguard` | 68/68 | apk-dependency-candidate | 提供 Android manager/失败语义并映射 theme/screenlock；逐设备确认能力/授权，不可由 OH 有对应子系统推断可用；缺硬件用真实 unavailable。 | 3–10 | medium |
| `svc:phone` | 68/0 | apk-dependency-candidate | 提供 Android manager/失败语义并映射 telephony/core_service；逐设备确认能力/授权，不可由 OH 有对应子系统推断可用；缺硬件用真实 unavailable。 | 3–10 | medium |
| `wv:renderer-process` | 68/68 | apk-dependency-candidate | 保留 Android 进程/Provider/WebView 生命周期协议，接 OH appspawn、IPC、surface；远程进程和 renderer 不得用空代理伪装。 | 10–25 | high |
| `svc:autofill` | 67/0 | candidate | 验证 AOSP manager 无服务降级路径；真无设备/能力则暴露真实 feature/异常；需要时接 unmapped，不可把 inert 自动当启动阻塞。 | 1–3 | medium |
| `svc:sensor` | 67/0 | apk-dependency-candidate | 提供 Android manager/失败语义并映射 sensors；逐设备确认能力/授权，不可由 OH 有对应子系统推断可用；缺硬件用真实 unavailable。 | 3–10 | medium |
| `svc:wifi` | 63/63 | apk-dependency-candidate | 提供 Android manager/失败语义并映射 communication/wifi；逐设备确认能力/授权，不可由 OH 有对应子系统推断可用；缺硬件用真实 unavailable。 | 3–10 | medium |
| `java:Networking` | 60/7 | apk-dependency-candidate | 逐签名核对 API 版本和 SDK_INT 分支；移植已有 AOSP 实现，底层 netmanager 另做适配；C1/C4/C9 须重分，不能按分组首行推断。 | 3–10 | medium |
| `pm:call:resolveService` | 60/60 | apk-dependency-candidate | 按 AOSP PackageManager 语义实现 resolveService；解析冻结 APK 的组件/IntentFilter/flags/权限，涉及其他包与 UID 时接 OH bundle 身份映射。 | 1–3 | medium |
| `java:WebView` | 59/0 | candidate | 对照同 API 级 AOSP 逐成员检查：合法空回调不修；C8 需调用/反射/动态 DEX 证明；确认 C9 才移植。 | 1–3 | low |
| `policy:lnk_file` | 58/58 | apk-dependency-candidate | 依据实际对象操作和设备策略重验；由 OH 系统侧决定沙箱内支持，或暴露真实 errno/unsupported；不得放宽全局策略或伪造成功。 | 5–15 | high |
| `java:Java extensions` | 56/48 | apk-dependency-candidate | 逐签名核对 API 版本和 SDK_INT 分支；移植已有 AOSP 实现，底层 none (library code inside Westlake) 另做适配；C1/C4/C9 须重分，不能按分组首行推断。 | 3–10 | medium |
| `java:Media store` | 56/15 | apk-dependency-candidate | 逐签名核对 API 版本和 SDK_INT 分支；移植已有 AOSP 实现，底层 multimedia/media_library 另做适配；C1/C4/C9 须重分，不能按分组首行推断。 | 3–10 | medium |
| `pm:call:getInstallerPackageName` | 54/54 | apk-dependency-candidate | 按 AOSP PackageManager 语义实现 getInstallerPackageName；解析冻结 APK 的组件/IntentFilter/flags/权限，涉及其他包与 UID 时接 OH bundle 身份映射。 | 1–3 | medium |
| `sym:bionic-private (not in the NDK)` | 51/51 | apk-dependency-candidate | 按每个 symbol 拆 C1 转发、C2 布局/常量翻译、C4 NDK 后端；当前没有 Android NDK 声明索引，bionic-private 标签不可信。 | 5–20 | high |
| `svc:camera` | 49/0 | apk-dependency-candidate | 提供 Android manager/失败语义并映射 multimedia/camera_framework；逐设备确认能力/授权，不可由 OH 有对应子系统推断可用；缺硬件用真实 unavailable。 | 3–10 | medium |
| `svc:captioning` | 48/48 | candidate | 沿 AOSP fetcher/helper 找到真实 Binder，验证 captioning 的实际实现和启动调用，再选择适配；不把未知当缺失。 | 1–3 | low |
| `svc:media_metrics` | 46/46 | apk-dependency-candidate | 按 media_metrics 的 AOSP 契约确认能力和权限；可用则接 unmapped，不可用则返回规定的 unsupported/feature 状态，证明调用方降级。 | 1–5 | medium |
| `java:Media` | 45/13 | apk-dependency-candidate | 逐签名核对 API 版本和 SDK_INT 分支；移植已有 AOSP 实现，底层 multimedia 另做适配；C1/C4/C9 须重分，不能按分组首行推断。 | 3–10 | medium |
| `pm:call:getInstallSourceInfo` | 45/45 | apk-dependency-candidate | 按 AOSP PackageManager 语义实现 getInstallSourceInfo；解析冻结 APK 的组件/IntentFilter/flags/权限，涉及其他包与 UID 时接 OH bundle 身份映射。 | 1–3 | medium |
| `svc:download` | 45/0 | apk-dependency-candidate | 提供 Android manager/失败语义并映射 miscservices/download_server；逐设备确认能力/授权，不可由 OH 有对应子系统推断可用；缺硬件用真实 unavailable。 | 3–10 | medium |
| `pm:call:getNameForUid` | 43/43 | apk-dependency-candidate | 按 AOSP PackageManager 语义实现 getNameForUid；解析冻结 APK 的组件/IntentFilter/flags/权限，涉及其他包与 UID 时接 OH bundle 身份映射。 | 1–3 | medium |
| `dep:google-play-services` | 42/42 | apk-dependency-candidate | Google 专有服务不由 AOSP 提供：保留不可用信号；push/maps 等另审 OH 后端适配，不能承诺 Google 登录、授权或服务端校验通过。 | 1–3 | medium |
| `pm:multiprocess` | 42/42 | apk-dependency-candidate | 保留 Android 进程/Provider/WebView 生命周期协议，接 OH appspawn、IPC、surface；远程进程和 renderer 不得用空代理伪装。 | 10–25 | high |
| `svc:biometric` | 41/41 | apk-dependency-candidate | 提供 Android manager/失败语义并映射 unmapped；逐设备确认能力/授权，不可由 OH 有对应子系统推断可用；缺硬件用真实 unavailable。 | 3–10 | medium |
| `java:Camera` | 40/0 | candidate | 对照同 API 级 AOSP 逐成员检查：合法空回调不修；C8 需调用/反射/动态 DEX 证明；确认 C9 才移植。 | 1–3 | low |
| `svc:fingerprint` | 39/39 | apk-dependency-candidate | 提供 Android manager/失败语义并映射 unmapped；逐设备确认能力/授权，不可由 OH 有对应子系统推断可用；缺硬件用真实 unavailable。 | 3–10 | medium |
| `dep:firebase-component-discovery:ComponentDiscoveryService` | 38/0 | candidate | Google 专有服务不由 AOSP 提供：保留不可用信号；push/maps 等另审 OH 后端适配，不能承诺 Google 登录、授权或服务端校验通过。 | 1–3 | medium |
| `svc:bluetooth` | 34/34 | candidate | 沿 AOSP fetcher/helper 找到真实 Binder，验证 bluetooth 的实际实现和启动调用，再选择适配；不把未知当缺失。 | 1–3 | low |
| `pm:call:getSystemAvailableFeatures` | 33/33 | apk-dependency-candidate | 按 AOSP PackageManager 语义实现 getSystemAvailableFeatures；解析冻结 APK 的组件/IntentFilter/flags/权限，涉及其他包与 UID 时接 OH bundle 身份映射。 | 1–3 | medium |
| `pm:call:getReceiverInfo` | 32/32 | apk-dependency-candidate | 按 AOSP PackageManager 语义实现 getReceiverInfo；解析冻结 APK 的组件/IntentFilter/flags/权限，涉及其他包与 UID 时接 OH bundle 身份映射。 | 1–3 | medium |
| `load:shadowed-by-board` | 31/31 | apk-dependency-candidate | 按依赖和 SONAME 建立 app namespace、装载次序及 JNI 注册所有权；复用 AOSP linker 语义；禁止全局抢符号和假成功。 | 2–5 | high |
| `svc:credential` | 31/0 | candidate | 验证 AOSP manager 无服务降级路径；真无设备/能力则暴露真实 feature/异常；需要时接 unmapped，不可把 inert 自动当启动阻塞。 | 1–3 | medium |
| `svc:vibrator_manager` | 30/30 | candidate | 沿 AOSP fetcher/helper 找到真实 Binder，验证 vibrator_manager 的实际实现和启动调用，再选择适配；不把未知当缺失。 | 1–3 | low |
| `svc:print` | 29/29 | candidate | 沿 AOSP fetcher/helper 找到真实 Binder，验证 print 的实际实现和启动调用，再选择适配；不把未知当缺失。 | 1–3 | low |
| `java:Job scheduling` | 26/0 | candidate | 对照同 API 级 AOSP 逐成员检查：合法空回调不修；C8 需调用/反射/动态 DEX 证明；确认 C9 才移植。 | 1–3 | low |
| `svc:storagestats` | 26/26 | apk-dependency-candidate | 按 storagestats 的 AOSP 契约确认能力和权限；可用则接 unmapped，不可用则返回规定的 unsupported/feature 状态，证明调用方降级。 | 1–5 | medium |
| `dep:firebase-component-discovery:MlKitComponentDiscoveryService` | 23/0 | candidate | Google 专有服务不由 AOSP 提供：保留不可用信号；push/maps 等另审 OH 后端适配，不能承诺 Google 登录、授权或服务端校验通过。 | 1–3 | medium |
| `svc:usagestats` | 22/22 | apk-dependency-candidate | 提供 Android manager/失败语义并映射 resourceschedule/device_usage_statistics；逐设备确认能力/授权，不可由 OH 有对应子系统推断可用；缺硬件用真实 unavailable。 | 3–10 | medium |
| `java:Utilities` | 21/3 | apk-dependency-candidate | 逐签名核对 API 版本和 SDK_INT 分支；移植已有 AOSP 实现，底层 none (library code inside Westlake) 另做适配；C1/C4/C9 须重分，不能按分组首行推断。 | 3–10 | medium |
| `svc:device_policy` | 21/21 | apk-dependency-candidate | 按 device_policy 的 AOSP 契约确认能力和权限；可用则接 unmapped，不可用则返回规定的 unsupported/feature 状态，证明调用方降级。 | 1–5 | medium |
| `svc:media_projection` | 21/0 | candidate | 验证 AOSP manager 无服务降级路径；真无设备/能力则暴露真实 feature/异常；需要时接 unmapped，不可把 inert 自动当启动阻塞。 | 1–3 | medium |
| `svc:servicediscovery` | 20/20 | apk-dependency-candidate | 提供 Android manager/失败语义并映射 unmapped；逐设备确认能力/授权，不可由 OH 有对应子系统推断可用；缺硬件用真实 unavailable。 | 3–10 | medium |
| `pm:call:getInstalledApplications` | 19/19 | apk-dependency-candidate | 按 AOSP PackageManager 语义实现 getInstalledApplications；解析冻结 APK 的组件/IntentFilter/flags/权限，涉及其他包与 UID 时接 OH bundle 身份映射。 | 1–3 | medium |
| `svc:telecom` | 19/0 | candidate | 验证 AOSP manager 无服务降级路径；真无设备/能力则暴露真实 feature/异常；需要时接 unmapped，不可把 inert 自动当启动阻塞。 | 1–3 | medium |
| `svc:media_session` | 17/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:telephony_subscription_service` | 17/17 | candidate | 沿 AOSP fetcher/helper 找到真实 Binder，验证 telephony_subscription_service 的实际实现和启动调用，再选择适配；不把未知当缺失。 | 1–3 | low |
| `svc:usb` | 17/17 | apk-dependency-candidate | 提供 Android manager/失败语义并映射 usb_manager；逐设备确认能力/授权，不可由 OH 有对应子系统推断可用；缺硬件用真实 unavailable。 | 3–10 | medium |
| `java:Location` | 16/0 | candidate | 对照同 API 级 AOSP 逐成员检查：合法空回调不修；C8 需调用/反射/动态 DEX 证明；确认 C9 才移植。 | 1–3 | low |
| `java:Telephony` | 16/6 | apk-dependency-candidate | 逐签名核对 API 版本和 SDK_INT 分支；移植已有 AOSP 实现，底层 telephony 另做适配；C1/C4/C9 须重分，不能按分组首行推断。 | 3–10 | medium |
| `pm:call:checkSignatures` | 15/15 | apk-dependency-candidate | 按 AOSP PackageManager 语义实现 checkSignatures；解析冻结 APK 的组件/IntentFilter/flags/权限，涉及其他包与 UID 时接 OH bundle 身份映射。 | 1–3 | medium |
| `pm:call:getApplicationEnabledSetting` | 15/15 | apk-dependency-candidate | 按 AOSP PackageManager 语义实现 getApplicationEnabledSetting；解析冻结 APK 的组件/IntentFilter/flags/权限，涉及其他包与 UID 时接 OH bundle 身份映射。 | 1–3 | medium |
| `svc:grammatical_inflection` | 15/15 | apk-dependency-candidate | 按 grammatical_inflection 的 AOSP 契约确认能力和权限；可用则接 unmapped，不可用则返回规定的 unsupported/feature 状态，证明调用方降级。 | 1–5 | medium |
| `svc:input` | 15/15 | candidate | 沿 AOSP fetcher/helper 找到真实 Binder，验证 input 的实际实现和启动调用，再选择适配；不把未知当缺失。 | 1–3 | low |
| `svc:search` | 15/15 | apk-dependency-candidate | 按 search 的 AOSP 契约确认能力和权限；可用则接 unmapped，不可用则返回规定的 unsupported/feature 状态，证明调用方降级。 | 1–5 | medium |
| `java:Bluetooth` | 14/0 | candidate | 对照同 API 级 AOSP 逐成员检查：合法空回调不修；C8 需调用/反射/动态 DEX 证明；确认 C9 才移植。 | 1–3 | low |
| `svc:appwidget` | 12/0 | candidate | 验证 AOSP manager 无服务降级路径；真无设备/能力则暴露真实 feature/异常；需要时接 unmapped，不可把 inert 自动当启动阻塞。 | 1–3 | medium |
| `svc:wifip2p` | 12/12 | apk-dependency-candidate | 提供 Android manager/失败语义并映射 communication/wifi (p2p)；逐设备确认能力/授权，不可由 OH 有对应子系统推断可用；缺硬件用真实 unavailable。 | 3–10 | medium |
| `java:Legacy HTTP` | 11/8 | apk-dependency-candidate | 逐签名核对 API 版本和 SDK_INT 分支；移植已有 AOSP 实现，底层 none (library code inside Westlake) 另做适配；C1/C4/C9 须重分，不能按分组首行推断。 | 3–10 | medium |
| `policy:fifo_file` | 11/11 | apk-dependency-candidate | 依据实际对象操作和设备策略重验；由 OH 系统侧决定沙箱内支持，或暴露真实 errno/unsupported；不得放宽全局策略或伪造成功。 | 5–15 | high |
| `svc:dropbox` | 11/11 | apk-dependency-candidate | 按 dropbox 的 AOSP 契约确认能力和权限；可用则接 unmapped，不可用则返回规定的 unsupported/feature 状态，证明调用方降级。 | 1–5 | medium |
| `svc:media_router` | 10/0 | candidate | 验证 AOSP manager 无服务降级路径；真无设备/能力则暴露真实 feature/异常；需要时接 unmapped，不可把 inert 自动当启动阻塞。 | 1–3 | medium |
| `svc:netstats` | 10/10 | apk-dependency-candidate | 按 netstats 的 AOSP 契约确认能力和权限；可用则接 unmapped，不可用则返回规定的 unsupported/feature 状态，证明调用方降级。 | 1–5 | medium |
| `java:Keystore & security` | 9/4 | apk-dependency-candidate | 逐签名核对 API 版本和 SDK_INT 分支；移植已有 AOSP 实现，底层 security 另做适配；C1/C4/C9 须重分，不能按分组首行推断。 | 3–10 | medium |
| `java:Text` | 9/1 | apk-dependency-candidate | 逐签名核对 API 版本和 SDK_INT 分支；移植已有 AOSP 实现，底层 none (library code inside Westlake) 另做适配；C1/C4/C9 须重分，不能按分组首行推断。 | 3–10 | medium |
| `svc:restrictions` | 9/9 | apk-dependency-candidate | 按 restrictions 的 AOSP 契约确认能力和权限；可用则接 unmapped，不可用则返回规定的 unsupported/feature 状态，证明调用方降级。 | 1–5 | medium |
| `pm:call:isSafeMode` | 8/8 | apk-dependency-candidate | 按 AOSP PackageManager 语义实现 isSafeMode；解析冻结 APK 的组件/IntentFilter/flags/权限，涉及其他包与 UID 时接 OH bundle 身份映射。 | 1–3 | medium |
| `svc:systemhealth` | 8/0 | apk-dependency-candidate | 按 systemhealth 的 AOSP 契约确认能力和权限；可用则接 unmapped，不可用则返回规定的 unsupported/feature 状态，证明调用方降级。 | 1–5 | medium |
| `svc:textservices` | 8/8 | apk-dependency-candidate | 按 textservices 的 AOSP 契约确认能力和权限；可用则接 unmapped，不可用则返回规定的 unsupported/feature 状态，证明调用方降级。 | 1–5 | medium |
| `java:Package manager` | 7/1 | apk-dependency-candidate | 逐签名核对 API 版本和 SDK_INT 分支；移植已有 AOSP 实现，底层 bundle_framework 另做适配；C1/C4/C9 须重分，不能按分组首行推断。 | 3–10 | medium |
| `pm:call:getSystemSharedLibraryNames` | 7/7 | apk-dependency-candidate | 按 AOSP PackageManager 语义实现 getSystemSharedLibraryNames；解析冻结 APK 的组件/IntentFilter/flags/权限，涉及其他包与 UID 时接 OH bundle 身份映射。 | 1–3 | medium |
| `java:Hardware` | 6/2 | apk-dependency-candidate | 逐签名核对 API 版本和 SDK_INT 分支；移植已有 AOSP 实现，底层 drivers / sensors 另做适配；C1/C4/C9 须重分，不能按分组首行推断。 | 3–10 | medium |
| `java:WiFi` | 6/0 | candidate | 对照同 API 级 AOSP 逐成员检查：合法空回调不修；C8 需调用/反射/动态 DEX 证明；确认 C9 才移植。 | 1–3 | low |
| `svc:performance_hint` | 6/6 | candidate | 沿 AOSP fetcher/helper 找到真实 Binder，验证 performance_hint 的实际实现和启动调用，再选择适配；不把未知当缺失。 | 1–3 | low |
| `svc:profiling` | 6/6 | candidate | 沿 AOSP fetcher/helper 找到真实 Binder，验证 profiling 的实际实现和启动调用，再选择适配；不把未知当缺失。 | 1–3 | low |
| `java:Privacy Sandbox` | 5/0 | candidate | 对照同 API 级 AOSP 逐成员检查：合法空回调不修；C8 需调用/反射/动态 DEX 证明；确认 C9 才移植。 | 1–3 | low |
| `svc:domain_verification` | 5/5 | apk-dependency-candidate | 按 domain_verification 的 AOSP 契约确认能力和权限；可用则接 unmapped，不可用则返回规定的 unsupported/feature 状态，证明调用方降级。 | 1–5 | medium |
| `svc:nfc` | 5/5 | candidate | 沿 AOSP fetcher/helper 找到真实 Binder，验证 nfc 的实际实现和启动调用，再选择适配；不把未知当缺失。 | 1–3 | low |
| `pm:call:getPackageGids` | 4/4 | apk-dependency-candidate | 按 AOSP PackageManager 语义实现 getPackageGids；解析冻结 APK 的组件/IntentFilter/flags/权限，涉及其他包与 UID 时接 OH bundle 身份映射。 | 1–3 | medium |
| `svc:statusbar` | 4/0 | candidate | 验证 AOSP manager 无服务降级路径；真无设备/能力则暴露真实 feature/异常；需要时接 unmapped，不可把 inert 自动当启动阻塞。 | 1–3 | medium |
| `pm:call:setComponentEnabledSettings` | 3/3 | apk-dependency-candidate | 按 AOSP PackageManager 语义实现 setComponentEnabledSettings；解析冻结 APK 的组件/IntentFilter/flags/权限，涉及其他包与 UID 时接 OH bundle 身份映射。 | 1–3 | medium |
| `svc:MiuiWifiService` | 3/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:content_capture` | 3/0 | candidate | 验证 AOSP manager 无服务降级路径；真无设备/能力则暴露真实 feature/异常；需要时接 none，不可把 inert 自动当启动阻塞。 | 1–3 | medium |
| `svc:midi` | 3/3 | apk-dependency-candidate | 按 midi 的 AOSP 契约确认能力和权限；可用则接 unmapped，不可用则返回规定的 unsupported/feature 状态，证明调用方降级。 | 1–5 | medium |
| `svc:permission_controller` | 3/3 | candidate | 沿 AOSP fetcher/helper 找到真实 Binder，验证 permission_controller 的实际实现和启动调用，再选择适配；不把未知当缺失。 | 1–3 | low |
| `svc:role` | 3/3 | apk-dependency-candidate | 按 role 的 AOSP 契约确认能力和权限；可用则接 unmapped，不可用则返回规定的 unsupported/feature 状态，证明调用方降级。 | 1–5 | medium |
| `svc:security` | 3/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `env:forter-fraud-sdk` | 2/0 | candidate | 比较 Android 正常基线，保留完整性/设备能力真实结果；SDK 被拒载后的降级与服务端接受度需实测，不伪造认证。 | 1–3 | high |
| `java:Providers & settings` | 2/1 | apk-dependency-candidate | 逐签名核对 API 版本和 SDK_INT 分支；移植已有 AOSP 实现，底层 various 另做适配；C1/C4/C9 须重分，不能按分组首行推断。 | 3–10 | medium |
| `pm:call:getPackagesHoldingPermissions` | 2/2 | apk-dependency-candidate | 按 AOSP PackageManager 语义实现 getPackagesHoldingPermissions；解析冻结 APK 的组件/IntentFilter/flags/权限，涉及其他包与 UID 时接 OH bundle 身份映射。 | 1–3 | medium |
| `pm:call:getTargetSdkVersion` | 2/2 | apk-dependency-candidate | 按 AOSP PackageManager 语义实现 getTargetSdkVersion；解析冻结 APK 的组件/IntentFilter/flags/权限，涉及其他包与 UID 时接 OH bundle 身份映射。 | 1–3 | medium |
| `pm:call:setApplicationEnabledSetting` | 2/2 | apk-dependency-candidate | 按 AOSP PackageManager 语义实现 setApplicationEnabledSetting；解析冻结 APK 的组件/IntentFilter/flags/权限，涉及其他包与 UID 时接 OH bundle 身份映射。 | 1–3 | medium |
| `svc:blob_store` | 2/2 | apk-dependency-candidate | 按 blob_store 的 AOSP 契约确认能力和权限；可用则接 unmapped，不可用则返回规定的 unsupported/feature 状态，证明调用方降级。 | 1–5 | medium |
| `svc:consumer_ir` | 2/2 | apk-dependency-candidate | 按 consumer_ir 的 AOSP 契约确认能力和权限；可用则接 unmapped，不可用则返回规定的 unsupported/feature 状态，证明调用方降级。 | 1–5 | medium |
| `svc:desktopmode` | 2/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:euicc` | 2/2 | candidate | 沿 AOSP fetcher/helper 找到真实 Binder，验证 euicc 的实际实现和启动调用，再选择适配；不把未知当缺失。 | 1–3 | low |
| `svc:metric_sdk_server` | 2/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:perfsdkservice` | 2/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `env:akamai-bot-manager` | 1/0 | candidate | 比较 Android 正常基线，保留完整性/设备能力真实结果；SDK 被拒载后的降级与服务端接受度需实测，不伪造认证。 | 1–3 | high |
| `java:Biometrics` | 1/0 | candidate | 对照同 API 级 AOSP 逐成员检查：合法空回调不修；C8 需调用/反射/动态 DEX 证明；确认 C9 才移植。 | 1–3 | low |
| `java:Network service discovery (mDNS)` | 1/1 | apk-dependency-candidate | 逐签名核对 API 版本和 SDK_INT 分支；移植已有 AOSP 实现，底层 netmanager/mdns 另做适配；C1/C4/C9 须重分，不能按分组首行推断。 | 3–10 | medium |
| `pm:call:clearPackagePreferredActivities` | 1/1 | apk-dependency-candidate | 按 AOSP PackageManager 语义实现 clearPackagePreferredActivities；解析冻结 APK 的组件/IntentFilter/flags/权限，涉及其他包与 UID 时接 OH bundle 身份映射。 | 1–3 | medium |
| `pm:call:getPreferredActivities` | 1/1 | apk-dependency-candidate | 按 AOSP PackageManager 语义实现 getPreferredActivities；解析冻结 APK 的组件/IntentFilter/flags/权限，涉及其他包与 UID 时接 OH bundle 身份映射。 | 1–3 | medium |
| `svc:: ` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:MicroMsg.FtsWebVideoView` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:Perfs.init() called with a non Application context: ` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:android.bluetooth.profile.extra.STATE` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:app_search` | 1/1 | apk-dependency-candidate | 按 app_search 的 AOSP 契约确认能力和权限；可用则接 unmapped，不可用则返回规定的 unsupported/feature 状态，证明调用方降级。 | 1–5 | medium |
| `svc:authentication_service` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:batteryinfo` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:carrier_config` | 1/1 | candidate | 沿 AOSP fetcher/helper 找到真实 Binder，验证 carrier_config 的实际实现和启动调用，再选择适配；不把未知当缺失。 | 1–3 | low |
| `svc:com.amazon.client.metrics.api` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:com.ubercab.uview.core.injection.UViewInjection$Loggers` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:com.ubercab.uview.core.injection.UViewInjection$Parameters` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:com.ubercab.uview.core.injection.UViewInjection$UberComposeInjectable` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:companiondevice` | 1/1 | apk-dependency-candidate | 按 companiondevice 的 AOSP 契约确认能力和权限；可用则接 unmapped，不可用则返回规定的 unsupported/feature 状态，证明调用方降级。 | 1–5 | medium |
| `svc:crossprofileapps` | 1/1 | apk-dependency-candidate | 按 crossprofileapps 的 AOSP 契约确认能力和权限；可用则接 unmapped，不可用则返回规定的 unsupported/feature 状态，证明调用方降级。 | 1–5 | medium |
| `svc:dcp_account_manager` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:dcp_amazon_account_man` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:dcp_authenticated_url_connection_factory` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:dcp_data_storage_factory` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:dcp_device_info` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:dcp_system` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:dcp_token_cache_holder` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:dcp_token_mangement` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:enterprise_policy` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:game` | 1/1 | apk-dependency-candidate | 按 game 的 AOSP 契约确认能力和权限；可用则接 none，不可用则返回规定的 unsupported/feature 状态，证明调用方降级。 | 1–5 | medium |
| `svc:getRealBottomHeight, get NULL windowManager` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:hardware_properties` | 1/1 | apk-dependency-candidate | 按 hardware_properties 的 AOSP 契约确认能力和权限；可用则接 unmapped，不可用则返回规定的 unsupported/feature 状态，证明调用方降级。 | 1–5 | medium |
| `svc:healthconnect` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:launcherapps` | 1/0 | candidate | 验证 AOSP manager 无服务降级路径；真无设备/能力则暴露真实 feature/异常；需要时接 unmapped，不可把 inert 自动当启动阻塞。 | 1–3 | medium |
| `svc:mtk-perfservice` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:popToActivity fail` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:scene` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:sms` | 1/1 | candidate | 沿 AOSP fetcher/helper 找到真实 Binder，验证 sms 的实际实现和启动调用，再选择适配；不把未知当缺失。 | 1–3 | low |
| `svc:sso_alarm_maanger` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:sso_local_datastorage` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:sso_map_account_manager_communicator` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:sso_platform` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:sso_webservice_caller_creator` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:t6c.b` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:tencent_identifier` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:value: %s` | 1/0 | observation | 复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。 | 0.5–2 | low |
| `svc:virtualdevice` | 1/1 | apk-dependency-candidate | 按 virtualdevice 的 AOSP 契约确认能力和权限；可用则接 unmapped，不可用则返回规定的 unsupported/feature 状态，证明调用方降级。 | 1–5 | medium |
| `svc:wallpaper` | 1/0 | apk-dependency-candidate | 按 wallpaper 的 AOSP 契约确认能力和权限；可用则接 miscservices/wallpaper，不可用则返回规定的 unsupported/feature 状态，证明调用方降级。 | 1–5 | medium |
