# Harness API 实现与验证全景

更新：2026-10-13（R6一行增量；基础图为2026-10-12）。离线汇总现有证据；本轮没有新增板测。

共 **315 个知识条目**（含冻结索引、支撑工具与交叉引用，不能相加当作独立 API 数）；覆盖 **8 个冻结条目**。其中 API 能力记录 293 条，冻结索引 8 条，支撑知识 14 条。

[CSV 表格](api-progress.csv) · [JSON 底表](api-progress.json) · [来源与覆盖范围](source-coverage.json) · [历史 NDK 符号明细](ndk-symbols-historical.csv) · [历史 JNI 占位声明](jni-stub-declarations-historical.csv)

## 怎样读这张表

- **已实现**描述列出的能力，仍须看方法与限制；**部分实现**有受限路径；**占位/降级**提供默认值或关闭能力；**缺口**尚未满足。
- `reported` 是引用历史报告；`static` 是静态存在；`unit` 是离线测试；`wall_shift` 只证明该 API 墙消失；`t20_ui` 是指定运行的首屏；`functional` 才是指定功能操作。它们不能互相替代。
- Android 源码版本、API level、APK targetSdk、Android 对照机版本分开；OH 版本只写记录能证明的范围。`unknown` 表示缺证据，不能解释成通用支持。
- 冻结是满足仓库既定多 APK 证据门槛的实现登记，不代表整个 Android 子系统完整。历史版本、候选件、现态证据也分别保留。
- 范围是仓库中已记录的能力与缺口；NDK 明细覆盖历史 API 33 符号全集，Java/JNI 能力表并非整个 Android SDK 的穷举。

## 版本证据地图

| 版本类型 | 已知版本 | 有效范围与限制 | 来源 |
|---|---|---|---|
| 实际 OH 运行环境 | OpenHarmony 6.1.0.31 | 2026-10-10 的 5cd U13 回归环境，identity 记录 319 路径一致；不把该平台证据自动套到每项早期 API 实验。 | [identity.json](<../../../../westlake-harness/benchmark/2026-10-10-5cd-demo-regression/pre-lock-identity/identity.json>) |
| 历史 OH 功能验证 | OpenHarmony 7.0.0.38 / aarch64 / Enforcing | 历史 dedicated HelloWorld org.a2hlab.baseline.helloworld：JNI 自检页面及点击变色；来自 09-28 本地证据复核报告。本表没有在 OH 7 重验整个 API 集。Release/Beta 与产物哈希不能混用。 | [architecture-platform.md](<../../../../westlake-harness/benchmark/2026-09-28-bms-route-study/evidence/architecture-platform.md>) |
| Android 源码基线 | AOSP android-14.0.0_r1 | 例如 FZ-007 完整 TagSoup 源码，和 FZ-005 dex2oat toolchain；源码来源不是支持 Android 14 全部 API 的承诺。 | [frozen.json](<../../../../westlake-harness/knowledge/frozen/frozen.json>) |
| NDK 静态接口基准 | NDK r25 / API 33 | 09-21 两套产物的 4,449 符号、25 库静态清单；导出存在不等于功能实测，缺失也不是当前统一态的缺口数。 | [README.md](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/README.md>) |
| Android 对照来源 | Android 11 arm64 | 头条/麦当劳 native import 对照的 17 系统库、12,152 导出，仅符号比对；不是 OH 上每个 API 的功能成功证据。 | [AOSP-PACKAGING-STRATEGY.md](<../../../../westlake-harness/analysis/AOSP-PACKAGING-STRATEGY.md>) |

## 概览

| 实现状态 | 知识条目数 |
|---|---:|
| 已实现 | 54 |
| 部分实现 | 84 |
| 占位/降级 | 110 |
| 缺口 | 40 |
| 未知 | 27 |

API 能力记录中的未补证字段（不含冻结索引与支撑工具）：

| 字段 | unknown 条目数 |
|---|---:|
| Android 源码版本 | 208 |
| Android API level | 255 |
| APK targetSdk | 293 |
| Android 实测版本 | 293 |
| OH 实测版本 | 291 |
| 源码 / 产物定位 | 89 |

## 按能力浏览

| ID / 能力 | 状态 / 冻结 | 实现方法 | Android 来源 / OH 实测 | APK 证据（严格按原级别） | 限制 |
|---|---|---|---|---|---|
| [JAVA-001](#java-001) T7-tagsoup | 部分实现 / historical | Four recognized property constants and Object backing fields; unknown property throws SAXNotRecognizedException；限制：Not a full TagSoup implementation; does not implement general HTML parse/setContentHandler/setFeature | unknown / OH: unknown / 路由与代际: T7c | 无直接 APK 验证记录 | Not a full TagSoup implementation; does not implement general HTML parse/setContentHandler/setFeature; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推; T7c旧TagSoup已被FZ-007完整AOSP实现替代，勿当现态缺少XMLReader/parse。 |
| [JAVA-002](#java-002) T7-networkrequest | 未知 / historical | Boot method added；限制：Does not fix kotlinx.coroutines class loading | unknown / OH: unknown / 路由与代际: T7c | 无直接 APK 验证记录 | Does not fix kotlinx.coroutines class loading; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-003](#java-003) T7-mediastore | 部分实现 / historical | Fields and class initialization added；限制：No canManageMedia or Files.getContentUri in T7c | unknown / OH: unknown / 路由与代际: T7c | 无直接 APK 验证记录 | No canManageMedia or Files.getContentUri in T7c; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-004](#java-004) T7-networkinfo | 未知 / historical | Boot method added；限制：No ColorMatrix.setSaturation repair | unknown / OH: unknown / 路由与代际: T7c | 无直接 APK 验证记录 | No ColorMatrix.setSaturation repair; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-005](#java-005) T7-bandwidth | 未知 / historical | Bandwidth accessors added；限制：No getSignalStrength repair | unknown / OH: unknown / 路由与代际: T7c | 无直接 APK 验证记录 | No getSignalStrength repair; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-006](#java-006) J7-appwidget | 占位/降级 / historical | Registers class-to-service mapping, allocates manager and type-zero local IAppWidgetService；限制：Not real widget hosting; arrays empty | unknown / OH: unknown / 路由与代际: J7b | 无直接 APK 验证记录 | Not real widget hosting; arrays empty; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-007](#java-007) J7-vibrator | 占位/降级 / historical | Seeds mLock skipped by allocateInstance, existing service returns int[0]；限制：No physical vibration or EGL/native repair | unknown / OH: unknown / 路由与代际: J7b | 无直接 APK 验证记录 | No physical vibration or EGL/native repair; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-008](#java-008) J7-wifi | 部分实现 / historical | Allocates non-null WifiManager even when IWifiManager is absent；限制：mService may remain null; does not supply IWifiManager or prove every WifiManager method | unknown / OH: unknown / 路由与代际: J7b | 无直接 APK 验证记录 | mService may remain null; does not supply IWifiManager or prove every WifiManager method; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-009](#java-009) J7-battery | 占位/降级 / historical | Only missing BATTERY_CHANGED sticky returns a synthetic Intent with full-charge defaults；限制：Other actions retain original possibly-null return; no Camera JNI fix | unknown / OH: unknown / 路由与代际: J7b | 无直接 APK 验证记录 | Other actions retain original possibly-null return; no Camera JNI fix; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-010](#java-010) J7-search | 占位/降级 / historical | Local ISearchManager installed in sCache；限制：Type-zero service, not real search backend | unknown / OH: unknown / 路由与代际: J7b | 无直接 APK 验证记录 | Type-zero service, not real search backend; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-011](#java-011) J7-wallpaper | 占位/降级 / historical | Seeds sGlobals with a type-zero IWallpaperManager；限制：Returns null colors, not a real wallpaper service | unknown / OH: unknown / 路由与代际: J7b | 无直接 APK 验证记录 | Returns null colors, not a real wallpaper service; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-012](#java-012) 用户解锁状态投影 | 部分实现 / historical | 安装 child-local user binder；B7报告的用户200解锁查询返回true，避免SharedPreferences NPE，非完整多用户服务 | unknown / OH: OH 6.1.0.31 on 5cd (historical report) / 路由与代际: B7 r2 a92f8135/r3 5aff7a2b | fd-catima [reported] 原NPE为0，后续停在别的墙；报告明确无这些APK自己的UI; fd-fennec_fdroid [reported] 原NPE为0，后续停在别的墙；报告明确无这些APK自己的UI | 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-013](#java-013) 纯Java APK nativeLibraryDir 投影 | 部分实现 / historical | 不存在的nativeLibraryDir回退到该包代码目录；不创建任意native库能力 | unknown / OH: unknown / 路由与代际: B7 r2/r3 | opencamera [reported] 报告namespace错误为0；仍有AppCompat/provider墙; fd-etar [reported] 报告namespace错误为0；仍有AppCompat/provider墙; burgerking [reported] 报告namespace错误为0；仍有AppCompat/provider墙 | 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-014](#java-014) activity-alias 目标解析 | 部分实现 / historical | 启动入口为alias时解析targetActivity，并保持目标activity的元数据；不等于全部主题顺序正确 | unknown / OH: unknown / 路由与代际: B5 carried by B7 r3 | fd-fennec_fdroid [reported] 来源报告描述此修复/失败路径；未在本轮重新测试或目视截图 | alias主题另有U15顺序修复; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-015](#java-015) XML-only图标安全占位 | 部分实现 / historical | 声明图标仅vector/adaptive XML时允许模板占位；截断/不可读图标仍拒 | unknown / OH: unknown / 路由与代际: libapk_installer 1ebf78ab (B7); prior675536e8 | fd-k9 [reported] 历史bm install成功；不是应用UI验证 | 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-016](#java-016) 电话/订阅 present-but-off | 占位/降级 / historical | 非空manager+本地ITelephony/ISub类型零binder；SIM/电话/数据状态为0、标识null，不伪造IMEI，不提供电话硬件 | AOSP14 TelephonyFrameworkInitializer registration pattern (reported) / OH: unknown / 路由与代际: U11 277d4641 / U11i 5ae3dd29 | 无直接 APK 验证记录 | x/头条为预测受益，本文构建报告不能充作已经过墙; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-017](#java-017) SSLEngine 元数据安全实例 | 占位/降级 / historical | 非空协议/cipher/session元数据；wrap/unwrap明确SSLException，不实现TLS传输 | unknown / OH: unknown / 路由与代际: U11b d75e90c0 | 无直接 APK 验证记录 | 不得把非空SSLEngine标成可握手/联网; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-018](#java-018) 本包Provider实例化与发布 | 部分实现 / historical | post-bind实例化Provider、attachInfo并发布；检测mLocalProvidersByName避免双onCreate；Application.onCreate之后才运行，与AOSP顺序不同 | unknown / OH: unknown / 路由与代际: U11c74434240误接线→U11d84c8da6b→U11i5ae3dd29 | 无直接 APK 验证记录 | Application.onCreate内部查询Provider的时序未覆盖; 报告预测notepad增亮不当作实测; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-019](#java-019) 每进程AES/GCM自检（支撑知识） | 已实现 / historical | 随机256-bit SecretKeySpec走默认AES/GCM并做Tink式帧往返；记录错误，不是API修复 | unknown / OH: unknown / 路由与代际: U11h14ed34bc/U11i5ae3dd29 | 无直接 APK 验证记录 | key存在性probe与key-independent selftest不可混算; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推; 诊断支撑知识条目，不计新增API实现或点亮增益。 |
| [JAVA-020](#java-020) 资源型Provider authority纠正 | 部分实现 / historical | 将@resource authority按同class的PM投影解析；literal不变，无法解析仍保留并记日志 | unknown / OH: unknown / 路由与代际: U12r2 runtime0482c9b1 | 无直接 APK 验证记录 | 构建/单测证明，不在本文虚报notepad/fd-client上屏; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-021](#java-021) 电话class→service名映射 | 部分实现 / historical | 仅已存在fetcher而class无name时补phone/subscription映射 | unknown / OH: unknown / 路由与代际: U12r2 runtime0482c9b1 | 无直接 APK 验证记录 | 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-022](#java-022) TelephonyServiceManager惰性取值 | 部分实现 / historical | 增加getter与缓存字段；setter仍原no-op；能找本地phone/isub，不变成完整system_server服务 | AOSP14 class/member names per report / OH: unknown / 路由与代际: U12r2 stubs00b30467/615b8bbe | 无直接 APK 验证记录 | setter仍为stub，不能宣称完整初始化; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-023](#java-023) 老版Predicate入BCP | 已实现 / historical | 接口从独立runtime类加载器移到boot可见stubs；只提供类型契约 | AOSP <=7.1 interface (report; exact tag unknown) / OH: unknown / 路由与代际: U11i错误位置→U12r2 stubs | 无直接 APK 验证记录 | 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-024](#java-024) GCM默认nonce旧R3失败实现 | 部分实现 / historical | U12/R3用外层Cipher包装BC delegate；Android libcore未初始化delegate，host JVM成功不能外推ART | unknown / OH: unknown / 路由与代际: U12r2/U13v2 506abe23 | 无直接 APK 验证记录 | 旧版本已知selftest error，不得列为通过; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-025](#java-025) GCM默认nonce修正v3 | 部分实现 / historical | 直接驱动delegate CipherSpi；无参encrypt/wrap补12字节nonce/128-bit tag，显式IV/AAD透传 | AOSP android-14.0.0_r1 host ART (test semantics, not source of bespoke wrapper) / OH: unknown / 路由与代际: U13v3 bbc3f530190fe98e2979dc4059379f8a0259d1f6ab243830347ca875cdb62f9b | 无直接 APK 验证记录 | test为host ART+板BCP，Android设备实测仍unknown; 全体JCA算法不在本修复范围; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-026](#java-026) NameValueCache本地ANDROID_ID | 部分实现 / historical | 注入Global/Secure/System holder的call快路径；稳定16hex ID存no_backup，其余keysnull；无直接query/observer服务 | Westlake 1c883ad/2c46770; AOSP14 Settings named fields per report / OH: unknown / 路由与代际: U12r1 3bca82c5 | 无直接 APK 验证记录 | Config holder未注入; 直接ContentResolver查询仍OH桥，不是本地完整settings数据库; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-027](#java-027) 本包Provider提前查询 | 部分实现 / historical | 本包authority优先local lookup以免路由到不可连接OH DataShare；具体边界依赖OwnProviderLocal源码 | unknown / OH: unknown / 路由与代际: U11j57aaaf7d63→U12r1 | 无直接 APK 验证记录 | 未在本轮确认所有provider跨进程/Binder行为; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-028](#java-028) ViewDelegate写回 | 部分实现 / historical | 有同名同参super_*则转发，其余类型零；修框架layoutParams契约，不提供网页渲染 | unknown / OH: unknown / 路由与代际: J10e3c147964 | caniwebview [reported] 报告记录原ViewGroup NPE与离线接线检查；本轮未重看图; jslab [reported] 报告记录原ViewGroup NPE与离线接线检查；本轮未重看图; beecount [reported] 报告记录原ViewGroup NPE与离线接线检查；本轮未重看图; trickytripper [reported] 报告记录原ViewGroup NPE与离线接线检查；本轮未重看图 | 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-029](#java-029) CookieManager空实现 | 占位/降级 / historical | 覆盖含@hide的16abstract方法；acceptCookie=true/getCookie=null/其余no-op；不是cookie持久化 | unknown / OH: unknown / 路由与代际: J10e3c147964 | 无直接 APK 验证记录 | 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-030](#java-030) WebSettings类型零实例 | 占位/降级 / historical | 按AOSP14 r1生成104abstract overrides，getter类型零/setterno-op；不激活JS引擎；null String有后续非空风险 | AOSP android-14.0.0_r1 WebSettings.java / OH: unknown / 路由与代际: J10f a0f8ba45 | 无直接 APK 验证记录 | 非空实例不等于WebView可渲染; 后续安全字符串默认值需另版本证据; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-031](#java-031) NWeb Java转接候选 | 部分实现 / historical | Java controller转发backend与回调；mock19case，JNI declarations存在但此包无native实现 | AOSP14 WebViewProvider signatures (report) / OH: unknown / 路由与代际: M2 candidate | 无直接 APK 验证记录 | mock不证明板上NWeb功能/绘制; 尚未验native↔Java部署闭环; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-032](#java-032) AndroidX WebKit支持库边界缺口 | 缺口 / historical | 记录privacybrowser在自身AndroidX触发UnsupportedOperation，缺support-library glue；不与网页绘制backend混算 | unknown / OH: unknown / 路由与代际: U13 history | privacybrowser [reported] 来源历史首致命定性，非本轮运行 | 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-033](#java-033) Activity自己的manifest theme恢复 | 部分实现 / historical | 在所有theme覆写后、scheduleTransaction前恢复Activity主题，非alias才restore；不能用platform windowActionBar代替app androidx属性 | unknown / OH: unknown / 路由与代际: J10d57d62183 | knot [reported] 历史报告定位主题链；离线6/6不等于本轮上屏; deadhash [reported] 历史报告定位主题链；离线6/6不等于本轮上屏; diaspora [reported] 历史报告定位主题链；离线6/6不等于本轮上屏 | 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-034](#java-034) alias目标主题最终写入顺序 | 部分实现 / historical | 现有AliasTargetTheme在sEnrichedTheme覆写之后再调用一次；不是新manifest reader | unknown / OH: unknown / 路由与代际: U15 candidate20e748e57c6ee8bd0b97dcfff074c3a1c001dd727cbcee6a754f60a598642770 | 无直接 APK 验证记录 | fd-api主题板验待证；U15旧提案needle会被后续覆写，不能两者混算; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-035](#java-035) 本进程bind-service回调排序 | 部分实现 / historical | 等Activity started/resumed再投递service callback，destroyed丢弃；只覆盖in-process事件 | unknown / OH: unknown / 路由与代际: U14 candidate0349eb83 | 无直接 APK 验证记录 | 完整Termux启动/terminal bootstrap未在host测试复现; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-036](#java-036) trampoline finish延迟/去重 | 部分实现 / historical | own-package start未达本进程时最多hold3秒，launch或timeout转交一次；其他调用透传 | unknown / OH: unknown / 路由与代际: U15 candidate20e748e5 | 无直接 APK 验证记录 | host ART测试模拟OH adapter；36key预测不充作36个实测成功; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-037](#java-037) APK网络权限投影 | 部分实现 / historical | uses-permission精确映射为OH INTERNET/GET_NETWORK_INFO并去重；仅这两项，不概括全部Android权限 | unknown / OH: unknown / 路由与代际: B89 baseline6f94d4f4/eb6824b4→background6aadb8b4/7048c7c5 | 无直接 APK 验证记录 | ATM实际授予/联网结果需关联历史run，不由HAP生成单测外推; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-038](#java-038) OH后台启动能力授予 | 部分实现 / historical / FZ-001 | APL_NORMAL/isSystemApp=false不变；ACL+preAuthorization+HAP声明允许pending前台期内部startActivity；是OH capability，不是放开任意权限 | unknown / OH: unknown / 路由与代际: libbms6aadb8b4/libapk_installer7048c7c5 | fd-tusky [reported] frozen登记历史白→自身页面；含foundation重启协变量，本轮不目视; fd-k9 [reported] frozen登记历史白→自身页面；含foundation重启协变量，本轮不目视; fd-android [reported] frozen登记历史白→自身页面；含foundation重启协变量，本轮不目视; fd-filemanager [reported] frozen登记历史白→自身页面；含foundation重启协变量，本轮不目视 | 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-039](#java-039) 主入口优先app自身launcher | 部分实现 / candidate | 多个launcher中优先app自身包入口，减少LeakCanary误选；无launcher等回退仍由selector定义 | unknown / OH: unknown / 路由与代际: 7048c7c5 + donor3188a4733 | anki [static] 来源原APK launcher解析测试，非启动成功; wikipedia [static] 来源原APK launcher解析测试，非启动成功; noice [static] 来源原APK launcher解析测试，非启动成功 | 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-040](#java-040) ARS C最高密度bitmap图标 | 部分实现 / historical | manifest图标id经arsc解析最高密度桶；已触发位图路径，不证明所有resource配置 | unknown / OH: unknown / 路由与代际: B3 libapk_installer675536e8 | wikipedia [reported] 报告安装图标文件路径和尺寸；非app UI; termux [reported] 报告安装图标文件路径和尺寸；非app UI; aegis [reported] 报告安装图标文件路径和尺寸；非app UI; markor [reported] 报告安装图标文件路径和尺寸；非app UI; mcdonalds [reported] 报告安装图标文件路径和尺寸；非app UI; burgerking [reported] 报告安装图标文件路径和尺寸；非app UI | 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-041](#java-041) adaptive-icon像素合成候选 | 部分实现 / historical | AXML+arsc引用，ARGB纯色背景、双线性resize、src-over；B3板上未触发adaptive分支 | unknown / OH: unknown / 路由与代际: B3 libapk_installer675536e8 | 无直接 APK 验证记录 | 运行时unverified，不能把位图分支验证借给adaptive分支; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-042](#java-042) APK native提取精确例外 | 部分实现 / historical | 51e1b525为#77/#79修订版；与2c9原板回滚版差异需按选定ABI精确样例解读，不放开所有ELF | unknown / OH: unknown / 路由与代际: 51e1b52538b3198d2a8a3236a9479bf8512f51acc74c0d68e34acca358f39be5 vs2c9a5294 | 无直接 APK 验证记录 | 补丁源码recipe/archive单独绑定，libinstalls不是libapk_installer; 源树未必等于冻结archive成员; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-043](#java-043) alarm兼容底线 | 占位/降级 / historical | set接受但永不投递，next-alarm为空；单一fetcher非完整Android系统服务 | unknown / OH: unknown / 路由与代际: U9 source-inventory, must cross-check deployed238ffc14 | 无直接 APK 验证记录 | 该来源曾低估部署B8层；机制描述只用于列明底线，不能照此判所有当前服务缺失; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-044](#java-044) clipboard兼容底线 | 部分实现 / historical | ClipData进程内保存，非跨进程全局剪贴板；单一fetcher非完整Android系统服务 | unknown / OH: unknown / 路由与代际: U9 source-inventory, must cross-check deployed238ffc14 | 无直接 APK 验证记录 | 该来源曾低估部署B8层；机制描述只用于列明底线，不能照此判所有当前服务缺失; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-045](#java-045) account兼容底线 | 占位/降级 / historical | 空账号/无feature/token，未登录所有平台；单一fetcher非完整Android系统服务 | unknown / OH: unknown / 路由与代际: U9 source-inventory, must cross-check deployed238ffc14 | 无直接 APK 验证记录 | 该来源曾低估部署B8层；机制描述只用于列明底线，不能照此判所有当前服务缺失; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-046](#java-046) power兼容底线 | 占位/降级 / historical | interactive/no-power-save；wake-lock本地接受；单一fetcher非完整Android系统服务 | unknown / OH: unknown / 路由与代际: U9 source-inventory, must cross-check deployed238ffc14 | 无直接 APK 验证记录 | 该来源曾低估部署B8层；机制描述只用于列明底线，不能照此判所有当前服务缺失; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-047](#java-047) uimode兼容底线 | 部分实现 / historical | NORMAL/night来自Resources配置；单一fetcher非完整Android系统服务 | unknown / OH: unknown / 路由与代际: U9 source-inventory, must cross-check deployed238ffc14 | 无直接 APK 验证记录 | 该来源曾低估部署B8层；机制描述只用于列明底线，不能照此判所有当前服务缺失; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-048](#java-048) content兼容底线 | 占位/降级 / historical | observer生命周期no-op，sync默认空；单一fetcher非完整Android系统服务 | unknown / OH: unknown / 路由与代际: U9 source-inventory, must cross-check deployed238ffc14 | 无直接 APK 验证记录 | 该来源曾低估部署B8层；机制描述只用于列明底线，不能照此判所有当前服务缺失; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-049](#java-049) audio兼容底线 | 占位/降级 / historical | IAudioService类型零，不提供AudioFlinger；单一fetcher非完整Android系统服务 | unknown / OH: unknown / 路由与代际: U9 source-inventory, must cross-check deployed238ffc14 | 无直接 APK 验证记录 | 该来源曾低估部署B8层；机制描述只用于列明底线，不能照此判所有当前服务缺失; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-050](#java-050) storage兼容底线 | 占位/降级 / historical | IStorageManager报告一个volume；其他事务空值可能造成cacheQuota=0；单一fetcher非完整Android系统服务 | unknown / OH: unknown / 路由与代际: U9 source-inventory, must cross-check deployed238ffc14 | 无直接 APK 验证记录 | 该来源曾低估部署B8层；机制描述只用于列明底线，不能照此判所有当前服务缺失; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-051](#java-051) appops部署注册 | 未知 / candidate | B8BindExtras.SERVICES反射sCache；清单只证明注册路径，未证明全方法功能 | unknown / OH: unknown / 路由与代际: U9 deployed JAR238ffc14 | 无直接 APK 验证记录 | binder非空/注册存在不能冒充真实backend与功能验证; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-052](#java-052) locale部署注册 | 未知 / candidate | B8BindExtras.SERVICES反射sCache；清单只证明注册路径，未证明全方法功能 | unknown / OH: unknown / 路由与代际: U9 deployed JAR238ffc14 | 无直接 APK 验证记录 | binder非空/注册存在不能冒充真实backend与功能验证; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-053](#java-053) notification部署注册 | 未知 / candidate | B8BindExtras.SERVICES类型安全binder；清单只证明注册路径，未证明全方法功能 | unknown / OH: unknown / 路由与代际: U9 deployed JAR238ffc14 | 无直接 APK 验证记录 | binder非空/注册存在不能冒充真实backend与功能验证; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-054](#java-054) shortcut部署注册 | 未知 / candidate | WlShortcutService native接线install；清单只证明注册路径，未证明全方法功能 | unknown / OH: unknown / 路由与代际: U9 deployed JAR238ffc14 | 无直接 APK 验证记录 | binder非空/注册存在不能冒充真实backend与功能验证; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-055](#java-055) media_session部署注册 | 占位/降级 / candidate | WlMediaSession+fetcher；mService stub；清单只证明注册路径，未证明全方法功能 | unknown / OH: unknown / 路由与代际: U9 deployed JAR238ffc14 | 无直接 APK 验证记录 | binder非空/注册存在不能冒充真实backend与功能验证; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-056](#java-056) power_exemption部署注册 | 占位/降级 / candidate | manager+mService stub；清单只证明注册路径，未证明全方法功能 | unknown / OH: unknown / 路由与代际: U9 deployed JAR238ffc14 | 无直接 APK 验证记录 | binder非空/注册存在不能冒充真实backend与功能验证; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-057](#java-057) restrictions部署注册 | 占位/降级 / candidate | empty-Bundle service；清单只证明注册路径，未证明全方法功能 | unknown / OH: unknown / 路由与代际: U9 deployed JAR238ffc14 | 无直接 APK 验证记录 | binder非空/注册存在不能冒充真实backend与功能验证; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-058](#java-058) fingerprint U9缺口 | 缺口 / candidate | U9 gap-table没有提供记录；这是当时fetcher/模块服务缺口，静态请求数量不等于实际失败数量 | unknown / OH: unknown / 路由与代际: U9 only | 无直接 APK 验证记录 | 不得将此历史缺口当当前版本仍缺; 未报告的APK不能补验证成功；NSD类型/服务实现另拆; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-059](#java-059) biometric U9缺口 | 缺口 / candidate | U9 gap-table没有提供记录；这是当时fetcher/模块服务缺口，静态请求数量不等于实际失败数量 | unknown / OH: unknown / 路由与代际: U9 only | 无直接 APK 验证记录 | 不得将此历史缺口当当前版本仍缺; 未报告的APK不能补验证成功；NSD类型/服务实现另拆; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-060](#java-060) media_metrics U9缺口 | 缺口 / candidate | U9 gap-table没有提供记录；这是当时fetcher/模块服务缺口，静态请求数量不等于实际失败数量 | unknown / OH: unknown / 路由与代际: U9 only | 无直接 APK 验证记录 | 不得将此历史缺口当当前版本仍缺; 未报告的APK不能补验证成功；NSD类型/服务实现另拆; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-061](#java-061) grammatical_inflection U9缺口 | 缺口 / candidate | U9 gap-table没有提供记录；这是当时fetcher/模块服务缺口，静态请求数量不等于实际失败数量 | unknown / OH: unknown / 路由与代际: U9 only | 无直接 APK 验证记录 | 不得将此历史缺口当当前版本仍缺; 未报告的APK不能补验证成功；NSD类型/服务实现另拆; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-062](#java-062) bluetooth U9缺口 | 缺口 / candidate | U9 gap-table没有提供记录；这是当时fetcher/模块服务缺口，静态请求数量不等于实际失败数量 | unknown / OH: unknown / 路由与代际: U9 only | 无直接 APK 验证记录 | 不得将此历史缺口当当前版本仍缺; 未报告的APK不能补验证成功；NSD类型/服务实现另拆; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-063](#java-063) batterymanager U9缺口 | 缺口 / candidate | U9 gap-table没有提供记录；这是当时fetcher/模块服务缺口，静态请求数量不等于实际失败数量 | unknown / OH: unknown / 路由与代际: U9 only | 无直接 APK 验证记录 | 不得将此历史缺口当当前版本仍缺; 未报告的APK不能补验证成功；NSD类型/服务实现另拆; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-064](#java-064) storagestats U9缺口 | 缺口 / candidate | U9 gap-table没有提供记录；这是当时fetcher/模块服务缺口，静态请求数量不等于实际失败数量 | unknown / OH: unknown / 路由与代际: U9 only | 无直接 APK 验证记录 | 不得将此历史缺口当当前版本仍缺; 未报告的APK不能补验证成功；NSD类型/服务实现另拆; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-065](#java-065) wifip2p U9缺口 | 缺口 / candidate | U9 gap-table没有提供记录；这是当时fetcher/模块服务缺口，静态请求数量不等于实际失败数量 | unknown / OH: unknown / 路由与代际: U9 only | 无直接 APK 验证记录 | 不得将此历史缺口当当前版本仍缺; 未报告的APK不能补验证成功；NSD类型/服务实现另拆; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-066](#java-066) usb U9缺口 | 缺口 / candidate | U9 gap-table没有提供记录；这是当时fetcher/模块服务缺口，静态请求数量不等于实际失败数量 | unknown / OH: unknown / 路由与代际: U9 only | 无直接 APK 验证记录 | 不得将此历史缺口当当前版本仍缺; 未报告的APK不能补验证成功；NSD类型/服务实现另拆; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-067](#java-067) device_policy U9缺口 | 缺口 / candidate | U9 gap-table没有提供记录；这是当时fetcher/模块服务缺口，静态请求数量不等于实际失败数量 | unknown / OH: unknown / 路由与代际: U9 only | 无直接 APK 验证记录 | 不得将此历史缺口当当前版本仍缺; 未报告的APK不能补验证成功；NSD类型/服务实现另拆; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-068](#java-068) dropbox U9缺口 | 缺口 / candidate | U9 gap-table没有提供记录；这是当时fetcher/模块服务缺口，静态请求数量不等于实际失败数量 | unknown / OH: unknown / 路由与代际: U9 only | 无直接 APK 验证记录 | 不得将此历史缺口当当前版本仍缺; 未报告的APK不能补验证成功；NSD类型/服务实现另拆; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-069](#java-069) servicediscovery U9缺口 | 缺口 / candidate | U9 gap-table没有提供记录；这是当时fetcher/模块服务缺口，静态请求数量不等于实际失败数量 | unknown / OH: unknown / 路由与代际: U9 only | 无直接 APK 验证记录 | 不得将此历史缺口当当前版本仍缺; 未报告的APK不能补验证成功；NSD类型/服务实现另拆; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推; U15只补NSD类型/值对象，5行为仍unsupported且service null，不能变完整支持。 |
| [JAVA-070](#java-070) usagestats U9缺口 | 缺口 / candidate | U9 gap-table没有提供记录；这是当时fetcher/模块服务缺口，静态请求数量不等于实际失败数量 | unknown / OH: unknown / 路由与代际: U9 only | 无直接 APK 验证记录 | 不得将此历史缺口当当前版本仍缺; 未报告的APK不能补验证成功；NSD类型/服务实现另拆; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-071](#java-071) crossprofileapps U9缺口 | 缺口 / candidate | U9 gap-table没有提供记录；这是当时fetcher/模块服务缺口，静态请求数量不等于实际失败数量 | unknown / OH: unknown / 路由与代际: U9 only | 无直接 APK 验证记录 | 不得将此历史缺口当当前版本仍缺; 未报告的APK不能补验证成功；NSD类型/服务实现另拆; 无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown; 当前部署是否为该历史/候选版本未核，不由最新目录名外推 |
| [JAVA-072](#java-072) ConnectivityManager成员补全 | 部分实现 / candidate | Handler/timeout overload委托已存在方法；从active network派生info/active；listeners no-op、restriction固定DISABLED；不是完整网络管理 | AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults / OH: unknown / 路由与代际: T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage | 无直接 APK 验证记录 | 138新增members是静态链接覆盖，不是138个功能实测; 其它缺失members48项仍在扫描残表，未分类为实现; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验 |
| [JAVA-073](#java-073) InetAddresses成员补全 | 已实现 / candidate | parseNumericAddress按AOSP数值IP解析入口；不等同DNS/绑定网络语义 | AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults / OH: unknown / 路由与代际: T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage | 无直接 APK 验证记录 | 138新增members是静态链接覆盖，不是138个功能实测; 其它缺失members48项仍在扫描残表，未分类为实现; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验 |
| [JAVA-074](#java-074) IpPrefix成员补全 | 占位/降级 / candidate | 无后备状态时default getter；非完整前缀语义 | AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults / OH: unknown / 路由与代际: T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage | 无直接 APK 验证记录 | 138新增members是静态链接覆盖，不是138个功能实测; 其它缺失members48项仍在扫描残表，未分类为实现; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验 |
| [JAVA-075](#java-075) LinkAddress成员补全 | 占位/降级 / candidate | 无后备状态时default getter | AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults / OH: unknown / 路由与代际: T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage | 无直接 APK 验证记录 | 138新增members是静态链接覆盖，不是138个功能实测; 其它缺失members48项仍在扫描残表，未分类为实现; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验 |
| [JAVA-076](#java-076) LinkProperties成员补全 | 占位/降级 / candidate | 默认构造对象空list/null；无真实链路枚举 | AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults / OH: unknown / 路由与代际: T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage | 无直接 APK 验证记录 | 138新增members是静态链接覆盖，不是138个功能实测; 其它缺失members48项仍在扫描残表，未分类为实现; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验 |
| [JAVA-077](#java-077) Network成员补全 | 部分实现 / candidate | default-network URL/socket/DNS；handle为NETID_UNSET0，fromNetworkHandle校验；不绑定真实netId | AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults / OH: unknown / 路由与代际: T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage | 无直接 APK 验证记录 | 138新增members是静态链接覆盖，不是138个功能实测; 其它缺失members48项仍在扫描残表，未分类为实现; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验 |
| [JAVA-078](#java-078) NetworkCapabilities成员补全 | 占位/降级 / candidate | 缺状态时默认null TransportInfo等，不当真实能力探测 | AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults / OH: unknown / 路由与代际: T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage | 无直接 APK 验证记录 | 138新增members是静态链接覆盖，不是138个功能实测; 其它缺失members48项仍在扫描残表，未分类为实现; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验 |
| [JAVA-079](#java-079) NetworkInfo$DetailedState成员补全 | 部分实现 / candidate | 13个AOSP常量名与==实例比较；保留plain class，不重塑为Enum | AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults / OH: unknown / 路由与代际: T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage | 无直接 APK 验证记录 | 138新增members是静态链接覆盖，不是138个功能实测; 其它缺失members48项仍在扫描残表，未分类为实现; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验 |
| [JAVA-080](#java-080) NetworkInfo成员补全 | 部分实现 / candidate | 从虚getType/isConnected派生typeName/detailedState；subtype固定UNKNOWN；其余空/默认 | AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults / OH: unknown / 路由与代际: T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage | 无直接 APK 验证记录 | 138新增members是静态链接覆盖，不是138个功能实测; 其它缺失members48项仍在扫描残表，未分类为实现; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验 |
| [JAVA-081](#java-081) RouteInfo成员补全 | 占位/降级 / candidate | 默认对象null字段；非真实路由表 | AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults / OH: unknown / 路由与代际: T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage | 无直接 APK 验证记录 | 138新增members是静态链接覆盖，不是138个功能实测; 其它缺失members48项仍在扫描残表，未分类为实现; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验 |
| [JAVA-082](#java-082) TrafficStats成员补全 | 占位/降级 / candidate | 统计计数/uid/tag返回-1，tag/untag/operationcount no-op；没有流量采集 | AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults / OH: unknown / 路由与代际: T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage | 无直接 APK 验证记录 | 138新增members是静态链接覆盖，不是138个功能实测; 其它缺失members48项仍在扫描残表，未分类为实现; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验 |
| [JAVA-083](#java-083) ScanResult成员补全 | 部分实现 / candidate | 补public字段及复制构造签名；并不实现扫描 | AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults / OH: unknown / 路由与代际: T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage | 无直接 APK 验证记录 | 138新增members是静态链接覆盖，不是138个功能实测; 其它缺失members48项仍在扫描残表，未分类为实现; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验 |
| [JAVA-084](#java-084) WifiInfo成员补全 | 占位/降级 / candidate | 默认未连接对象、unknown ssid/INVALID_RSSI/redactions；不是真WiFi状态 | AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults / OH: unknown / 路由与代际: T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage | 无直接 APK 验证记录 | 138新增members是静态链接覆盖，不是138个功能实测; 其它缺失members48项仍在扫描残表，未分类为实现; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验 |
| [JAVA-085](#java-085) WifiManager成员补全 | 占位/降级 / candidate | 无IWifiManager时默认值/空list；无radio扫描/锁/开关实际效果 | AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults / OH: unknown / 路由与代际: T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage | 无直接 APK 验证记录 | 138新增members是静态链接覆盖，不是138个功能实测; 其它缺失members48项仍在扫描残表，未分类为实现; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验 |
| [JAVA-086](#java-086) NetworkRequest成员补全 | 部分实现 / candidate | 无要求请求的默认逻辑；不是完整request注册或匹配状态 | AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults / OH: unknown / 路由与代际: T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage | 无直接 APK 验证记录 | 138新增members是静态链接覆盖，不是138个功能实测; 其它缺失members48项仍在扫描残表，未分类为实现; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验 |
| [JAVA-087](#java-087) NetworkRequest$Builder成员补全 | 占位/降级 / candidate | 新增builder选项安全默认，不真实纳入other-UID网络 | AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults / OH: unknown / 路由与代际: T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage | 无直接 APK 验证记录 | 138新增members是静态链接覆盖，不是138个功能实测; 其它缺失members48项仍在扫描残表，未分类为实现; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验 |
| [JAVA-088](#java-088) WifiConfiguration成员补全 | 未知 / candidate | 成员表证明名字/签名存在；本轮未完整逐body审计，留unknown | AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults / OH: unknown / 路由与代际: T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage | 无直接 APK 验证记录 | 138新增members是静态链接覆盖，不是138个功能实测; 其它缺失members48项仍在扫描残表，未分类为实现; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验 |
| [JAVA-089](#java-089) 签名依赖类新增 | 部分实现 / candidate | 8个签名依赖类型保证resolve；逐类型行为另见donor，不因class可load判有硬件服务 | unknown / OH: unknown / 路由与代际: net-stubs-members-v1 | 无直接 APK 验证记录 | Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验 |
| [JAVA-090](#java-090) NSD接口/监听器类型 | 已实现 / candidate | AOSP监听器接口/默认回调保持原样，修Unresolved Reference verifier shape；不建立mdns后端 | android-14.0.0_r1 Connectivity bd692130 / OH: unknown / 路由与代际: U15 candidate94a949053ec8c5a520a9a228b64ae8adb861977f92a6b5f63fa689214c4628fe | 无直接 APK 验证记录 | immich受益只是host ART linking测试；未来libcronet墙另存; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验 |
| [JAVA-091](#java-091) NSD服务信息值对象 | 已实现 / candidate | NsdServiceInfo AOSP文件逐字采用，getter/setter/Parcelable；值对象真实，不是发现服务 | android-14.0.0_r1 Connectivity bd692130 / OH: unknown / 路由与代际: U15 candidate94a94905 | 无直接 APK 验证记录 | Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验 |
| [JAVA-092](#java-092) NSD行为明确unsupported | 占位/降级 / candidate | 5methods保持AOSP签名但抛UnsupportedOperationException；manager不可实例化；无服务注册 | unknown / OH: unknown / 路由与代际: U15 candidate94a94905 | 无直接 APK 验证记录 | Context.getSystemService("servicediscovery")仍null；不算mDNS已实现; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验 |
| [JAVA-093](#java-093) BLE callback原版类型 | 已实现 / candidate | AOSP原版abstract callback及ScanFailed annotation；空default callback是上游契约，不提供BLE扫描 | android-14.0.0_r1 Bluetooth cbb30d72 / OH: unknown / 路由与代际: U14 stubs87cf65cc | 无直接 APK 验证记录 | fd-plus仅历史bind缺类+候选host test；不借为实际蓝牙功能; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验 |
| [JAVA-094](#java-094) android/bluetooth/le/尚缺类型 | 缺口 / candidate | 历史U10.1T8/U12/U13 BCP类型差集；ScanCallback后补见独立行，不泛称整个Bluetooth完整 | unknown / OH: unknown / 路由与代际: BCP2f365a75/615b8bbe vs android34 SDK | 无直接 APK 验证记录 | 缺类静态引用87keys是上界，仅fd-plus有历史缺类致命; API34在此是inventory reference，非所有API被测支持; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验; 含后续已补ScanCallback的旧BCP差集，不能当U14后现态差集。 |
| [JAVA-095](#java-095) android/bluetooth/尚缺类型 | 缺口 / candidate | 历史U10.1T8/U12/U13 BCP类型差集；ScanCallback后补见独立行，不泛称整个Bluetooth完整 | unknown / OH: unknown / 路由与代际: BCP2f365a75/615b8bbe vs android34 SDK | 无直接 APK 验证记录 | 缺类静态引用87keys是上界，仅fd-plus有历史缺类致命; API34在此是inventory reference，非所有API被测支持; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验 |
| [JAVA-096](#java-096) 生命周期:task-root/本包task | 部分实现 / historical | 记录应用的一个task，修-1/空返回；不是完整任务栈；只属于source-build/host路线，绝不套U13/128签认 | unknown / OH: unknown / 路由与代际: r84 builds81/84 | Instagram [reported] build81后不再因isTaskRoot=false立即finish，随后还遇到ModalActivity同步重入，非完整功能通过。 [reported；本轮未目视/上板]; CapCut [reported] 原launcher检查isTaskRoot=false就关闭；task model纠正，后续home drawing含build83+shim组合，不单归本条。 [reported；本轮未目视/上板]; Shazam [reported] 纠正launcher的task-root自finish路径；r86另外修own implicit intent，本条不借最终drawing作独立验证。 [reported；本轮未目视/上板]; fmessages [reported] 原launcher同属task-root错误关闭组；本包task纠正不证明SMS role/电话硬件可用。 [reported；本轮未目视/上板]; RedReader [reported] 报告build83组合后draw，原task-root自finish纠正；不是单API因果证明。 [reported；本轮未目视/上板] | 源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验; members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。 |
| [JAVA-097](#java-097) 生命周期:本进程started services | 部分实现 / candidate | 服务创建一次，每次start分发onStartCommand并按AOSPstop规则处理；只属于source-build/host路线，绝不套U13/128签认 | unknown / OH: unknown / 路由与代际: r84 build84 | 无直接 APK 验证记录 | 243静态调用keys不是243功能验证; 源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验; members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。 |
| [JAVA-098](#java-098) 生命周期:本包broadcast | 部分实现 / candidate | 保存receiver并按匹配派发本包广播；有sticky默认，不提供完整跨进程广播；只属于source-build/host路线，绝不套U13/128签认 | unknown / OH: unknown / 路由与代际: r84 build84 | 无直接 APK 验证记录 | 源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验; members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。 |
| [JAVA-099](#java-099) 系统服务:MemoryInfo | 部分实现 / historical | 从/proc/meminfo与ProcessList levels填内存数据；替代不写out结构的桩；只属于source-build/host路线，绝不套U13/128签认 | unknown / OH: unknown / 路由与代际: r84 build84 | CNN [reported] getMemoryInfo原来不填out结构，现从/proc/meminfo填；build84组合测试CNN draw，但另需getSpace0，不单归MemoryInfo。 [reported；本轮未目视/上板] | 源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验; members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。 |
| [JAVA-100](#java-100) 资源:Application labelRes保持 | 部分实现 / historical | 不在launch清空Android资源ID，修labelRes为0的标签路径；只属于source-build/host路线，绝不套U13/128签认 | unknown / OH: unknown / 路由与代际: r84 build82/83 | ScrambledExif [reported] Application labelRes曾被launch清零；保留资源ID后build83组合20-app测试报告draw。 [reported；本轮未目视/上板] | 源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验; members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。 |
| [JAVA-101](#java-101) 系统服务:cache quota默认 | 占位/降级 / historical | StorageStatsService以64MiB默认回答；不是实时空间配额系统；只属于source-build/host路线，绝不套U13/128签认 | unknown / OH: unknown / 路由与代际: r84 build82 | LibreTube [reported] cache quota原为0；StorageStatsService回答64MiB默认值后build82组合报告draw，不证明真实配额。 [reported；本轮未目视/上板] | 源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验; members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。 |
| [JAVA-102](#java-102) 内容提供者:authority manifest顺序 | 部分实现 / historical | manifest顺序占authority，避开disabled provider抢占；只报告本包机制；只属于source-build/host路线，绝不套U13/128签认 | unknown / OH: unknown / 路由与代际: r84 build82/83 | quitter [reported] disabled provider曾先占authority；改manifest顺序后build83组合测试报告draw。 [reported；本轮未目视/上板] | 源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验; members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。 |
| [JAVA-103](#java-103) 生命周期:异步本包launch与Intent保留 | 部分实现 / historical | own activity在caller当前消息后启动，传app自己的Intent而非OH前缀action；只属于source-build/host路线，绝不套U13/128签认 | unknown / OH: unknown / 路由与代际: r84 builds82/84/85 | Instagram [reported] ModalActivity.onCreate曾同步进入caller.startActivity；改在caller消息后启动，后续仍有停止点，不是完整功能通过。 [reported；本轮未目视/上板]; AndStatus [reported] 旧Want带OH前缀action而等待defaults后finish；build82/build85保留本包Intent/action，报告draw。 [reported；本轮未目视/上板] | 源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验; members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。 |
| [JAVA-104](#java-104) 文件空间:libcore真实查询 | 部分实现 / historical | missing-natives将libcore statvfs实现覆写return0 runtime stub；JNI交叉给native shard；只属于source-build/host路线，绝不套U13/128签认 | unknown / OH: unknown / 路由与代际: r84 runtime override | CNN [reported] File usable space=0使OkHttp maxSize<=0；12-app File-space单项换statvfs后CNN draw，报告无回退。 [reported；本轮未目视/上板] | native绑定winner/TU/产物SHA需native shard补，不由Java导出推功能; 源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验; members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。 |
| [JAVA-105](#java-105) 资源/窗口:global Configuration | 部分实现 / historical | 每窗使用display global configuration，修bind-time bounds为0；确切bridge method/TU未知；只属于source-build/host路线，绝不套U13/128签认 | unknown / OH: unknown / 路由与代际: r86 builds86–90 | Draw Anywhere [reported] display作为global Configuration后从原overlay/view阶段推进到drawing；不是overlay全过程功能验证。 [reported；本轮未目视/上板] | 源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验; members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。 |
| [JAVA-106](#java-106) 生命周期:本包implicit intent | 部分实现 / historical | 为app自己activities解析implicit intents；不承诺跨app resolver完整；只属于source-build/host路线，绝不套U13/128签认 | unknown / OH: unknown / 路由与代际: r86 builds86–90 | Shazam [reported] 补本包implicit intent后从未绘制推进drawing；不证明跨包resolver完整。 [reported；本轮未目视/上板] | 源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验; members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。 |
| [JAVA-107](#java-107) 生命周期:onPostCreate与launch transaction | 部分实现 / historical | launch transaction带start，确保onPostCreate；本地init调用链未绑定到产物；只属于source-build/host路线，绝不套U13/128签认 | unknown / OH: unknown / 路由与代际: r86 builds86–90 | linphone [reported] launch transaction带start使onPostCreate运行，原等待onPostCreate路径推进drawing；不是通话验证。 [reported；本轮未目视/上板] | 源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验; members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。 |
| [JAVA-108](#java-108) 窗口/输入:SurfaceView焦点组 | 部分实现 / candidate | 父window与SurfaceViews的OH windows作为一个focus group；native部分由native shard对齐；只属于source-build/host路线，绝不套U13/128签认 | unknown / OH: unknown / 路由与代际: r86 builds86–90 | 无直接 APK 验证记录 | 源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验; members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。 |
| [JAVA-109](#java-109) 权限:runtime request回调 | 部分实现 / candidate | in-process回答permission requests；报告未列所有结果/授权策略，不推成全授权；只属于source-build/host路线，绝不套U13/128签认 | unknown / OH: unknown / 路由与代际: r86 builds86–90 | 无直接 APK 验证记录 | 源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验; members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。 |
| [JAVA-110](#java-110) 系统服务:Android15 CEunlock名称 | 未知 / candidate | README只称按Android15名称回答credential-encrypted unlock；精确method名/源码尚无直接证据，不能猜；只属于source-build/host路线，绝不套U13/128签认 | unknown / OH: unknown / 路由与代际: r86 builds86–90 | 无直接 APK 验证记录 | 精确CEunlock member名待来源补；本项保留unknown; 源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验; members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。 |
| [JAVA-111](#java-111) 生命周期:direct resume只一次 | 部分实现 / candidate | direct launch仅在launch transaction resume，消重复报告；只属于source-build/host路线，绝不套U13/128签认 | unknown / OH: unknown / 路由与代际: r86 build92 | 无直接 APK 验证记录 | build90重复resume旧行为保留为前史，不混新实现; 源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验; members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。 |
| [JAVA-112](#java-112) 权限/标识:序列号按Android拒绝 | 部分实现 / historical | in-process service拒getSerial并抛SecurityException，插件可catch；不伪造serial；只属于source-build/host路线，绝不套U13/128签认 | unknown / OH: unknown / 路由与代际: r87 builds91–95 | wormhole2 [reported] getSerial原遇null service抛NPE使插件失败；改SecurityException被插件catch，报告首屏drawing，不提供真实serial。 [reported；本轮未目视/上板] | 源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验; members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。 |
| [JAVA-113](#java-113) 系统服务:LauncherApps本用户回答 | 部分实现 / historical | in-process LauncherApps能枚举本用户profile/launcher；透明window仍可能只见host；只属于source-build/host路线，绝不套U13/128签认 | unknown / OH: unknown / 路由与代际: r87 builds91–95 | cclauncher [reported] LauncherApps可读本用户profiles/launcher activities、first frame drawn；透明windowShowWallpaper仍只见host screen，非可见launcher UI。 [reported；本轮未目视/上板] | 源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验; members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。 |
| [JAVA-114](#java-114) 系统服务:User profile group | 部分实现 / historical | 给app唯一用户profile group回答；不当多用户管理完整实现；只属于source-build/host路线，绝不套U13/128签认 | unknown / OH: unknown / 路由与代际: r87 builds91–95 | clauncher [reported] getProfileIds不再拒绝，白色clock/hints已画；透明窗叠light host仍像host。r88黑host后可见，wallpaper仍缺。 [reported；本轮未目视/上板] | 源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验; members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。 |
| [JAVA-115](#java-115) 安装/入口:相对Activity名展开 | 部分实现 / historical | launcher展开manifest相对package的Activity名；具体源码method待追证；只属于source-build/host路线，绝不套U13/128签认；未证明源码调用ComponentName.createRelative。 | unknown / OH: unknown / 路由与代际: r87 launcher | Emacs [reported] launcher展开manifest相对Activity名后，从r86首activity停止推进drawing；非全Emacs功能验证。 [reported；本轮未目视/上板] | ComponentName.createRelative为对应Android契约名，README不证明实现调用它; 源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验; members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。 |
| [JAVA-116](#java-116) 权限/音频:host microphone声明 | 部分实现 / historical | 执行OH录音call的是host；host申请MICROPHONE并原UID覆盖安装，非只Android APK声明即可；只属于source-build/host路线，绝不套U13/128签认 | unknown / OH: unknown / 路由与代际: r87 host application | MuseKit [reported] host缺MICROPHONE致AudioRecord未初始化；声明授予并保留UID覆盖安装后，报告调音器可见且能听音，仍是reported。 [reported；本轮未目视/上板] | host HAP与运行时SHA待引用该路线receipt；reported listens不改成本轮功能测试; 源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验; members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。 |
| [JAVA-117](#java-117) 时间:默认时区supplier | 部分实现 / candidate | common init安装Android同型supplier，读取persist.sys.timezone后回退OH persist.time.timezone，避免所有appUTC；只属于source-build/host路线，绝不套U13/128签认 | unknown / OH: unknown / 路由与代际: r88 build96 | 无直接 APK 验证记录 | 报告只列clocks/calendars整类，不能造具体APK成功对象; 源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验; members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。 |
| [JAVA-118](#java-118) 系统服务:VPN未同意答案 | 部分实现 / historical | in-process返回用户尚未同意该app VPN的Android状态；不当VPN隧道已工作；只属于source-build/host路线，绝不套U13/128签认 | unknown / OH: unknown / 路由与代际: r89 build99 | socks5 [reported] 以未同意VPN状态回答vpn_management，报告first frame1.37s；不证明隧道建立/转发。 [reported；本轮未目视/上板]; blockads [reported] 报告VPN线程不再抛错；未授权状态答案不等于隧道成功。 [reported；本轮未目视/上板] | 源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验; members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。 |
| [JAVA-119](#java-119) 加密:legacy KeyPairGeneratorSpec | 部分实现 / historical | in-process provider转旧spec为支持的参数，保留Android语义；算法/持久化范围未全部证明；只属于source-build/host路线，绝不套U13/128签认 | unknown / OH: unknown / 路由与代际: r89 build99 | gitling [reported] 支持legacy KeyPairGeneratorSpec；另有UnixNativeDispatcher补齐，组合后first frame3.2s/drawing，不证明硬件KeyStore认证。 [reported；本轮未目视/上板] | 源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验; members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。 |
| [JAVA-120](#java-120) 包管理:platform android包 | 部分实现 / historical | PM能回答platform package android，修服务调用NameNotFound；不从此泛称安装任意system包；只属于source-build/host路线，绝不套U13/128签认 | unknown / OH: unknown / 路由与代际: r89 build99 | NewPipe [reported] PM回答platform android包，媒体服务启动的NameNotFoundException消失、服务起来；不证明所有播放/网络功能。 [reported；本轮未目视/上板]; Retro Music [reported] platform android包NameNotFoundException消失、媒体服务可启动；非本轮播放实测。 [reported；本轮未目视/上板] | 源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA; Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围; 源码路线、候选、历史验证与当前部署分开，未做本轮设备核验; members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。 |
| [NATIVE-001](#native-001) libEGL.so：当时缺口 | 缺口 / historical | 仅对API33 stub核dynsym；本组3名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-002](#native-002) libEGL.so：当时导出，功能未知 | 未知 / historical | 仅对API33 stub核dynsym；本组70名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=oh；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-003](#native-003) libGLESv1_CM.so：当时缺口 | 缺口 / historical | 仅对API33 stub核dynsym；本组180名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-004](#native-004) libGLESv1_CM.so：当时导出，功能未知 | 未知 / historical | 仅对API33 stub核dynsym；本组98名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=oh；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-005](#native-005) libGLESv2.so：当时导出，功能未知 | 未知 / historical | 仅对API33 stub核dynsym；本组204名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=oh；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-006](#native-006) libGLESv3.so：当时导出，功能未知 | 未知 / historical | 仅对API33 stub核dynsym；本组418名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=oh；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-007](#native-007) libOpenMAXAL.so：当时缺口 | 缺口 / historical | 仅对API33 stub核dynsym；本组44名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-008](#native-008) libOpenSLES.so：当时缺口 | 缺口 / historical | 仅对API33 stub核dynsym；本组11名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-009](#native-009) libOpenSLES.so：当时导出，功能未知 | 未知 / historical | 仅对API33 stub核dynsym；本组45名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=oh；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-010](#native-010) libaaudio.so：当时缺口 | 缺口 / historical | 仅对API33 stub核dynsym；本组67名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-011](#native-011) libamidi.so：当时缺口 | 缺口 / historical | 仅对API33 stub核dynsym；本组14名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-012](#native-012) libandroid.so：当时缺口 | 缺口 / historical | 仅对API33 stub核dynsym；本组277名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有37名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-013](#native-013) libandroid.so：当时导出，功能未知 | 未知 / historical | 仅对API33 stub核dynsym；本组46名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=westlake；source-build另profile有4名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-014](#native-014) libbinder_ndk.so：当时缺口 | 缺口 / historical | 仅对API33 stub核dynsym；本组107名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有104名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-015](#native-015) libc.so：当时缺口 | 缺口 / historical | 仅对API33 stub核dynsym；本组214名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有6名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-016](#native-016) libc.so：当时导出，功能未知 | 未知 / historical | 仅对API33 stub核dynsym；本组1170名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=oh；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-017](#native-017) libc.so：当时导出，功能未知 | 未知 / historical | 仅对API33 stub核dynsym；本组9名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=westlake；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-018](#native-018) libcamera2ndk.so：当时缺口 | 缺口 / historical | 仅对API33 stub核dynsym；本组69名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-019](#native-019) libdl.so：当时缺口 | 缺口 / historical | 仅对API33 stub核dynsym；本组3名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-020](#native-020) libdl.so：当时导出，功能未知 | 未知 / historical | 仅对API33 stub核dynsym；本组9名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=oh；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-021](#native-021) libicu.so：当时缺口 | 缺口 / historical | 仅对API33 stub核dynsym；本组306名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-022](#native-022) libjnigraphics.so：当时缺口 | 缺口 / historical | 仅对API33 stub核dynsym；本组36名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有36名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-023](#native-023) libjnigraphics.so：当时导出，功能未知 | 未知 / historical | 仅对API33 stub核dynsym；本组3名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=westlake；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-024](#native-024) liblog.so：当时导出，功能未知 | 未知 / historical | 仅对API33 stub核dynsym；本组18名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=westlake；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-025](#native-025) libm.so：当时缺口 | 缺口 / historical | 仅对API33 stub核dynsym；本组9名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-026](#native-026) libm.so：当时导出，功能未知 | 未知 / historical | 仅对API33 stub核dynsym；本组277名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=oh；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-027](#native-027) libmediandk.so：当时缺口 | 缺口 / historical | 仅对API33 stub核dynsym；本组287名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-028](#native-028) libmediandk.so：当时导出，功能未知 | 未知 / historical | 仅对API33 stub核dynsym；本组13名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=westlake；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-029](#native-029) libnativehelper.so：当时导出，功能未知 | 未知 / historical | 仅对API33 stub核dynsym；本组6名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=westlake；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-030](#native-030) libnativewindow.so：当时缺口 | 缺口 / historical | 仅对API33 stub核dynsym；本组5名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-031](#native-031) libnativewindow.so：当时导出，功能未知 | 未知 / historical | 仅对API33 stub核dynsym；本组21名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=westlake；source-build另profile有4名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-032](#native-032) libneuralnetworks.so：当时缺口 | 缺口 / historical | 仅对API33 stub核dynsym；本组69名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-033](#native-033) libstdc++.so：当时缺口 | 缺口 / historical | 仅对API33 stub核dynsym；本组12名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有12名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-034](#native-034) libstdc++.so：当时导出，功能未知 | 未知 / historical | 仅对API33 stub核dynsym；本组1名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=westlake；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-035](#native-035) libsync.so：当时缺口 | 缺口 / historical | 仅对API33 stub核dynsym；本组3名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有3名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-036](#native-036) libvulkan.so：当时缺口 | 缺口 / historical | 仅对API33 stub核dynsym；本组3名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-037](#native-037) libvulkan.so：当时导出，功能未知 | 未知 / historical | 仅对API33 stub核dynsym；本组229名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=oh；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-038](#native-038) libz.so：当时导出，功能未知 | 未知 / historical | 仅对API33 stub核dynsym；本组93名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=oh；source-build另profile有0名改变供应，不合并为今日成功。 | NDK r25符号stub，不是方法体 / OH: unknown / 路由与代际: 2026-09-21 legacy / source-build两种profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。 |
| [NATIVE-039](#native-039) android.app.Activity：nullptr | 占位/降级 / historical | 兼容降级/占位组=nullptr；原声明示例：android.app.Activity.getDlWarning ()Ljava/lang/String; \| :30 \| nullptr \| "OH musl has no android_dlwarning; null = no warnings"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-040](#native-040) android.database.CursorWindow：unsupported | 占位/降级 / historical | 兼容降级/占位组=unsupported；原声明示例：android.database.CursorWindow.nativeCreateFromParcel (Landroid/os/Parcel;)J \| :118 \| 0 (throws UnsupportedOperationException) \| "Binder marshalling stubbed; path unused; throw if reached"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-041](#native-041) android.graphics.BLASTBufferQueue：0 | 占位/降级 / historical | 兼容降级/占位组=0；原声明示例：android.graphics.BLASTBufferQueue.nativeGetLastAcquiredFrameNum (J)J \| BBQ_nativeGetLastAcquiredFrameNum \| :653 \| 0 \| -。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-042](#native-042) android.graphics.BLASTBufferQueue：JNI_FALSE | 占位/降级 / historical | 兼容降级/占位组=JNI_FALSE；原声明示例：android.graphics.BLASTBufferQueue.nativeSyncNextTransaction (JLjava/util/function/Consumer;Z)Z \| BBQ_nativeSyncNextTransaction \| :647 \| JNI_FALSE \| "OH queue has no SF transaction-acquisition callback; report none armed"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-043](#native-043) android.graphics.BLASTBufferQueue：void | 占位/降级 / historical | 兼容降级/占位组=void；原声明示例：android.graphics.BLASTBufferQueue.nativeStopContinuousSyncTransaction (J)V \| BBQ_nativeStopContinuousSyncTransaction \| :650 \| void \| -。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-044](#native-044) android.graphics.BLASTBufferQueue：固定/占位/有损返回 | 占位/降级 / historical | 兼容降级/占位组=固定/占位/有损返回；原声明示例：android.graphics.BLASTBufferQueue.nativeGatherPendingTransactions (JJ)Landroid/view/SurfaceControl$Transaction; \| BBQ_nativeGatherPendingTransactions \| :655 \| new empty Transaction \| "return a live Transaction wrapper; no pending SF tx in OH"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-045](#native-045) android.graphics.HardwareRenderer：0 | 占位/降级 / historical | 兼容降级/占位组=0；原声明示例：android.graphics.HardwareRenderer.nGetRenderThreadTid (J)I \| HRN_zero_j \| :876 \| 0 \| "proxy-handle natives no-op"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。; NEUTER仅OHUB_VARIANT/OHUB_UNITY_LIBDIR门控，不能泛化到整个runtime的HWUI实现。 |
| [NATIVE-046](#native-046) android.graphics.HardwareRenderer：JNI_FALSE | 占位/降级 / historical | 兼容降级/占位组=JNI_FALSE；原声明示例：android.graphics.HardwareRenderer.nLoadSystemProperties (J)Z \| HRN_false_j \| :873 \| JNI_FALSE \| "proxy-handle natives no-op"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。; NEUTER仅OHUB_VARIANT/OHUB_UNITY_LIBDIR门控，不能泛化到整个runtime的HWUI实现。 |
| [NATIVE-047](#native-047) android.graphics.HardwareRenderer：JNI_TRUE | 占位/降级 / historical | 兼容降级/占位组=JNI_TRUE；原声明示例：android.graphics.HardwareRenderer.nIsDrawingEnabled ()Z \| HRN_true0 \| :875 \| JNI_TRUE \| "proxy-handle no-op"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。; NEUTER仅OHUB_VARIANT/OHUB_UNITY_LIBDIR门控，不能泛化到整个runtime的HWUI实现。 |
| [NATIVE-048](#native-048) android.graphics.HardwareRenderer：void | 占位/降级 / historical | 兼容降级/占位组=void；原声明示例：android.graphics.HardwareRenderer.nDeleteProxy (J)V \| HRN_v1 \| :868 \| void \| "RenderThread birth"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。; NEUTER仅OHUB_VARIANT/OHUB_UNITY_LIBDIR门控，不能泛化到整个runtime的HWUI实现。 |
| [NATIVE-049](#native-049) android.graphics.HardwareRenderer：固定/占位/有损返回 | 占位/降级 / historical | 兼容降级/占位组=固定/占位/有损返回；原声明示例：android.graphics.HardwareRenderer.nCreateRootRenderNode ()J \| HRN_make \| :870 \| 1L \| "RenderThread birth load-bearing entries: no proxy => no RenderThread"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。; NEUTER仅OHUB_VARIANT/OHUB_UNITY_LIBDIR门控，不能泛化到整个runtime的HWUI实现。 |
| [NATIVE-050](#native-050) android.graphics.ImageDecoder：nullptr | 占位/降级 / historical | 兼容降级/占位组=nullptr；原声明示例：android.graphics.ImageDecoder.nGetColorSpace (J)Landroid/graphics/ColorSpace; \| ID_nGetColorSpace \| :79 \| nullptr \| "libhwui caches gColorSpace jfieldID; when it fails (framework.jar layout) fid stays null -> CheckJNI abort. Override: return null; sRGB assumed when null" [ASSUMPTION REFUTED by fd-musicplayer -- but mus。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-051](#native-051) android.graphics.ImageDecoder：void | 占位/降级 / historical | 兼容降级/占位组=void；原声明示例：android.graphics.ImageDecoder.nClose (J)V \| ID_nClose \| :109 \| void \| "stub remaining ImageDecoder natives; HelloWorld doesn't decode images"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-052](#native-052) android.graphics.ImageDecoder：固定/占位/有损返回 | 占位/降级 / historical | 兼容降级/占位组=固定/占位/有损返回；原声明示例：android.graphics.ImageDecoder.nGetPadding (JLandroid/graphics/Rect;)V \| ID_nGetPadding \| :87 \| void (outRect unchanged) \| "same fid/jclass cache problem; libhwui IsInstanceOf on null gNinePatchInsetsClass -> abort. leave outRect (0,0,0,0)"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-053](#native-053) android.graphics.Typeface：0 | 占位/降级 / historical | 兼容降级/占位组=0；原声明示例：android.graphics.Typeface.nativeGetStyle (J)I \| :73 \| 0 \| same。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-054](#native-054) android.graphics.Typeface：nullptr | 占位/降级 / historical | 兼容降级/占位组=nullptr；原声明示例：android.graphics.Typeface.nativeGetSupportedAxes (J)[I \| :71 \| nullptr \| "safe defaults, non-functional but non-crashing at ctor time"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-055](#native-055) android.graphics.Typeface：void | 占位/降级 / historical | 兼容降级/占位组=void；原声明示例：android.graphics.Typeface.nativeSetDefault (J)V \| :72 \| void \| same。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-056](#native-056) android.graphics.Typeface：固定/占位/有损返回 | 占位/降级 / historical | 兼容降级/占位组=固定/占位/有损返回；原声明示例：android.graphics.Typeface.nativeCreateFromTypeface (JI)J \| :66 \| 1L (kFakeTypefaceHandle) \| "Return non-zero fake handle so Typeface ctor accepts (rejects 0 with RuntimeException); same handle reused -> non-functional rendering"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-057](#native-057) android.hardware.SystemSensorManager：0 | 占位/降级 / historical | 兼容降级/占位组=0；原声明示例：android.hardware.SystemSensorManager.nativeCreateDirectChannel (...)I \| :93 \| 0 \| "no channel / unsupported"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-058](#native-058) android.hardware.SystemSensorManager：JNI_FALSE | 占位/降级 / historical | 兼容降级/占位组=JNI_FALSE；原声明示例：android.hardware.SystemSensorManager.nativeGetSensorAtIndex (JLandroid/hardware/Sensor;I)Z \| :74 \| JNI_FALSE \| "false ends enumeration loop -> empty sensor list"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-059](#native-059) android.hardware.SystemSensorManager：void | 占位/降级 / historical | 兼容降级/占位组=void；原声明示例：android.hardware.SystemSensorManager.nativeClassInit ()V \| :64 \| void \| "no Sensor field-ID caching; never populate a Sensor"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-060](#native-060) android.hardware.SystemSensorManager：固定/占位/有损返回 | 占位/降级 / historical | 兼容降级/占位组=固定/占位/有损返回；原声明示例：android.hardware.SystemSensorManager.nativeCreate (Ljava/lang/String;)J \| :69 \| 1 (sentinel) \| "non-zero sentinel; never dereferenced"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-061](#native-061) android.hardware.SystemSensorManager$BaseEventQueue：0 | 占位/降级 / historical | 兼容降级/占位组=0；原声明示例：android.hardware.SystemSensorManager$BaseEventQueue.nativeEnableSensor (JIII)I \| :124 \| 0 \| "never reached with zero sensors"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-062](#native-062) android.hardware.SystemSensorManager$BaseEventQueue：void | 占位/降级 / historical | 兼容降级/占位组=void；原声明示例：android.hardware.SystemSensorManager$BaseEventQueue.nativeDestroySensorEventQueue (J)V \| :133 \| void \| -。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-063](#native-063) android.hardware.SystemSensorManager$BaseEventQueue：固定/占位/有损返回 | 占位/降级 / historical | 兼容降级/占位组=固定/占位/有损返回；原声明示例：android.hardware.SystemSensorManager$BaseEventQueue.nativeInitBaseEventQueue (...)J \| :117 \| 1 (sentinel) \| -。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-064](#native-064) android.media.AudioSystem：0 | 占位/降级 / historical | 兼容降级/占位组=0；原声明示例：android.media.AudioSystem.newAudioSessionId ()I \| :34 \| 0 \| "0 = AUDIO_UNIQUE_ID_ALLOCATE; no AudioFlinger"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-065](#native-065) android.media.AudioSystem：固定/占位/有损返回 | 占位/降级 / historical | 兼容降级/占位组=固定/占位/有损返回；原声明示例：android.media.AudioSystem.native_getMaxChannelCount ()I \| :10 \| 2 \| "D600 route stereo; smallest truthful value for FMOD CHANNEL_OUT_STEREO"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-066](#native-066) android.media.AudioTrack：void | 占位/降级 / historical | 兼容降级/占位组=void；原声明示例：android.media.AudioTrack.native_setPlayerIId (I)V \| :202 \| void \| -。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-067](#native-067) android.media.AudioTrack：固定/占位/有损返回 | 占位/降级 / historical | 兼容降级/占位组=固定/占位/有损返回；原声明示例：android.media.AudioTrack.native_get_output_sample_rate (I)I \| :112 \| 48000 \| -。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-068](#native-068) android.media.MediaPlayer：无codec/空值/假状态 | 占位/降级 / historical | 兼容降级/占位组=无codec/空值/假状态；原声明示例：#  getVideoWidth:312=0 getVideoHeight:313=0 getCurrentPosition:314=0 getDuration:315=0 getAudioSessionId:316=0 isLooping:317=FALSE。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-069](#native-069) android.media.audiopolicy.AudioProductStrategy：固定/占位/有损返回 | 占位/降级 / historical | 兼容降级/占位组=固定/占位/有损返回；原声明示例：android.media.audiopolicy.AudioProductStrategy.native_list_audio_product_strategies (Ljava/util/ArrayList;)I \| :24 \| 0 (empty) \| "no audio-policy service; empty -> AudioAttributes DEFAULT fallback"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-070](#native-070) android.opengl.EGL14：unsupported | 占位/降级 / historical | 兼容降级/占位组=unsupported；原声明示例：android.opengl.EGL14.eglCreatePixmapSurface (...)Landroid/opengl/EGLSurface; \| :738 \| throws UnsupportedOperationException, nullptr \| -。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-071](#native-071) android.os.Binder：0 | 占位/降级 / historical | 兼容降级/占位组=0；原声明示例：android.os.Binder.clearCallingIdentity ()J \| :86 \| 0。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-072](#native-072) android.os.Binder：JNI_FALSE | 占位/降级 / historical | 兼容降级/占位组=JNI_FALSE；原声明示例：android.os.Binder.isDirectlyHandlingTransaction ()Z \| :84 \| JNI_FALSE。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-073](#native-073) android.os.Binder：void | 占位/降级 / historical | 兼容降级/占位组=void；原声明示例：android.os.Binder.restoreCallingIdentity (J)V \| :87 \| void。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-074](#native-074) android.os.Binder：固定/占位/有损返回 | 占位/降级 / historical | 兼容降级/占位组=固定/占位/有损返回；原声明示例：android.os.Binder.getCallingWorkSourceUid ()I \| :91 \| -1。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-075](#native-075) android.os.Debug：固定/占位/有损返回 | 占位/降级 / historical | 兼容降级/占位组=固定/占位/有损返回；原声明示例：android.os.Debug.getMemoryInfo (Landroid/os/Debug$MemoryInfo;)V \| :58 \| void (MemoryInfo left zeroed) \| "no PSS/smaps backing on OH"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-076](#native-076) android.os.GraphicsEnvironment：JNI_FALSE | 占位/降级 / historical | 兼容降级/占位组=JNI_FALSE；原声明示例：android.os.GraphicsEnvironment.isDebuggable ()Z \| :24 \| JNI_FALSE \| "non-debug build -> production path, no debug GLES layers"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-077](#native-077) android.os.GraphicsEnvironment：JNI_TRUE | 占位/降级 / historical | 兼容降级/占位组=JNI_TRUE；原声明示例：android.os.GraphicsEnvironment.setInjectLayersPrSetDumpable ()Z \| :41 \| JNI_TRUE \| "caller treats failure as ok"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-078](#native-078) android.os.GraphicsEnvironment：void | 占位/降级 / historical | 兼容降级/占位组=void；原声明示例：android.os.GraphicsEnvironment.setLayerPaths/setDebugLayers/setDebugLayersGLES/setDriverPathAndSphalLibraries/setGpuStats/setAngleInfo/nativeToggleAngleAsSystemDriver/hintActivityLaunch (...)V \| :27-45 \| void \| "no-op" [8 no-ops]。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-079](#native-079) android.os.MessageQueue：void | 占位/降级 / historical | 兼容降级/占位组=void；原声明示例：android.os.MessageQueue.nativeSetFileDescriptorEvents (JII)V \| :128 \| void \| "HelloWorld doesn't install custom fd watchers"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-080](#native-080) android.os.Parcel：0 | 占位/降级 / historical | 兼容降级/占位组=0；原声明示例：android.os.Parcel.getGlobalAllocSize ()J \| :520 \| 0 \| "process-wide stats -> zeros"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-081](#native-081) android.os.Parcel：JNI_FALSE | 占位/降级 / historical | 兼容降级/占位组=JNI_FALSE；原声明示例：android.os.Parcel.nativeHasFileDescriptors (J)Z \| :560 \| JNI_FALSE \| -。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-082](#native-082) android.os.Parcel：nullptr | 占位/降级 / historical | 兼容降级/占位组=nullptr；原声明示例：android.os.Parcel.nativeReadStrongBinder (J)Landroid/os/IBinder; \| :541 \| nullptr \| "consume placeholder"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-083](#native-083) android.os.Parcel：void | 占位/降级 / historical | 兼容降级/占位组=void；原声明示例：android.os.Parcel.nativeEnforceInterface (JLjava/lang/String;)V \| :574 \| void \| "silently accept; AIDL-stub not routed to OH IPC"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-084](#native-084) android.os.Parcel：固定/占位/有损返回 | 占位/降级 / historical | 兼容降级/占位组=固定/占位/有损返回；原声明示例：android.os.Parcel.nativeMarkForBinder (JLandroid/os/IBinder;)V \| :529 \| void (warn-only) \| -。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-085](#native-085) android.os.SystemProperties：0 | 占位/降级 / historical | 兼容降级/占位组=0；原声明示例：android.os.SystemProperties.native_find (Ljava/lang/String;)J \| :192 \| 0 \| "find returns opaque handle, 0=not found"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-086](#native-086) android.os.SystemProperties：defVal | 部分实现 / historical | 兼容降级/占位组=defVal；原声明示例：android.os.SystemProperties.native_get_int (JI)I \| :205 \| defVal \| same。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-087](#native-087) android.os.SystemProperties：void | 占位/降级 / historical | 兼容降级/占位组=void；原声明示例：android.os.SystemProperties.native_set (Ljava/lang/String;Ljava/lang/String;)V \| :222 \| void \| "OH has no process-writable property store; writes dropped"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-088](#native-088) android.os.SystemProperties：固定/占位/有损返回 | 占位/降级 / historical | 兼容降级/占位组=固定/占位/有损返回；原声明示例：android.os.SystemProperties.native_get (J)Ljava/lang/String; \| :200 \| empty string \| "handle variants always get handle=0"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-089](#native-089) android.util.EventLog：void | 占位/降级 / historical | 兼容降级/占位组=void；原声明示例：android.util.EventLog.readEventsOnWrapping ([IJLjava/util/Collection;)V \| :244 \| void \| same。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-090](#native-090) android.util.EventLog：固定/占位/有损返回 | 占位/降级 / historical | 兼容降级/占位组=固定/占位/有损返回；原声明示例：android.util.EventLog.readEvents ([ILjava/util/Collection;)V \| :238 \| void (Collection unchanged) \| "no event channel on OH"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-091](#native-091) android.view.DisplayEventReceiver：0 | 占位/降级 / historical | 兼容降级/占位组=0；原声明示例：android.view.DisplayEventReceiver.nativeGetDisplayEventReceiverFinalizer ()J \| DER_nativeGetDisplayEventReceiverFinalizer \| :523 \| 0 \| "previously returned 0 (feeds NAR(0) crash via ART intrinsic). Real DER_release caused regression; TODO P1 real release fn" [HAZARD: a 0 finalizer handed to NativeAllocationRegistry.app。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-092](#native-092) android.view.InputChannel：nullptr | 占位/降级 / historical | 兼容降级/占位组=nullptr；原声明示例：android.view.InputChannel.nativeGetToken (J)Landroid/os/IBinder; \| IC_nativeGetToken \| :224 \| nullptr \| "no InputDispatcher; Java callers null-check (ViewRootImpl.setView)"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-093](#native-093) android.view.InputChannel：void | 占位/降级 / historical | 兼容降级/占位组=void；原声明示例：android.view.InputChannel.nativeWriteToParcel (Landroid/os/Parcel;J)V \| IC_nativeWriteToParcel \| :195 \| void \| "read side allocates fresh"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-094](#native-094) android.view.InputChannel：固定/占位/有损返回 | 占位/降级 / historical | 兼容降级/占位组=固定/占位/有损返回；原声明示例：android.view.InputChannel.nativeReadFromParcel (Landroid/os/Parcel;)J \| IC_nativeReadFromParcel \| :185 \| placeholder OhInputChannel* \| "channels not Parcel-transported in adapter; alloc fresh placeholder so nativeGetName/Dispose work"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-095](#native-095) android.view.InputEventReceiver：JNI_FALSE | 占位/降级 / historical | 兼容降级/占位组=JNI_FALSE；原声明示例：android.view.InputEventReceiver.nativeConsumeBatchedInputEvents (JJ)Z \| IER_nativeConsumeBatchedInputEvents \| :856 \| JNI_FALSE \| "no frame-time batching; one-per-MOVE; jank acceptable"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-096](#native-096) android.view.InputEventReceiver：void | 占位/降级 / historical | 兼容降级/占位组=void；原声明示例：android.view.InputEventReceiver.nativeReportTimeline (JIJJ)V \| IER_nativeReportTimeline \| android_view_InputEventReceiver.cpp:850 \| void \| "Choreographer FrameInfo timeline; not needed for input"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-097](#native-097) android.view.InputEventReceiver：固定/占位/有损返回 | 占位/降级 / historical | 兼容降级/占位组=固定/占位/有损返回；原声明示例：android.view.InputEventReceiver.nativeDump (JLjava/lang/String;)Ljava/lang/String; \| IER_nativeDump \| :863 \| empty string \| -。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-098](#native-098) android.view.KeyCharacterMap：0 | 占位/降级 / historical | 兼容降级/占位组=0；原声明示例：android.view.KeyCharacterMap.nativeGetCharacter (JII)C \| :163 \| 0 \| "mMap permanently nullptr"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-099](#native-099) android.view.KeyCharacterMap：false | 占位/降级 / historical | 兼容降级/占位组=false；原声明示例：android.view.KeyCharacterMap.nativeGetFallbackAction (JIILandroid/view/KeyCharacterMap$FallbackAction;)Z \| :174 \| false \| -。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-100](#native-100) android.view.KeyCharacterMap：void | 占位/降级 / historical | 兼容降级/占位组=void；原声明示例：android.view.KeyCharacterMap.nativeWriteToParcel (JLandroid/os/Parcel;)V \| :151 \| void \| same。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-101](#native-101) android.view.KeyCharacterMap：固定/占位/有损返回 | 占位/降级 / historical | 兼容降级/占位组=固定/占位/有损返回；原声明示例：android.view.KeyCharacterMap.nativeReadFromParcel (Landroid/os/Parcel;)J \| :143 \| placeholder NativeKeyCharacterMap* \| "no cross-proc KCM Parcel; fresh empty so Dispose works"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-102](#native-102) android.view.MotionEvent：unsupported | 占位/降级 / historical | 兼容降级/占位组=unsupported；原声明示例：android.view.MotionEvent.nativeReadFromParcel (JLandroid/os/Parcel;)J \| :379 \| throws UnsupportedOperationException, 0 \| "MotionEvent Parcel I/O not implemented in Phase 1"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-103](#native-103) android.view.Surface：0 | 占位/降级 / historical | 兼容降级/占位组=0；原声明示例：android.view.Surface.nativeCreateFromSurfaceTexture (Landroid/graphics/SurfaceTexture;)J \| S_nativeCreateFromSurfaceTexture \| :189 \| 0 \| "HelloWorld doesn't use SurfaceTexture; return 0"。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | fd-plus [reported] ac59历史Surface was not locked失败；不是修复成功; fd-plus [reported] ac59历史首致命点：nativeLockCanvas返回0→Surface未lock ISE；r86 source-build后期实现分NATIVE-142，不能覆写本历史桩。 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-104](#native-104) android.view.Surface：JNI_FALSE | 占位/降级 / historical | 兼容降级/占位组=JNI_FALSE；原声明示例：android.view.Surface.nativeIsConsumerRunningBehind (J)Z \| S_nativeIsConsumerRunningBehind \| :212 \| JNI_FALSE \| -。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-105](#native-105) android.view.Surface：void | 占位/降级 / historical | 兼容降级/占位组=void；原声明示例：android.view.Surface.nativeRelease (J)V \| S_nativeRelease \| :208 \| void \| -。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-106](#native-106) android.view.Surface：固定/占位/有损返回 | 占位/降级 / historical | 兼容降级/占位组=固定/占位/有损返回；原声明示例：android.view.Surface.nativeReadFromParcel (JLandroid/os/Parcel;)J \| S_nativeReadFromParcel \| :215 \| nativeObject (parcel ignored) \| -。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-107](#native-107) android.view.SurfaceControl：returns 0 / empty (3) | 占位/降级 / historical | 兼容降级/占位组=returns 0 / empty (3)；原声明示例：# returns 0 / empty (3): nativeGetTransformHint:445(0=IDENTITY) nativeGetGPUContextPriority:634(0) nativeCreateJankDataListenerWrapper:630(0 null-token) nativeGetCompositionDataspaces:643(empty int[])。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-108](#native-108) android.view.SurfaceControl：returns JNI_FALSE (8) | 占位/降级 / historical | 兼容降级/占位组=returns JNI_FALSE (8)；原声明示例：# returns JNI_FALSE (8): nativeGetBootDisplayModeSupport:592 nativeSetActiveColorMode:535 nativeSetDesiredDisplayModeSpecs:538 nativeSetDisplayBrightness:541 nativeGetDisplayBrightnessSupport:544 nativeSetDisplayedContentSamplingEnabled:547 nativeGetProtectedContentSupport:640。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-109](#native-109) android.view.SurfaceControl：returns JNI_TRUE (5, "always succeeded/booted") | 占位/降级 / historical | 兼容降级/占位组=returns JNI_TRUE (5, "always succeeded/booted")；原声明示例：# returns JNI_TRUE (5, "always succeeded/booted"): nativeClearContentFrameStats:385 nativeGetContentFrameStats:386 nativeClearAnimationFrameStats:387 nativeGetAnimationFrameStats:388 nativeBootFinished:622。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-110](#native-110) android.view.SurfaceControl：returns nullptr (7) | 占位/降级 / historical | 兼容降级/占位组=returns nullptr (7)；原声明示例：# returns nullptr (7): nativeGetDisplayedContentSample:550 nativeGetDisplayDecorationSupport:553 nativeGetDisplayNativePrimaries:556 nativeGetDynamicDisplayInfo:559 nativeGetStaticDisplayInfo:562 nativeGetOverlaySupport:637 nativeGetDefaultApplyToken:647。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-111](#native-111) android.view.SurfaceControl：returns void log-only (22) | 占位/降级 / historical | 兼容降级/占位组=returns void log-only (22)；原声明示例：# returns void log-only (22): nativeSetLayerStack:472 nativeSetTransformHint:480 nativeSetMetadata:487 nativeAddWindowInfosReportedListener:510 nativeSetFixedTransformHint:526 nativeSanitize:615 nativeSetFocusedWindow:603 nativeSetInputWindowInfo:607 nativeSetGameContentType:596 nativeSetAutoLowLatencyMode:599 nativeSe。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-112](#native-112) android.view.SurfaceControl：returns void no-op (28) | 占位/降级 / historical | 兼容降级/占位组=returns void no-op (28)；原声明示例：# returns void no-op (28): nativeSetShadowRadius:419 nativeSetFrameRate:425 nativeSetTrustedOverlay:371 nativeSurfaceFlushJankData:373 nativeSetRelativeLayer:278 nativeSetTransparentRegionHint:293 nativeSetColorTransform:304 nativeSetColorSpaceAgnostic:418 nativeSetBlurRegions:368 nativeSetStretchEffect:369 nativeSetFr。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-113](#native-113) com.android.internal.os.BinderInternal：nullptr | 占位/降级 / historical | 兼容降级/占位组=nullptr；原声明示例：com.android.internal.os.BinderInternal.getContextObject ()Landroid/os/IBinder; \| :102 \| nullptr。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-114](#native-114) com.android.internal.os.BinderInternal：void | 占位/降级 / historical | 兼容降级/占位组=void；原声明示例：com.android.internal.os.BinderInternal.handleGc ()V \| :103 \| void。回退不能冒充真实硬件/Android服务。 | unknown / OH: unknown / 路由与代际: 2026-10-02 census / ac59历史profile | 无直接 APK 验证记录 | 本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。; 原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。 |
| [NATIVE-115](#native-115) SQLiteConnection 真实JNI→sqlite3 | 已实现 / historical | U13编入android_database_SQLiteConnection.cpp真实TU，注册27方法并走sqlite3，不是Boat的弱return0 registrar；JNI注册完整不保证文件权限、CANTOPEN或所有SQL语义。 | android-14.0.0_r1（源码证据，不是Android对照机） / OH: unknown / 路由与代际: U13 18763dd4 | com.Unity3d.BoatAttackDay [static] 静态对照：Boat adc错放runtime无SQLiteConnection真实注册，U13 18763dd4含27方法。Boat五触摸/LAP历史成功不能验证SQLite；本行没有该APK真实开库成功证据。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。 |
| [NATIVE-116](#native-116) CursorWindow本进程缓存与SQLiteGlobal/Debug | 已实现 / historical | U13 21/1/1表包含本地窗口和SQLite操作；Parcel跨进程两方法仍另列stub，不把IPC无实现藏进真实窗口行。 | unknown / OH: unknown / 路由与代际: U13 18763dd4 | com.Unity3d.BoatAttackDay [static] 静态对照：U13含CursorWindow/Global/Debug的21/1/1表，adc对应弱return0；没有从Boat渲染成功推IPC或数据库功能。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。 |
| [NATIVE-117](#native-117) Boat覆盖runtime导致SQLite真实注册缺失 | 缺口 / historical | adc125f4是libandroid9ccf49字节改件被别名放到runtime；四registrar弱return0替代真实TU，无nativeOpen；349表差/520导出差不是APK挡住数。 | unknown / OH: unknown / 路由与代际: Boat adc125f4 vs U13 18763dd4 | com.Unity3d.BoatAttackDay [reported] 历史Boat图形五触摸/LAP可过；共享路径却被adc替换，四SQLite registrar为空且nativeOpen表缺失；SQLite兼容性未过。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。 |
| [NATIVE-118](#native-118) NDK CPU lock/post真实队列与fence适配 | 已实现 / candidate | 8728134a小shim引用唯一runtime和libsurface.z；oh_anw_get_oh解包、usage3/dequeue、BufferHandle真实映射、fence等待/失败取消、mutex保护。报告行为夹具过，不等于21消费者全部亮。 | unknown / OH: unknown / 路由与代际: U11 candidate 8728134a | 无直接 APK 验证记录 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。 |
| [NATIVE-119](#native-119) 跨拷贝NativeWindow反查M1 | 部分实现 / candidate | M1通过runtime导出/遍历已映射拷贝反查窗口；t4拆成m1_copy TU，PLT可抢占；1d42相对94c3仅既定变化，单owner和FZ-009复验必须按具体bundle。 | unknown / OH: unknown / 路由与代际: U16 candidate1d42dbfb / U15 94c31177 | 无直接 APK 验证记录 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。 |
| [NATIVE-120](#native-120) U14对话子窗口Z序与finish后后台 | 部分实现 / candidate | bridge7daa5435的M5/M6仅改对应窗口函数；ddmodel2是否移动依赖runtime M1，不用旧无M1预测替代U14结果。 | unknown / OH: unknown / 路由与代际: U14 bridge7daa5435 / runtime18763dd4 | 无直接 APK 验证记录 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。 |
| [NATIVE-121](#native-121) Flutter proc-address窗口解包钩子 | 已实现 / candidate | eb90a640先返回自身4个EGL窗口/surface包装，再委托平台resolver；是ANW转接不是GPU实现；只westlake_flutter槽，不改westlake_native。 | unknown / OH: unknown / 路由与代际: U16 A‴eb90a640 vs U15 9b824502 | 无直接 APK 验证记录 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。 |
| [NATIVE-122](#native-122) Bitmap JNI真实owner与空ColorSpace边界 | 部分实现 / historical | 真实JNI在libhwui be59260f，nativeComputeColorSpace注册与AOSP14对应但源bitmap的SkColorSpace可真实为null；不是runtime漏注册，后续Java sRGB隐式fallback归java分片。 | AOSP14 Bitmap.cpp 对照 / OH: unknown / 路由与代际: U13/U12 libhwui be59260f | privacybrowser [reported] U13/5ea缩放favicon时Bitmap.createBitmap抛can't create bitmap without a color space；nativeComputeColorSpace真实注册但源SkColorSpace=null；不是漏JNI。; fd-musicplayer [reported] U12/5cd缩放album-art同一ColorSpace IAE为终止点；MediaStore Artists NCDFE来自背景线程，不用它替代主线程死因。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。 |
| [NATIVE-123](#native-123) AMedia状态API合法unsupported边界 | 占位/降级 / candidate | 50实际Unity导入拆成13行为组；本行仅21个status型unsupported接口，返回AOSP合法AMEDIA_ERROR_UNSUPPORTED=-10002且清输出；AMediaFormat/DataSource小容器的真实分配/读写/释放另行列，不将50个全称空桩。无Codec/Stagefright/OH解码引擎。 | android-14.0.0_r1 frameworks/av 402dbe885fd58af75e4c1d7e790fbf4bb22f29f9 / OH: unknown / 路由与代际: U12 candidate8fc0752d | subwaysurfers [static] libunity.so静态导入本行members（AMediaFormat_new为候选额外container接口）；8fc provider可覆盖名称与类型。没有新解码/播放/首屏证据，已证该候选新亮0。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。 |
| [NATIVE-124](#native-124) Android↔OH整数宽度与IID真实转接原语 | 已实现 / candidate | 移植四上游commit的结构/队列算法，Android32 vs OH64与16↔24字节IID字段换算、continuous queue有夹具；route-A真实backend注入/单owner准入尚未证。 | unknown / OH: unknown / 路由与代际: U12 offline primitives / OH owner05d8ac90 | 无直接 APK 验证记录 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。 |
| [NATIVE-125](#native-125) PLAY completion及回调尚无真实实现 | 缺口 / historical | 现役OH05d8两方法返回12 FEATURE_UNSUPPORTED；上游c7d2992仍委托OH PLAY，原样抄不能解除墙；真实AudioRenderer completion未交，不把ledger成功当该route成功。 | unknown / OH: unknown / 路由与代际: U10.1/U12 OH05d8 owner | mindustry [static] OH owner 05d8的PLAY RegisterCallback/SetCallbackEventsMask返回12；c7d2992仍原样委托，不能以移植上游或ABI测试声称此墙已移走。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。 |
| [NATIVE-126](#native-126) Android _ctype_指针与257字节原表 | 已实现 / candidate | AOSP原ctype_.c无改表；8字节GLOBAL指针指LOCAL257字节EOF+ASCII表，不导出裸数组。b8a87源/ELF表逐字等，符号存在不保证Realm relocation scope。 | android-14.0.0_r1 bionic e4df46f213d8d363017dce7ded5d1f2159614425 / OH: unknown / 路由与代际: U13 compat-v2 b8a87f6f | mcdonalds [static] librealmc.so实际需要8字节_ctype_指针；候选257字节表与AOSP逐字等、全UND静态核对；scope仍未由这个候选的APK启动证明。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。 |
| [NATIVE-127](#native-127) strtoll_l/strtoull_l locale包装 | 已实现 / candidate | 按AOSP stdlib_l委托strtoll/strtoull且忽略locale，保留endptr/base/ERANGE；不是改变全进程locale。候选b2be657c与resident scope分开。 | AOSP14r1 stdlib_l.cpp:49/57 / OH: unknown / 路由与代际: U12 compat b2be657c | vlc [reported] 窗口5终止证据是strtoll_l/strtoull_l及cleanup缺口；b2be4方法有离线行为测试与消费闭包，预测移走1首致命点，已证移动0。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。 |
| [NATIVE-128](#native-128) cleanup push/pop记录布局真实翻译 | 已实现 / candidate | Android/OH都24字节但字段序不同，转换后使用OH真实cleanup栈，覆盖pthread_exit；不以TLS-only no-op冒认。 | AOSP14r1 pthread_exit.cpp，NDK23仅布局参考 / OH: unknown / 路由与代际: U12 compat b2be657c | vlc [reported] 同一VLC缺符号簇；真实cleanup栈包装经过离线pthread_exit路径，尚无该候选VLC进程成功退出/播放的功能证据。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。 |
| [NATIVE-129](#native-129) errno及cmsg辅助函数新增候选 | 已实现 / candidate | 4698c0a5加两导出；015aa基座__errno为LOCAL且cmsg缺失，不能由源map臆测动态导出。函数补齐不证明纳入app重定位scope。 | unknown / OH: unknown / 路由与代际: U10.1 015aa3a6 -> candidate4698c0a5 | x [reported] U9符号相关日志实报__errno；新增导出只可能移走此加载点，后续首致命unknown；不能把静态50key算实际挡住。; ooniprobe [reported] U9已签亮仍有__errno加载错误；这是反例，不能将同行报错全部当首致命点。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。 |
| [NATIVE-130](#native-130) dlext仅空flags可用，其他扩展拒绝 | 部分实现 / candidate | weak __loader后端存在才真实转调；NULL extinfo/flags0走dlopen；非零flags缺后端时ENOTSUP+NULL。PPSSPP实际0x200/0x210非空，不能算修复。 | unknown / OH: unknown / 路由与代际: U14 native_abi7605812c复制U10 015aa行为 | ppsspp [static] libppsspp_jni两实际调用extinfo.flags=0x200/0x210；无__loader后端仍ENOTSUP/NULL，预测移动0，普通dlopen忽略flags不合格。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。 |
| [NATIVE-131](#native-131) Gecko LIBC版本入口与fortify/strerror | 部分实现 / candidate | native_abi加真实body和LIBC版本节点，通过consumer静态replay；LIBC_O callback另节点，弱dlext扩展仍拒。GNU strerror使用char* ABI，fortify非法参数可abort不是空桩成功。 | unknown / OH: unknown / 路由与代际: U14 native_abi7605812c | firefox [static] 7605812c闭包按musl序replay：Gecko库除libplugin-container.__libc_init外0 unresolved、无版本差；预测libmozglue加载墙移动，非零dlext可能仍拒，未证整app亮。; fd-fennec_fdroid [static] 7605812c闭包按musl序replay：Gecko库除libplugin-container.__libc_init外0 unresolved、无版本差；预测libmozglue加载墙移动，非零dlext可能仍拒，未证整app亮。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。 |
| [NATIVE-132](#native-132) Realm native域ctype补齐 | 已实现 / candidate | f8619ad5=7605+原ctype一导出，44函数不变；RTLD_GLOBAL native_abi与NEEDED liblog/private libandroid组成实际provider集合。静态replay0missing不是McD/Element整app通过。 | AOSP14r1原ctype表 / OH: unknown / 路由与代际: U14 native_abi f8619ad5 | mcdonalds [static] f8619ad5相对7605仅加_ctype_@@LIBC、44旧函数同；Realm librealmc/librealm-jni重定位replay 0 missing。真实native域已有liblog/private libandroid参与，不能只看compat。; fd-im-vector-app [static] f8619ad5相对7605仅加_ctype_@@LIBC、44旧函数同；Realm librealmc/librealm-jni重定位replay 0 missing。真实native域已有liblog/private libandroid参与，不能只看compat。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。 |
| [NATIVE-133](#native-133) 私有zlib窄路由/别名 | 部分实现 / candidate | N8仅删root libz壳、保留private alias和provider；N10 owner routing按域解析；不把库同名/SONAME同当scope完整或全局默认fallback。 | unknown / OH: unknown / 路由与代际: N8 manifest3dd48299 | fd-im-vector-app [static] N8只改变root/private壳布局；Element仍可能受app域libz搜索与provider可见性影响，N8物理件不能自动证明其NEEDED已解析。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。 |
| [NATIVE-134](#native-134) media_jni映射现驻runtime而非mediandk | 部分实现 / candidate | 棋钟框架clinit先load media_jni再native_init；U12mediandk不能解此manifest墙，须system_libraries绑定常驻runtime并resident-only，真实后续播放未证。 | unknown / OH: unknown / 路由与代际: U13 policy / resident owner路线 | cv2-com-chessclock-android [reported] 窗5 MediaPlayer.<clinit> loadLibrary(media_jni)→native_init的manifest缺失；加libmediandk没有此key受益，真实媒体播放下一墙unknown。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。 |
| [NATIVE-135](#native-135) Jitsi native域双名单与runtime可见 | 部分实现 / candidate | host9e3a与ANLb96a同时加org.jitsi.meet，native_selected+host条件都成立才发布native_abi/runtime；不是另做compat假修，预计过LIBC墙，后续WebRTC未知。 | unknown / OH: unknown / 路由与代际: U15 host9e3ad72e + ANLb96a8991 | fd-meet [static] 两份native_cluster_path与needs_runtime同时加入org.jitsi.meet；fd-meet静态LIBC replay 0缺符号，__register_atfork墙预期移动，WebRTC功能/下一墙unknown。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。 |
| [NATIVE-136](#native-136) 公共库继承与ICU74名→72转接 | 部分实现 / candidate | 341c扩host app共享白名单；9b36 libicuuc新增NEEDED4886shim，7个74后缀tail-branch到72；不能把两个ICU数据目录强换或宣称74全API实现。 | unknown / OH: unknown / 路由与代际: U14 host341c1260 / ICU9b36b989+4886bc5c | toutiao [static] ICU74后缀调用经7符号shim转72；不能把该shim解释成完整ICU74，目录与版本混用风险仍有，未由本候选实证文章/刷新通过。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。 |
| [NATIVE-137](#native-137) Locale UErrorCode零初始化修复 | 部分实现 / candidate | AOSP ScopedIcuLocale.h未初始化UErrorCode；零初始化编译参数在指令层新增err=0。此报告未完整重建libicu_jni（closure blocked）；后续1e206531候选须另绑产物回执，不能用本报告假称库已构建/部署。 | AOSP14r1 ScopedIcuLocale.h / OH: unknown / 路由与代际: U12 ICU修法/后续候选1e206531 | fd-wifianalyzer [reported] U9首致命NPE：String.toUpperCase(Locale)返回null的归因为cc-t3记录；旧source532633d未含03678da，零初始化codegen可修原因，本报告没有重建候选库。; fd-breezyweather [reported] U9Locale.getDisplayCountry返回null→Activity启动NPE；JNI走同一个未初始化err，报告为归因而非该候选APK验证成功。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。 |
| [NATIVE-138](#native-138) Boat v2图形共享层与三私有库 | 部分实现 / candidate | stock18763dd4 + adapter8ab/jar633 + Unity/il2cpp/signal_box，window9历史报告可渲染互动；并不证明共享adapter/jar对128无回退，runtime adc/947不进v2。 | unknown / OH: unknown / 路由与代际: Boat v2 ownership(a) / U13底座 | com.Unity3d.BoatAttackDay [reported] window9历史报告stock runtime+v2桥/JAR：t15/t30/t45渲染、约t95可移动；rehearsal1只证init触发，恢复原始JSON失败；尚无候选重启全128不退步签认。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。 |
| [NATIVE-139](#native-139) r84静态Bionic mutex类型翻译 | 已实现 / historical | Bionic初始化字0x4000/0x8000与musl低位不同；未锁定时转换recursive/errorcheck类型再委托musl，避免sentry递归锁死。 | unknown / OH: unknown / 路由与代际: source-build/host r84 build80 | Discord [reported] 20app mutex实验中首帧62.9s→1.98s；采纳Bionic递归initializer解sentry自锁。; OsmAnd [reported] 负对照：带mutex采纳时abort，无采纳时draw；递归恢复后暴露PROJ数据异常，报告未证明资产拷贝根因；不能称无回退。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; 实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。 |
| [NATIVE-140](#native-140) r84 UnixFileSystem空间查询真实statvfs | 已实现 / historical | missing-natives用libcore statvfs注册替换返回0的openjdk stub；不再使CNN cacheSize<=0。不是U13自动包含该override。 | unknown / OH: unknown / 路由与代际: source-build/host r84 build80 | CNN [reported] getSpace0返回0导致OkHttp maxSize<=0；12app File-space测试改为libcore statvfs后CNN draw；95静态调用app不是95功能验证。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; 实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。 |
| [NATIVE-141](#native-141) r86 Android buffer geometry/CPU lock | 已实现 / historical | source-build shim把SDL geometry按Android语义对适配器窗口实现，报告SDLGames过首帧；与U11 CPU lock和ac59JNI Canvas是不同profile。 | unknown / OH: unknown / 路由与代际: source-build/host r86 builds86–90 | anarchre [reported] r86 Android buffer geometry+按句柄EGL后SDL从此前驱动abort/error-dialog推进至drawing；这是source-build历史报告，不升本轮t20。; diesimu [reported] r86 Android buffer geometry+按句柄EGL后SDL从此前驱动abort/error-dialog推进至drawing；这是source-build历史报告，不升本轮t20。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; 实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。 |
| [NATIVE-142](#native-142) r86 Surface.lockCanvas后期实现 | 已实现 / historical | r86 runtime override新增软件Canvas路径；历史ac59返回0的stub仍保留独立行；本报告未独立钉此build源码/ELF SHA，源码细节unknown。 | unknown / OH: unknown / 路由与代际: source-build/host r86 builds86–90 | 无直接 APK 验证记录 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; r86摘要列出此能力实现，但未逐API提供单APK A/B；validations为空是未归因，不是能力未入表。; 实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。 |
| [NATIVE-143](#native-143) r86 Process.readProcFile补全 | 已实现 / historical | source-build缺失natives补proc文件解析，不把r86新注册回写为U13已有；具体format flags/错误边界需补方法体。 | unknown / OH: unknown / 路由与代际: source-build/host r86 builds86–90 | 无直接 APK 验证记录 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; r86摘要列出此能力实现，但未逐API提供单APK A/B；validations为空是未归因，不是能力未入表。; 实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。 |
| [NATIVE-144](#native-144) r86 legacy Camera注册/兼容边界 | 部分实现 / historical | source-build legacyCamera JNI按无Camera设备给合法回答；注册缺口被补，不是OH有可用Camera HAL，更不保证完整拍摄。 | unknown / OH: unknown / 路由与代际: source-build/host r86 builds86–90 | Open Camera [reported] r84缺legacyCamera/no camera service，后续无camera回答与注册补全后可达view；设备没有Camera能力，未证拍摄功能。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; 实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。 |
| [NATIVE-145](#native-145) r86 LocalSocketImpl后期native实现 | 部分实现 / historical | runtime补缺native实现；注册方法/Android reserved namespace和FD ancillary语义尚未逐个核，不从加载成功推完整LocalSocket兼容。 | unknown / OH: unknown / 路由与代际: source-build/host r86 builds86–90 | 无直接 APK 验证记录 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; r86摘要列出此能力实现，但未逐API提供单APK A/B；validations为空是未归因，不是能力未入表。; 实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。 |
| [NATIVE-146](#native-146) r86 SQLite collations补全 | 已实现 / historical | 后期source-build补SQLite本地化排序规则，与U13真实nativeOpen以及CursorWindow Parcel stub是独立能力；collation全集/locale版本unknown。 | unknown / OH: unknown / 路由与代际: source-build/host r86 builds86–90 | 无直接 APK 验证记录 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; r86摘要列出此能力实现，但未逐API提供单APK A/B；validations为空是未归因，不是能力未入表。; 实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。 |
| [NATIVE-147](#native-147) r86 font iterator真实供给 | 部分实现 / historical | 报告shim补NDK字体列表，使Fennec继续；未记录此组全部字体轴/matcher覆盖或文件格式，精确源码/产物仍unknown。 | unknown / OH: unknown / 路由与代际: source-build/host r86 builds86–90 | Fennec [reported] r86 NDK font list与libmozglue operators/allocator-by-version一起使Fennec到drawing；字体列表独立A/B与font matcher全覆盖尚无。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; 实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。 |
| [NATIVE-148](#native-148) r86 PerformanceHint manager接口 | 部分实现 / historical | 报告shim+runtime hint-manager入口；尚无真实OH调度/功耗效果证据，不把非null manager当性能收益实现。 | unknown / OH: unknown / 路由与代际: source-build/host r86 builds86–90 | 无直接 APK 验证记录 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; r86摘要列出此能力实现，但未逐API提供单APK A/B；validations为空是未归因，不是能力未入表。; 实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。 |
| [NATIVE-149](#native-149) r86枚举已创建运行VM | 已实现 / historical | 回答正在运行的JavaVM而非另建VM，报告ElementX移动；多VM/ABI/当前VM对象生命周期边界未知。 | unknown / OH: unknown / 路由与代际: source-build/host r86 builds86–90 | Element X [reported] r86由正在运行的VM回答JNI_GetCreatedJavaVMs后到drawing；r84 pointer-from-string故障是更早profile，不能借成U13同函数。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; 实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。 |
| [NATIVE-150](#native-150) r86目录遍历fts移植 | 已实现 / historical | 报告补Bionic fts使Emacs native库可载入，随后仍停首Activity；载入不等于整个编辑器可用。 | unknown / OH: unknown / 路由与代际: source-build/host r86 builds86–90 | emacs [reported] r86 fts让native库载入，但首Activity仍ClassNotFoundException（相对类名未展开）；r87 launcher展开后才draw，不将fts加载当全编辑器成功。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; 实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。 |
| [NATIVE-151](#native-151) r86线程创建参数顺序转接 | 已实现 / historical | 报告按Bionic参数/attr顺序转到OH musl，TikTok过该线程墙；未外推pthread结构/全部同步API。 | unknown / OH: unknown / 路由与代际: source-build/host r86 builds86–90 | TikTok [reported] r86 pthread_create按Bionic顺序转接后到drawing；r87所记libhwui SIGSEGV dump实际是早2h22m同PID的PPSSPP，不能借错dump降级TikTok。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; 实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。 |
| [NATIVE-152](#native-152) r86 mozglue allocator/operator版本选择 | 部分实现 / historical | 按libmozglue版本提供C++operator/allocator，防runtime复制件错误interposition；精确版本节点应补本profile导出map，不能用U14 LIBC map代替。 | unknown / OH: unknown / 路由与代际: source-build/host r86 builds86–90 | Fennec [reported] r86 libmozglue operator/allocator按版本+字体一起到drawing；未凭该报告断定对应版本map已在U13。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; 实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。 |
| [NATIVE-153](#native-153) r87不会递交到app的queue shim | 占位/降级 / historical | AInputQueue/Event/Key/Motion为空queue兼容shim，runtime无NativeActivity native，fromJava省略；aaaaxy库可加载不证明NDK事件递交。 | unknown / OH: unknown / 路由与代际: source-build/host r87 build95 | aaaaxy [reported] 8app输入shim测试只让libgojni载入，随后glGenVertexArrays missing并不画；queue永不到app/fromJava省略，后来GL修复不能算输入功能验证。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; 实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。 |
| [NATIVE-154](#native-154) r87 GLESv2 dlopen转OH GLESv3及继承 | 已实现 / historical | 在.z探测前将Android libGLESv2句柄映射OH GLESv3；Android namespace继承父GL栈。aaaaxy过GL加载/绘图为历史reported，不是输入shim突然真实现。 | unknown / OH: unknown / 路由与代际: source-build/host r87 build95 | aaaaxy [reported] r87 libGLESv2句柄转OH GLESv3，Ebiten取得glGenVertexArrays并draw；仅GL加载/绘图历史reported，没有真实NDK事件队列递交证据。; supertuxkart [reported] r86手工路由后GL可载入但入口仍null；r87 GLES3 lookup后路由对照可画菜单，未路由全量仍因runtime PNG的setjmp崩；r88才默认路由到首控件。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; 实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。 |
| [NATIVE-155](#native-155) r88默认native路由防runtime interposition | 部分实现 / historical | 129apps按gap maps将consumer库路由Android ns避开runtime PNG/HWUI复制；PPSSPP/STK移动；Chaquopy written-module双libpython风险须排除，SONAME!=文件名规则后续补。 | unknown / OH: unknown / 路由与代际: source-build/host r88 build96 | PPSSPP [reported] r88路由后JNI函数不再绑定libhwui副本，画welcome screen；r87未路由SIGSEGV仍在。; supertuxkart [reported] r88 libmain/libSDL2在Android ns后首启controls dialog覆于menu；r87未路由musl setjmp失败，非候选PPSSPP dlext补好了。; econverter [reported] routing A/B131app中written Chaquopy模块旁多出未初始化libpython而回退；随后排除这两app，不能声称所有129外的app都应强制路由。; werewolvesgame [reported] routing A/B131app中written Chaquopy模块旁多出未初始化libpython而回退；随后排除这两app，不能声称所有129外的app都应强制路由。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; 实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。 |
| [NATIVE-156](#native-156) r88 per-thread passwd/group结果 | 已实现 / historical | shim保留每线程结果而非musl共享line buffer；MaterialFiles交替6+6报告带shim0崩/不带1崩，样本有限，不承诺全线程安全。 | unknown / OH: unknown / 路由与代际: source-build/host r88 build96 | Material Files [reported] r88交替12次：per-thread getpw/getgr带shim6次0 crash，不带6次1次musl free/getgrgid heap crash；8其他app绘图，样本不是普遍功能保证。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; 实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。 |
| [NATIVE-157](#native-157) r89 if_name索引getifaddrs回退 | 已实现 / historical | OH app域ioctl被拒时shim通过getifaddrs查名/索引；不是绕过用户授权/任意ioctl放行，yaacc/openhab报告移动。 | unknown / OH: unknown / 路由与代际: source-build/host r89 build99 | yaacc [reported] r89 if_name索引用getifaddrs fallback后draw，首帧2.0s；只处理接口查询，不放行全部app域ioctl。; openhab [reported] r89 network-interface异常不再出现；报告该调用墙移动，不等同任意网络服务/跨版本功能通过。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; 实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。 |
| [NATIVE-158](#native-158) r89 UnixNativeDispatcher setters | 已实现 / historical | 报告runtime override补文件时间setter，gitling下一墙移动；该摘要未给具体native方法名/ABI/源码件SHA，保持类级成员并记缺口，不臆造futimes签名。 | unknown / OH: unknown / 路由与代际: source-build/host r89 build99 | gitling [reported] r89先支持legacy KeyPairGeneratorSpec，再补UnixNativeDispatcher file-time setter下一墙；报告draw首帧3.2s，精确native签名/本profile源码SHA未给。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; 实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。 |
| [NATIVE-159](#native-159) r89同窗口GL与HWUI surface竞争 | 缺口 / historical | usp小SurfaceView共用Activity OH window，GL先抢surface时HWUI abort；HWUI先抢时GL EGL_BAD_ALLOC且内容缺失；不是两条绘图路径完整可互换。 | unknown / OH: unknown / 路由与代际: source-build/host r89 build99 | usp [reported] r89 GL先获共享Activity EGL surface→HWUI drawRenderNode无surface abort；4次重跑2次GL先abort/2次HWUI先draw但emulator空。这是真功能缺口，drawing不是模拟器画面成功。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; 实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。 |
| [NATIVE-160](#native-160) r86/r87宿主麦克风请求后AudioRecord过墙 | 部分实现 / historical | host重装保持uid并请求麦克风，MuseKit报告调音器绘制/监听；未外推全部AudioRecord/AAudio或自动代用户授权。 | unknown / OH: unknown / 路由与代际: source-build/host r87 host4/build95 | MuseKit [reported] r86先因AudioRecord uninitialized停；host保持uid请求MICROPHONE并获授权后调音器draw/listens，r87再确认；没有自动代用户授予或所有录音API证明。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; 实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。 |
| [NATIVE-161](#native-161) 对象未产生时的void诊断 | 占位/降级 / candidate | AImage/AImageReader不产对象，delete只记录unsupported；不能冒充图像生命周期实现。 | android-14.0.0_r1 frameworks/av 402dbe885fd58af75e4c1d7e790fbf4bb22f29f9 / OH: unknown / 路由与代际: U12 candidate8fc0752d | subwaysurfers [static] libunity.so静态导入本行members（AMediaFormat_new为候选额外container接口）；8fc provider可覆盖名称与类型。没有新解码/播放/首屏证据，已证该候选新亮0。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; 候选provider-only行为测试不等于Subwaysurfers APK解码/播放成功；没有本轮t20或功能签认。 |
| [NATIVE-162](#native-162) 异步删除只释放转移来的fence | 部分实现 / candidate | 无image可删除，但AImage_deleteAsync关闭调用方转移的fence fd；保留所有权语义，不提供图像。 | android-14.0.0_r1 frameworks/av 402dbe885fd58af75e4c1d7e790fbf4bb22f29f9 / OH: unknown / 路由与代际: U12 candidate8fc0752d | subwaysurfers [static] libunity.so静态导入本行members（AMediaFormat_new为候选额外container接口）；8fc provider可覆盖名称与类型。没有新解码/播放/首屏证据，已证该候选新亮0。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; 候选provider-only行为测试不等于Subwaysurfers APK解码/播放成功；没有本轮t20或功能签认。 |
| [NATIVE-163](#native-163) Codec/track指针型unsupported | 占位/降级 / candidate | 构造/缓冲区/format/track返回NULL；缓冲区size置0，不造decoder或数据。 | android-14.0.0_r1 frameworks/av 402dbe885fd58af75e4c1d7e790fbf4bb22f29f9 / OH: unknown / 路由与代际: U12 candidate8fc0752d | subwaysurfers [static] libunity.so静态导入本行members（AMediaFormat_new为候选额外container接口）；8fc provider可覆盖名称与类型。没有新解码/播放/首屏证据，已证该候选新亮0。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; 候选provider-only行为测试不等于Subwaysurfers APK解码/播放成功；没有本轮t20或功能签认。 |
| [NATIVE-164](#native-164) 无decoder/样本的负数边界 | 占位/降级 / candidate | Codec dequeue返回合法unsupported；Extractor样本索引/时间/read返回无样本负数，非解码成功。 | android-14.0.0_r1 frameworks/av 402dbe885fd58af75e4c1d7e790fbf4bb22f29f9 / OH: unknown / 路由与代际: U12 candidate8fc0752d | subwaysurfers [static] libunity.so静态导入本行members（AMediaFormat_new为候选额外container接口）；8fc provider可覆盖名称与类型。没有新解码/播放/首屏证据，已证该候选新亮0。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; 候选provider-only行为测试不等于Subwaysurfers APK解码/播放成功；没有本轮t20或功能签认。 |
| [NATIVE-165](#native-165) DataSource/Extractor/Format真实释放 | 已实现 / candidate | 释放本候选拥有的callback holder、unconfigured extractor与int32 property链表；DataSource_delete不自行调用close；不接收Stagefright/AMessage外来对象。 | android-14.0.0_r1 frameworks/av 402dbe885fd58af75e4c1d7e790fbf4bb22f29f9 / OH: unknown / 路由与代际: U12 candidate8fc0752d | subwaysurfers [static] libunity.so静态导入本行members（AMediaFormat_new为候选额外container接口）；8fc provider可覆盖名称与类型。没有新解码/播放/首屏证据，已证该候选新亮0。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; 候选provider-only行为测试不等于Subwaysurfers APK解码/播放成功；没有本轮t20或功能签认。 |
| [NATIVE-166](#native-166) AMediaDataSource真实callback holder分配 | 已实现 / candidate | calloc自有opaque holder；非AOSP DataSource引擎对象，不把callback读取当实际媒体读取。 | android-14.0.0_r1 frameworks/av 402dbe885fd58af75e4c1d7e790fbf4bb22f29f9 / OH: unknown / 路由与代际: U12 candidate8fc0752d | subwaysurfers [static] libunity.so静态导入本行members（AMediaFormat_new为候选额外container接口）；8fc provider可覆盖名称与类型。没有新解码/播放/首屏证据，已证该候选新亮0。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; 候选provider-only行为测试不等于Subwaysurfers APK解码/播放成功；没有本轮t20或功能签认。 |
| [NATIVE-167](#native-167) AMediaDataSource保留callback/userdata | 已实现 / candidate | 真实写入read_at/get_size/close/userdata供后续持有；目前无解码器调用这些callback，不是流播放支持。 | android-14.0.0_r1 frameworks/av 402dbe885fd58af75e4c1d7e790fbf4bb22f29f9 / OH: unknown / 路由与代际: U12 candidate8fc0752d | subwaysurfers [static] libunity.so静态导入本行members（AMediaFormat_new为候选额外container接口）；8fc provider可覆盖名称与类型。没有新解码/播放/首屏证据，已证该候选新亮0。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; 候选provider-only行为测试不等于Subwaysurfers APK解码/播放成功；没有本轮t20或功能签认。 |
| [NATIVE-168](#native-168) 未支持property/轨道读取的false边界 | 占位/降级 / candidate | 未实现float/int64/string property查询返回false且不改输出，Extractor_advance也false；与int32真实属性分行。 | android-14.0.0_r1 frameworks/av 402dbe885fd58af75e4c1d7e790fbf4bb22f29f9 / OH: unknown / 路由与代际: U12 candidate8fc0752d | subwaysurfers [static] libunity.so静态导入本行members（AMediaFormat_new为候选额外container接口）；8fc provider可覆盖名称与类型。没有新解码/播放/首屏证据，已证该候选新亮0。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; 候选provider-only行为测试不等于Subwaysurfers APK解码/播放成功；没有本轮t20或功能签认。 |
| [NATIVE-169](#native-169) Extractor无配置时的零track | 部分实现 / candidate | 读取自有未配置容器返回0轨道；无媒体解析、track选择与sample读取，不返回假轨道。 | android-14.0.0_r1 frameworks/av 402dbe885fd58af75e4c1d7e790fbf4bb22f29f9 / OH: unknown / 路由与代际: U12 candidate8fc0752d | subwaysurfers [static] libunity.so静态导入本行members（AMediaFormat_new为候选额外container接口）；8fc provider可覆盖名称与类型。没有新解码/播放/首屏证据，已证该候选新亮0。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; 候选provider-only行为测试不等于Subwaysurfers APK解码/播放成功；没有本轮t20或功能签认。 |
| [NATIVE-170](#native-170) AMediaExtractor未配置容器真实分配 | 部分实现 / candidate | 分配本候选自有未配置opaque对象；setDataSource仍unsupported；不是NuMediaExtractor真移植。 | android-14.0.0_r1 frameworks/av 402dbe885fd58af75e4c1d7e790fbf4bb22f29f9 / OH: unknown / 路由与代际: U12 candidate8fc0752d | subwaysurfers [static] libunity.so静态导入本行members（AMediaFormat_new为候选额外container接口）；8fc provider可覆盖名称与类型。没有新解码/播放/首屏证据，已证该候选新亮0。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; 候选provider-only行为测试不等于Subwaysurfers APK解码/播放成功；没有本轮t20或功能签认。 |
| [NATIVE-171](#native-171) AMediaFormat真实int32属性读取 | 已实现 / candidate | 遍历本候选property链表，存在键输出int32并返回true；缺键false且输出不变，不向AMessage传对象。 | android-14.0.0_r1 frameworks/av 402dbe885fd58af75e4c1d7e790fbf4bb22f29f9 / OH: unknown / 路由与代际: U12 candidate8fc0752d | subwaysurfers [static] libunity.so静态导入本行members（AMediaFormat_new为候选额外container接口）；8fc provider可覆盖名称与类型。没有新解码/播放/首屏证据，已证该候选新亮0。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; 候选provider-only行为测试不等于Subwaysurfers APK解码/播放成功；没有本轮t20或功能签认。 |
| [NATIVE-172](#native-172) AMediaFormat真实创建/int32写入 | 已实现 / candidate | AMediaFormat_new分配自有property容器；setInt32新增strdup键或更新真实int32节点，delete释放；仅int32，不声称所有format字段类型。 | android-14.0.0_r1 frameworks/av 402dbe885fd58af75e4c1d7e790fbf4bb22f29f9 / OH: unknown / 路由与代际: U12 candidate8fc0752d | subwaysurfers [static] libunity.so静态导入本行members（AMediaFormat_new为候选额外container接口）；8fc provider可覆盖名称与类型。没有新解码/播放/首屏证据，已证该候选新亮0。 | Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。; 本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。; 候选provider-only行为测试不等于Subwaysurfers APK解码/播放成功；没有本轮t20或功能签认。 |
| [NATIVE-173](#native-173) R6 BLASTBufferQueue.nativeUpdate：成功SurfaceView专属child尺寸与主窗口兼容尺寸分流（未冻结） | 部分实现 / candidate | 仅BBQ_nativeUpdate：oh_rs_get_child_surface_window成功返回专属child才使用requested width/height；主ViewRoot/非SurfaceView和child失败fallback main均固定panel1200x1920；SurfaceView名字本身不能判成功。无session/无producer原失败返回保留；其余三几何/lazy/STAGE0/M1/SQLite行为不动。不是BLASTBufferQueue整族或SurfaceFlinger事务完整实现。 | unknown；source-only：候选JNI注册/源码注释指向AOSP调用约定，未建立Android版本支持区间 / OH: OpenHarmony 6.1.0.31，仅5ea实际；b711 Boat补充可操作，db429五popup另组原证据；其他OH版本unknown / 路由与代际: 5ea U13/R6 bounded candidate；7bind/337身份原完整集合；c208/f28；b711与db429证据组分别绑定 | com.Unity3d.BoatAttackDay [unit] 成功专属child→requested；主窗及名称SurfaceView但child失败→1200x1920；无session/无producer等六host分支实际通过；不是整族BLAST实现; com.Unity3d.BoatAttackDay [functional] root GAME_PASS，5ea/b711 boot、同PID5158/birth7195/UID20011062，1920x1200圆HUD/无观察到紫屏，左/右/加速/reset可见响应及LAP0/3→1/3；不宣称完整一圈或全赛道通关; cv2-com-edward-studytracker [reported] 同f28原R6 db4296cb-1d0a-46c2-ad31-5fbe3909002f t20原图经BMS目读：必需控件保留；本轮只静态消费该报告/原图pin，未重判human；原record foreground_unconfirmed保留，不能转借b711或full128; cv2-com-nicue-onetwo [reported] 同f28原R6 db4296cb-1d0a-46c2-ad31-5fbe3909002f t20原图经BMS目读：必需控件保留；本轮只静态消费该报告/原图pin，未重判human；原record foreground_unconfirmed保留，不能转借b711或full128; cv2-com-trianguloy-clipboardeditor [reported] 同f28原R6 db4296cb-1d0a-46c2-ad31-5fbe3909002f t20原图经BMS目读：必需控件保留；本轮只静态消费该报告/原图pin，未重判human；原record foreground_unconfirmed保留，不能转借b711或full128; cv2-io-github-jdanders-dropcount [reported] 同f28原R6 db4296cb-1d0a-46c2-ad31-5fbe3909002f t20原图经BMS目读：必需控件保留；本轮只静态消费该报告/原图pin，未重判human；原record foreground_unconfirmed保留，不能转借b711或full128; fd-seal [reported] 同f28原R6 db4296cb-1d0a-46c2-ad31-5fbe3909002f t20原图经BMS目读：必需控件保留；本轮只静态消费该报告/原图pin，未重判human；原record foreground_unconfirmed保留，不能转借b711或full128 | 能力未冻结：frozen_ids为空；源码/产物归档或实验freeze不等于API frozen登记。; 原全128八窗仍pending；十控/批量启动与337 PASS不能代替全128实际完成和用户解封。; Android运行版本、API支持范围与APK targetSdk均unknown/source-only，不能借AOSP注释或NDK对照推断。; 五popup为db429原组BMS图审报告，原foreground_unconfirmed不改；不能借其oldboot身份为新boot授准入。; 原首Boat五触组没有证明方向/LAP；成功为b711本轮补充独立组，非追认原首组。; 主ViewRoot政策相对947的1920x1200有实际变化；仅列出已测组，不外推所有popup/native方法。; nativeGetLastAcquiredFrameNum/nativeSyncNextTransaction/事务相关历史stub和r89 usp混合surface缺口旧行不升格。 |
| [REG-001](#reg-001) BMS 安装的 Android 包后台拉起 ability(START_ABILITIES_FROM_BACKGROUND) | 已实现 / historical / FZ-001 | 安装器在安装时刻授后台启动权限并登记 launcher 入口;libbms 查询路径返回可启动。只覆盖 BMS 安装路线 | unknown / OH: unknown / 路由与代际: feat/bms-route-deploy b5a67c62 代 | fd-tusky [reported] 61b: white -> own login page with only the installer changed (+ reboot); fd-k9 [reported] 61b: white -> own database upgrade page; fd-android (Thunderbird) [reported] 61b: white -> own database upgrade page; fd-filemanager [reported] 61b: white -> own list with three tabs; fd-k9 / fd-tusky / fd-android / fd-filemanager [reported] 5cd: same four, reproduced on a second board | APK 级验证为历史 reported,本轮未重看图; oh_tested 置 unknown:冻结登记为历史签认,未在本轮逐板核 OH 小版本;版本证据在 verified_apps 的 board 字段(61b/5cd/5ea); deployment=historical:冻结登记不等于当前部署;当前部署代需 image-provenance/runtime 指纹另证 |
| [REG-002](#reg-002) Android 子进程 ActivityThread 运行在显式 8MiB pthread(大栈 provider) | 已实现 / historical / FZ-002 | runtime provider 为每个 Android 子进程在独立 8MiB pthread 上跑 ActivityThread(深递归/大帧防溢出);双路径部署(/system/android/lib64 与 /system/lib64/westlake/route-a/) | unknown / OH: unknown / 路由与代际: Route A / provider 0509fe235a7883b5cd9b57477221cb868465de944c6f70ed0cf2835b0fe4a97c；登记实验 2026-09-30，U 代际 unknown | fd-tusky [reported] 5cd: Tusky own UI at t20 with ActivityThread on the dedicated 8 MiB pthread ([CM-BIGSTACK] stack=8390896 in its hilog); antennapod [reported] 5cd: AntennaPod own UI at t20 with ActivityThread on the dedicated 8 MiB pthread ([CM-BIGSTACK] stack=8390896 in its hilog); markor [reported] 5cd: Markor own UI at t20 with ActivityThread on the dedicated 8 MiB pthread ([CM-BIGSTACK] stack=8390896 in its hilog); fd-k9 [reported] 5cd: K-9 own UI at t20 with ActivityThread on the dedicated 8 MiB pthread ([CM-BIGSTACK] stack=8390896 in its hilog); fd-auxio [reported] 5cd: Auxio own UI at t20 with ActivityThread on the dedicated 8 MiB pthread ([CM-BIGSTACK] stack=8390896 in its hilog); helloworld / zigzag [reported] 61b: controls, same log line and own UI (cx-t0 native freeze audit) | APK 级验证为历史 reported,本轮未重看图; oh_tested 置 unknown:冻结登记为历史签认,未在本轮逐板核 OH 小版本;版本证据在 verified_apps 的 board 字段(61b/5cd/5ea); deployment=historical:冻结登记不等于当前部署;当前部署代需 image-provenance/runtime 指纹另证 |
| [REG-003](#reg-003) AssetManager.nativeOpenAssetFd 返回真实 ParcelFileDescriptor(未压缩 asset) | 已实现 / historical / FZ-003 | 对未压缩 asset 返回真实 ParcelFileDescriptor;仅此对象变更,与 532633da ReturnParcelFileDescriptor 同源 | unknown / OH: unknown / 路由与代际: unknown | newpipe [reported] 61b: t20 desktop -> own 直播 page (compare_runs variables: 1, runtime only); fd-uhabits [reported] 61b: UnsupportedOperationException 'Implement me' from nativeOpenAssetFd gone; first fatal moved to hwui 'drawRenderNode called on a context with no surface' | APK 级验证为历史 reported,本轮未重看图; oh_tested 置 unknown:冻结登记为历史签认,未在本轮逐板核 OH 小版本;版本证据在 verified_apps 的 board 字段(61b/5cd/5ea); deployment=historical:冻结登记不等于当前部署;当前部署代需 image-provenance/runtime 指纹另证 |
| [REG-004](#reg-004) sun.security.jca.Providers.jarVerificationProviders[0] conscrypt→BouncyCastle 重写 | 已实现 / historical / FZ-004 | JAR 层把 jarVerificationProviders[0] 从 conscrypt 重写为 BouncyCastle,getSunProvider 路径恢复;随 J1-final/J2/J3 代际携带 | unknown / OH: unknown / 路由与代际: J1-final faf0782b / J2 0715c964 / J3 75c2068c (jar 链) | fd-droidify [reported] J3 61b: Earlier PID-attributed Sun-provider failure; J3 helper rewrite present, old failure absent, own t20 UI; fd-com-amaze-filemanager [reported] J3 5ea: Earlier PID-attributed Sun-provider failure; J3 helper rewrite present, old failure absent, own t20 UI; antennapod [reported] J3 5ea: Earlier PID-attributed Sun-provider failure; J3 helper rewrite present, old failure absent, own t20 UI | APK 级验证为历史 reported,本轮未重看图; oh_tested 置 unknown:冻结登记为历史签认,未在本轮逐板核 OH 小版本;版本证据在 verified_apps 的 board 字段(61b/5cd/5ea); deployment=historical:冻结登记不等于当前部署;当前部署代需 image-provenance/runtime 指纹另证 |
| [REG-005](#reg-005) dex2oat-once 工具链: host dex2oat64(r1 树+22 补丁)离线重生成 27 件 boot image | 已实现 / historical / FZ-005 | 自有工具链离线重生成 27 件 boot image;板上 R155 libart 接受 image-only(T6c)与 image+jar 包(T7c)无 CheckSystemClass abort;常驻 libart 不变 | AOSP android-14.0.0_r1 / OH: unknown / 路由与代际: master(art-r155 T3c/T5c/T6c/T7c) | helloworld [reported] 61b: own-UI (Hello World! + CHANGE COLOR + lifecycle log + service buttons) under T5c image-only (T6c PASS); zigzag [reported] 61b: Unity 3D isometric path + ball + Trial Version under T5c (T6c PASS); aegis [reported] 61b: welcome / 2FA onboarding own-UI under T7c package (image+stubs jar); ooniprobe [reported] 61b: What is OONI Probe onboarding own-UI under T7c package | APK 级验证为历史 reported,本轮未重看图; oh_tested 置 unknown:冻结登记为历史签认,未在本轮逐板核 OH 小版本;版本证据在 verified_apps 的 board 字段(61b/5cd/5ea); deployment=historical:冻结登记不等于当前部署;当前部署代需 image-provenance/runtime 指纹另证 |
| [REG-006](#reg-006) android.os.VibratorManager.getVibratorIds() → int[0](route-A stub) | 已实现 / historical / FZ-006 | adapter 替换 vibrator_manager fetcher,无服务端实现按空设备集返回;mLock 保护(J7)。语义=无振动器设备而非真实振动 API | unknown / OH: unknown / 路由与代际: J7 a6a2537f9 / J7b jar 381110a6 / U6 统一态 | fd-feeder [reported] 5cd: U5 t20=no -> U6 own-UI at t20 (alive gained U5->U6); the vibrator_manager fetcher clears the getVibratorIds path Feeder hits during startup; fd-reader [reported] 5ea: vibrator getVibratorIds NPE cleared; first-fatal moved past the vibrator wall to the tagsoup/XMLReader boot-jar wall | APK 级验证为历史 reported,本轮未重看图; oh_tested 置 unknown:冻结登记为历史签认,未在本轮逐板核 OH 小版本;版本证据在 verified_apps 的 board 字段(61b/5cd/5ea); deployment=historical:冻结登记不等于当前部署;当前部署代需 image-provenance/runtime 指纹另证 |
| [REG-007](#reg-007) 完整 AOSP android-14.0.0_r1 external/tagsoup 进 BCP adapter-mainline-stubs jar | 已实现 / historical / FZ-007 | BCP 顺序(stubs 在 framework 前)使 stubs-jar 内完整 tagsoup 成为生效类,解除 IncompatibleClassChangeError;源=AOSP r1 外部 tagsoup | AOSP android-14.0.0_r1 / OH: unknown / 路由与代际: BCP adapter-mainline-stubs.jar T7d d8b2406e / AOSP android-14.0.0_r1 | fd-libretube [reported] 5cd: System.exit(1) (IncompatibleClassChangeError: tagsoup Parser does not implement XMLReader, MainActivity.onCreate) -> full native UI (LibreTube home, search + empty-state + Retry/Change-instance + bottom nav); wikipedia [reported] 5cd: tagsoup IncompatibleClassChangeError (Compose feed ErrorState/WikiErrorView) gone -> process no longer System.exit(1) (now alive t20; residual blank is a separate Compose-render wall) | APK 级验证为历史 reported,本轮未重看图; oh_tested 置 unknown:冻结登记为历史签认,未在本轮逐板核 OH 小版本;版本证据在 verified_apps 的 board 字段(61b/5cd/5ea); deployment=historical:冻结登记不等于当前部署;当前部署代需 image-provenance/runtime 指纹另证 |
| [REG-008](#reg-008) android.net.ssl.SSLSockets stub 进 BCP adapter-mainline-stubs jar | 已实现 / historical / FZ-008 | 新建类(BCP 无他处定义→G3 安全不遮蔽);类可解析使 OkHttp AndroidPlatform.buildIfSupported 走 fallback 而非 Dispatcher 崩溃 | unknown / OH: unknown / 路由与代际: BCP adapter-mainline-stubs.jar T7d d8b2406e | noice [reported] 5cd: blank (caught SSLSockets NoClassDefFoundError) -> noice AppIntro welcome own-UI (欢迎 + logo + Skip); wikipedia [reported] 5cd: 18x SSLSockets NoClassDefFoundError on OkHttp Dispatcher (TLS dead) gone -> OkHttp TLS resolves; fd-noice [reported] 5cd: SSLSockets CNF gone (3 runs) | APK 级验证为历史 reported,本轮未重看图; oh_tested 置 unknown:冻结登记为历史签认,未在本轮逐板核 OH 小版本;版本证据在 verified_apps 的 board 字段(61b/5cd/5ea); deployment=historical:冻结登记不等于当前部署;当前部署代需 image-provenance/runtime 指纹另证 |
| [REG-101](#reg-101) 板上 libart 代际判定(oat230/image108, R155 无布局差)（支撑知识） | 已实现 / historical | 板上 libart(59e1bb45)与官方 aosp-14.0.0_r16 产物逐指令同形(count@8/tbnz bit0/hash@12/data@16)+源码级 230/108 常量;R155 风险排除 | AOSP android-14.0.0_r16(对照) 与 android-14.0.0_r1(源) / OH: unknown / 路由与代际: unknown | (无 APK——纯静态反汇编) [static] 指纹+常量双验 | 板上 libart 精确源 commit 未知(d600 树未取得) |
| [REG-102](#reg-102) 官方 r16 dex2oat 9-jar 复现(7s 工具链 vs c-route 570s 挂起)（支撑知识） | 已实现 / historical | 官方 aosp-14.0.0_r16 树构建,板上 boot.oat 内 cmdline 逐字复刻;7.086s 出 27 文件(vdex 9/9 逐位同,art/oat 因 cmdline 路径串+53KB 残差) | unknown / OH: unknown / 路由与代际: unknown | (无 APK——host 工具) [unit] 27 文件生成+L1/L2 判定 | art/oat 18 件未逐字节复现(checksum+53KB 残差,归因 d600 构建侧差异); d600 树源未取得 |
| [REG-103](#reg-103) arm64 asm 常量对齐(asm_defines 上游生成器重生成)（支撑知识） | 已实现 / historical | A15 手写 asm_defines.h(THREAD_CARD_TABLE_OFFSET 0x90)毒化 asm 对象;用 108 树自带 cpp-define-generator 重生成真值(0x98/0xa0/0xe0/0x24)并强制重汇三件,修掉 thread_arm64 Check failed | unknown / OH: unknown / 路由与代际: unknown | (无 APK——交叉编译产物) [static] Thread 布局常量与 108 源一致 | 产物未持久到 master 树(hw248 $HW248_ROOT) |
| [REG-104](#reg-104) CheckSystemClass 豁免(A15 patch 语义移植)（支撑知识） | 已实现 / historical | A15 host 线从来是放行(非通过)String mismatch;把该豁免打到 108 原生基上,r16 host 链 InitWithoutImage 通过;板上 libart 无豁免(纯 r16 镜像必 abort,已由 5cd L2 失败实证) | unknown / OH: unknown / 路由与代际: unknown | (5cd L2 板测——历史) [reported] 纯 r16 镜像 5 app 全死 SIGABRT #05 CheckSystemClass;卸载恢复 | 豁免仅存在于 host 工具链,板上 libart 未打(设计如此) |
| [REG-105](#reg-105) 部署标签配方(12 规则, inode 标签非策略)（支撑知识） | 已实现 / historical | cx-bms 单一配方;seccomp-stock 规则因证伪删除(61b/5ea 原厂即 system_lib_file);每条经 sepolicy 门 sesearch 证明 | unknown / OH: unknown / 路由与代际: unknown | (无 APK——策略证明) [unit] 35 proofs 0 failures(app-private 范围外 skip) | app-private(/data/app)域归属未证(安装域关注,范围外) |
| [REG-106](#reg-106) 离线 sepolicy 门(sesearch 证明+fail-closed)（支撑知识） | 已实现 / historical | 读 cx-bms 配方原位(rules[]+match/context),a2hlab VM setools 4.4.4 sesearch;漂移/缺失/工具不可达均 fail-closed;拒复用过期 evidence | unknown / OH: unknown / 路由与代际: unknown | (无 APK——门禁) [unit] 5/5 测试+cargo selector | live 板上策略 vs 拉取件一致性依赖 SHA 钉(未每板重拉) |
| [REG-107](#reg-107) U13 recover-v3 冷启动恢复链(post-fs-data→ready 参数→boat overlay)（支撑知识） | 已实现 / historical | post-fs-data 期(先于 foundation/AMS)重放 56 基线 mount 不 umount(stat 连续防 init INVALID 闩锁);设 ready 参数触发 boat overlay;幂等(同 boot 已 READY 即退出);v3 增默认 OFF 的 permissive opt-in | unknown / OH: unknown / 路由与代际: unknown | (5cd/61b 电源循环验收——历史) [reported] 拔电重启无 Mac t20 亮;dmesg 0 invalid;父=init | v2/v3 双 cfg 并存,staged 目录需按 RECOVER_VARIANT 选择; permissive 14s 窗依赖 receipt-ready barrier |
| [REG-108](#reg-108) 封存 driver receipt-ready barrier(竞态修复)（支撑知识） | 已实现 / historical | oc-t4 只读审计定位:wait_boot 以 boot.completed 为准而 recover 收尾晚 14s;setenforce/dmesg/socket 检查曾撞窗口;cc-wiki 落 barrier 轮询 receipt.env state=READY+boot_id 匹配 | unknown / OH: unknown / 路由与代际: unknown | (无 APK——driver 逻辑) [static] 四检查移至 barrier 后 | 新版 driver 尚未在真实封存跑过一次(barrier 未实测) |
| [REG-109](#reg-109) BoatAttack 三私有件(C7/C4/signal-box)与 9 共享路径部署判定（支撑知识） | 已实现 / historical | 12 件输入(3 私有+9 共享候选)全部对钉值逐字节核验(0 缺 0 漂移);9 共享路径里 pthread_bridge 两代字节同(db31d6d8),libandroid 差 49B=CLASSNAME_FIX 非 ABI;路线①=统一态+私有件不碰共享路径 | unknown / OH: unknown / 路由与代际: unknown | boatattack [static] 12/12 输入件 SHA 对钉值 | 可玩判据(1920×1200/HUD/KPH)待上板; 49B CLASSNAME_FIX 移植决策未落 |
| [REG-110](#reg-110) NDK libandroid 缺口(ANativeWindow 簇等 16 符号) | 部分实现 / historical | OH 6.1 sysroot 符号核算:16 缺失;ANativeWindow 簇经 android_graphics_compat_shim.cpp 桥到 OH_NativeWindow_*(00.Workspace 72a2f0a52);传感器/配置簇未实现 | unknown / OH: unknown / 路由与代际: unknown | SDL2 类 app(libSDL2.so 命中) [static] 符号导出存在 | 16 缺失符号中仅 ANativeWindow 簇有桥;ASensor/AConfiguration 无实现; 桥接层未入主仓 |
| [REG-111](#reg-111) 可重编产物清单(adapter846/Boat8ab/U13 runtime187 等)（支撑知识） | 部分实现 / historical | 按两次干净构建+receipt 审计判定可重编/锁定;adapter846/Boat8ab/U13 runtime187 初批;无行证据或无双干净构建=locked | unknown / OH: unknown / 路由与代际: unknown | 无直接 APK 验证记录 | 清单为诊断性,不修改部署/准入/冻结; U13 其余成员待审计 receipt |
| [REG-112](#reg-112) 新 native 准入与 BCP 替换例外（支撑知识） | 已实现 / historical | 新 native 库走 new-native-admissions(SHA 钉);BCP jar 只许 adapter-mainline-stubs 例外+显式登记(U15 framework 位图经外环批) | unknown / OH: unknown / 路由与代际: unknown | 无直接 APK 验证记录 | 例外清单封闭集合,新例外需走同流程 |
| [REG-113](#reg-113) 验证辅助清单(flaky/benign/未落地 ack)（支撑知识） | 已实现 / historical | flaky key 单列防误判回归;fatal 判定先滤 benign 签名;未落地 lane 以 listing SHA 锚定 ack,改动即失效 | unknown / OH: unknown / 路由与代际: unknown | 无直接 APK 验证记录 | benign 库只覆盖已见签名,新噪声需增量 |
| [REG-114](#reg-114) 镜像来源例外与统一态归属判定（支撑知识） | 已实现 / historical | 按 boot-image-inputs SHA 与 runtime 指纹判定当前部署代归属;例外显式登记防误归 | unknown / OH: unknown / 路由与代际: unknown | 无直接 APK 验证记录 | 三板代际混杂历史(U13/U15/boat 候选),例外表需随封存收敛 |

## 逐项来源与版本

### JAVA-001

**T7-tagsoup** · BCP/系统服务

- 成员：org.ccil.cowan.tagsoup.Parser.setProperty(String,Object), org.ccil.cowan.tagsoup.Parser.getProperty(String)
- 实现：Four recognized property constants and Object backing fields; unknown property throws SAXNotRecognizedException；限制：Not a full TagSoup implementation; does not implement general HTML parse/setContentHandler/setFeature
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-u6-prospective/api-repairs.json
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：T7c；部署证据：historical
- 冻结：未登记；关联：REG-007
- 待补 / 限制：Not a full TagSoup implementation; does not implement general HTML parse/setContentHandler/setFeature；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推；T7c旧TagSoup已被FZ-007完整AOSP实现替代，勿当现态缺少XMLReader/parse。

- [api-repairs.json](<../../../../westlake-harness/benchmark/2026-10-01-u6-prospective/api-repairs.json>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `7b8fd383a0cf124af9e77a70dbd6574b05ba89f80fe47c1622843ec73079f1ed`
- [jar-api-members.json](<../../../../westlake-harness/benchmark/2026-10-01-u6-prospective/evidence/jar-api-members.json>)：已归档成员或来源摘录；SHA256 `de2ce5ed7578a113e5cd8c84dd1eaeb1d49cef68e9d8af9b7a9b7c5b33d04c33`

### JAVA-002

**T7-networkrequest** · BCP/系统服务

- 成员：android.net.NetworkRequest.getNetworkSpecifier()
- 实现：Boot method added；限制：Does not fix kotlinx.coroutines class loading
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-u6-prospective/api-repairs.json
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：T7c；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Does not fix kotlinx.coroutines class loading；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [api-repairs.json](<../../../../westlake-harness/benchmark/2026-10-01-u6-prospective/api-repairs.json>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `7b8fd383a0cf124af9e77a70dbd6574b05ba89f80fe47c1622843ec73079f1ed`
- [jar-api-members.json](<../../../../westlake-harness/benchmark/2026-10-01-u6-prospective/evidence/jar-api-members.json>)：已归档成员或来源摘录；SHA256 `de2ce5ed7578a113e5cd8c84dd1eaeb1d49cef68e9d8af9b7a9b7c5b33d04c33`

### JAVA-003

**T7-mediastore** · BCP/系统服务

- 成员：android.provider.MediaStore$Images$Media.EXTERNAL_CONTENT_URI, android.provider.MediaStore$Images$Media.INTERNAL_CONTENT_URI
- 实现：Fields and class initialization added；限制：No canManageMedia or Files.getContentUri in T7c
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-u6-prospective/api-repairs.json
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：T7c；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：No canManageMedia or Files.getContentUri in T7c；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [api-repairs.json](<../../../../westlake-harness/benchmark/2026-10-01-u6-prospective/api-repairs.json>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `7b8fd383a0cf124af9e77a70dbd6574b05ba89f80fe47c1622843ec73079f1ed`
- [jar-api-members.json](<../../../../westlake-harness/benchmark/2026-10-01-u6-prospective/evidence/jar-api-members.json>)：已归档成员或来源摘录；SHA256 `de2ce5ed7578a113e5cd8c84dd1eaeb1d49cef68e9d8af9b7a9b7c5b33d04c33`

### JAVA-004

**T7-networkinfo** · BCP/系统服务

- 成员：android.net.NetworkInfo.getState()
- 实现：Boot method added；限制：No ColorMatrix.setSaturation repair
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-u6-prospective/api-repairs.json
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：T7c；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：No ColorMatrix.setSaturation repair；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [api-repairs.json](<../../../../westlake-harness/benchmark/2026-10-01-u6-prospective/api-repairs.json>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `7b8fd383a0cf124af9e77a70dbd6574b05ba89f80fe47c1622843ec73079f1ed`
- [jar-api-members.json](<../../../../westlake-harness/benchmark/2026-10-01-u6-prospective/evidence/jar-api-members.json>)：已归档成员或来源摘录；SHA256 `de2ce5ed7578a113e5cd8c84dd1eaeb1d49cef68e9d8af9b7a9b7c5b33d04c33`

### JAVA-005

**T7-bandwidth** · BCP/系统服务

- 成员：android.net.NetworkCapabilities.getLinkUpstreamBandwidthKbps(), android.net.NetworkCapabilities.getLinkDownstreamBandwidthKbps()
- 实现：Bandwidth accessors added；限制：No getSignalStrength repair
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-u6-prospective/api-repairs.json
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：T7c；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：No getSignalStrength repair；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [api-repairs.json](<../../../../westlake-harness/benchmark/2026-10-01-u6-prospective/api-repairs.json>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `7b8fd383a0cf124af9e77a70dbd6574b05ba89f80fe47c1622843ec73079f1ed`
- [jar-api-members.json](<../../../../westlake-harness/benchmark/2026-10-01-u6-prospective/evidence/jar-api-members.json>)：已归档成员或来源摘录；SHA256 `de2ce5ed7578a113e5cd8c84dd1eaeb1d49cef68e9d8af9b7a9b7c5b33d04c33`

### JAVA-006

**J7-appwidget** · BCP/系统服务

- 成员：Context.getSystemService(AppWidgetManager.class), AppWidgetManager.getAppWidgetIds(ComponentName)
- 实现：Registers class-to-service mapping, allocates manager and type-zero local IAppWidgetService；限制：Not real widget hosting; arrays empty
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-u6-prospective/api-repairs.json
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：J7b；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Not real widget hosting; arrays empty；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [api-repairs.json](<../../../../westlake-harness/benchmark/2026-10-01-u6-prospective/api-repairs.json>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `7b8fd383a0cf124af9e77a70dbd6574b05ba89f80fe47c1622843ec73079f1ed`
- [j7b-source.json](<../../../../westlake-harness/benchmark/2026-10-01-u6-prospective/evidence/j7b-source.json>)：已归档成员或来源摘录；SHA256 `80afea1adb70d8eb3500556fdb32cad08de9716a59c4a7c996953151e2e1458e`

### JAVA-007

**J7-vibrator** · BCP/系统服务

- 成员：SystemVibratorManager.getVibratorIds(), SystemVibrator.hasVibrator()
- 实现：Seeds mLock skipped by allocateInstance, existing service returns int[0]；限制：No physical vibration or EGL/native repair
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-u6-prospective/api-repairs.json
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：J7b；部署证据：historical
- 冻结：未登记；关联：REG-006
- 待补 / 限制：No physical vibration or EGL/native repair；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [api-repairs.json](<../../../../westlake-harness/benchmark/2026-10-01-u6-prospective/api-repairs.json>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `7b8fd383a0cf124af9e77a70dbd6574b05ba89f80fe47c1622843ec73079f1ed`
- [j7b-source.json](<../../../../westlake-harness/benchmark/2026-10-01-u6-prospective/evidence/j7b-source.json>)：已归档成员或来源摘录；SHA256 `80afea1adb70d8eb3500556fdb32cad08de9716a59c4a7c996953151e2e1458e`

### JAVA-008

**J7-wifi** · BCP/系统服务

- 成员：Context.getSystemService(wifi)
- 实现：Allocates non-null WifiManager even when IWifiManager is absent；限制：mService may remain null; does not supply IWifiManager or prove every WifiManager method
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-u6-prospective/api-repairs.json
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：J7b；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：mService may remain null; does not supply IWifiManager or prove every WifiManager method；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [api-repairs.json](<../../../../westlake-harness/benchmark/2026-10-01-u6-prospective/api-repairs.json>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `7b8fd383a0cf124af9e77a70dbd6574b05ba89f80fe47c1622843ec73079f1ed`
- [j7b-source.json](<../../../../westlake-harness/benchmark/2026-10-01-u6-prospective/evidence/j7b-source.json>)：已归档成员或来源摘录；SHA256 `80afea1adb70d8eb3500556fdb32cad08de9716a59c4a7c996953151e2e1458e`

### JAVA-009

**J7-battery** · BCP/系统服务

- 成员：registerReceiverWithFeature(ACTION_BATTERY_CHANGED), Intent.getIntExtra(level/scale/status/plugged)
- 实现：Only missing BATTERY_CHANGED sticky returns a synthetic Intent with full-charge defaults；限制：Other actions retain original possibly-null return; no Camera JNI fix
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-u6-prospective/api-repairs.json
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：J7b；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Other actions retain original possibly-null return; no Camera JNI fix；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [api-repairs.json](<../../../../westlake-harness/benchmark/2026-10-01-u6-prospective/api-repairs.json>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `7b8fd383a0cf124af9e77a70dbd6574b05ba89f80fe47c1622843ec73079f1ed`
- [j7b-source.json](<../../../../westlake-harness/benchmark/2026-10-01-u6-prospective/evidence/j7b-source.json>)：已归档成员或来源摘录；SHA256 `80afea1adb70d8eb3500556fdb32cad08de9716a59c4a7c996953151e2e1458e`

### JAVA-010

**J7-search** · BCP/系统服务

- 成员：ServiceManager.getService(search), SearchManager initialization
- 实现：Local ISearchManager installed in sCache；限制：Type-zero service, not real search backend
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-u6-prospective/api-repairs.json
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：J7b；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Type-zero service, not real search backend；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [api-repairs.json](<../../../../westlake-harness/benchmark/2026-10-01-u6-prospective/api-repairs.json>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `7b8fd383a0cf124af9e77a70dbd6574b05ba89f80fe47c1622843ec73079f1ed`
- [j7b-source.json](<../../../../westlake-harness/benchmark/2026-10-01-u6-prospective/evidence/j7b-source.json>)：已归档成员或来源摘录；SHA256 `80afea1adb70d8eb3500556fdb32cad08de9716a59c4a7c996953151e2e1458e`

### JAVA-011

**J7-wallpaper** · BCP/系统服务

- 成员：WallpaperManager.getWallpaperColors()
- 实现：Seeds sGlobals with a type-zero IWallpaperManager；限制：Returns null colors, not a real wallpaper service
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-u6-prospective/api-repairs.json
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：J7b；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Returns null colors, not a real wallpaper service；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [api-repairs.json](<../../../../westlake-harness/benchmark/2026-10-01-u6-prospective/api-repairs.json>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `7b8fd383a0cf124af9e77a70dbd6574b05ba89f80fe47c1622843ec73079f1ed`
- [j7b-source.json](<../../../../westlake-harness/benchmark/2026-10-01-u6-prospective/evidence/j7b-source.json>)：已归档成员或来源摘录；SHA256 `80afea1adb70d8eb3500556fdb32cad08de9716a59c4a7c996953151e2e1458e`

### JAVA-012

**用户解锁状态投影** · 系统服务

- 成员：UserManager.isUserUnlockingOrUnlocked(int), ContextImpl.getSharedPreferences(String,int), adapter.packagemanager.UserManagerProjectionProxy
- 实现：安装 child-local user binder；B7报告的用户200解锁查询返回true，避免SharedPreferences NPE，非完整多用户服务
- 源码 / 产物：unknown; implementation described in benchmark/2026-09-29-bms-link-entry-walls/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：OH 6.1.0.31 on 5cd (historical report)；ABI：unknown；路由 / 代际：B7 r2 a92f8135/r3 5aff7a2b；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [README.md](<../../../../westlake-harness/benchmark/2026-09-29-bms-link-entry-walls/README.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `02b5ab58fe23c44c12b3416e8e9b8fdec51e46e8348711fa2249a44de7b583b1`

### JAVA-013

**纯Java APK nativeLibraryDir 投影** · 包管理

- 成员：ApplicationInfo.nativeLibraryDir, B7BindFixes.apply
- 实现：不存在的nativeLibraryDir回退到该包代码目录；不创建任意native库能力
- 源码 / 产物：unknown; implementation described in benchmark/2026-09-29-bms-link-entry-walls/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：B7 r2/r3；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [README.md](<../../../../westlake-harness/benchmark/2026-09-29-bms-link-entry-walls/README.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `02b5ab58fe23c44c12b3416e8e9b8fdec51e46e8348711fa2249a44de7b583b1`

### JAVA-014

**activity-alias 目标解析** · 生命周期

- 成员：ActivityInfo.targetActivity, LaunchActivityAliasProjection.apply, AppSchedulerBridge.buildActivityInfoFromAbility
- 实现：启动入口为alias时解析targetActivity，并保持目标activity的元数据；不等于全部主题顺序正确
- 源码 / 产物：unknown; implementation described in benchmark/2026-09-29-bms-link-entry-walls/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：B5 carried by B7 r3；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：alias主题另有U15顺序修复；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [README.md](<../../../../westlake-harness/benchmark/2026-09-29-bms-link-entry-walls/README.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `02b5ab58fe23c44c12b3416e8e9b8fdec51e46e8348711fa2249a44de7b583b1`

### JAVA-015

**XML-only图标安全占位** · 安装/资源

- 成员：ClassifyIconlessApk, DECLARED_XML_ONLY
- 实现：声明图标仅vector/adaptive XML时允许模板占位；截断/不可读图标仍拒
- 源码 / 产物：unknown; implementation described in benchmark/2026-09-29-bms-link-entry-walls/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：libapk_installer 1ebf78ab (B7); prior675536e8；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [README.md](<../../../../westlake-harness/benchmark/2026-09-29-bms-link-entry-walls/README.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `02b5ab58fe23c44c12b3416e8e9b8fdec51e46e8348711fa2249a44de7b583b1`

### JAVA-016

**电话/订阅 present-but-off** · 系统服务

- 成员：Context.getSystemService("phone"), TelephonyManager.getDeviceId(), TelephonyManager.getSimState(), SubscriptionManager, adapter.activity.TelephonyFetcher.install
- 实现：非空manager+本地ITelephony/ISub类型零binder；SIM/电话/数据状态为0、标识null，不伪造IMEI，不提供电话硬件
- 源码 / 产物：benchmark/2026-10-01-u11-jar/src/TelephonyFetcher.java
- Android 源码：AOSP14 TelephonyFrameworkInitializer registration pattern (reported)；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U11 277d4641 / U11i 5ae3dd29；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：x/头条为预测受益，本文构建报告不能充作已经过墙；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [README.md](<../../../../westlake-harness/benchmark/2026-10-01-u11-jar/README.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `545c09616c1c2dd094e4caff959e69c467522e292b2fbfdbac1437d58159f605`
- [TelephonyFetcher.java](<../../../../westlake-harness/benchmark/2026-10-01-u11-jar/src/TelephonyFetcher.java>)：本轮读取的实现源码快照，不能独立证明已部署同源；SHA256 `4e9e7358568f10137aa7cd78c45efa882cc4ec4f514e5d069dd787109b55703e`

### JAVA-017

**SSLEngine 元数据安全实例** · TLS/Java

- 成员：SSLContext.createSSLEngine(), WestlakeSSLContextSpi.engineCreateSSLEngine(), WlSSLEngine.wrap, WlSSLEngine.unwrap
- 实现：非空协议/cipher/session元数据；wrap/unwrap明确SSLException，不实现TLS传输
- 源码 / 产物：benchmark/2026-10-01-u11-jar/src/WlSSLEngine.java
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U11b d75e90c0；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：不得把非空SSLEngine标成可握手/联网；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [README.md](<../../../../westlake-harness/benchmark/2026-10-01-u11-jar/README.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `545c09616c1c2dd094e4caff959e69c467522e292b2fbfdbac1437d58159f605`
- [WlSSLEngine.java](<../../../../westlake-harness/benchmark/2026-10-01-u11-jar/src/WlSSLEngine.java>)：本轮读取的实现源码快照，不能独立证明已部署同源；SHA256 `8516d602bf74dbe4d85eabbecac64302cfba18e26c990e0eff5188cc2f6b7989`

### JAVA-018

**本包Provider实例化与发布** · 内容提供者

- 成员：ActivityThread.installContentProviders, ContentProvider.attachInfo, ContentProviderRegistry, AppContentProviders.install
- 实现：post-bind实例化Provider、attachInfo并发布；检测mLocalProvidersByName避免双onCreate；Application.onCreate之后才运行，与AOSP顺序不同
- 源码 / 产物：benchmark/2026-10-01-u11-jar/src/AppContentProviders.java
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U11c74434240误接线→U11d84c8da6b→U11i5ae3dd29；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Application.onCreate内部查询Provider的时序未覆盖；报告预测notepad增亮不当作实测；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [README.md](<../../../../westlake-harness/benchmark/2026-10-01-u11-jar/README.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `545c09616c1c2dd094e4caff959e69c467522e292b2fbfdbac1437d58159f605`
- [AppContentProviders.java](<../../../../westlake-harness/benchmark/2026-10-01-u11-jar/src/AppContentProviders.java>)：本轮读取的实现源码快照，不能独立证明已部署同源；SHA256 `ecd98575914d8a41275e43535d7a7f7d8760d0be815283e2fae1132cc8361dfb`

### JAVA-019

**每进程AES/GCM自检** · 支撑工具/进程自检（非API修复）

- 成员：KeystoreBoardProbe.selfTest(), KeystoreBoardProbe.run(String)
- 实现：随机256-bit SecretKeySpec走默认AES/GCM并做Tink式帧往返；记录错误，不是API修复
- 源码 / 产物：benchmark/2026-10-01-u11-jar/src/KeystoreBoardProbe.java
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U11h14ed34bc/U11i5ae3dd29；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：key存在性probe与key-independent selftest不可混算；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推；诊断支撑知识条目，不计新增API实现或点亮增益。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-01-u11-jar/README.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `545c09616c1c2dd094e4caff959e69c467522e292b2fbfdbac1437d58159f605`
- [KeystoreBoardProbe.java](<../../../../westlake-harness/benchmark/2026-10-01-u11-jar/src/KeystoreBoardProbe.java>)：本轮读取的实现源码快照，不能独立证明已部署同源；SHA256 `a586dcaee3d214e7143d5f465f260d198334c2b35cc24d8f04d62e45fde1a54a`

### JAVA-020

**资源型Provider authority纠正** · 内容提供者

- 成员：ProviderInfo.authority, ProviderAuthorityRefs, SelfComponentFallback.manifestProvider
- 实现：将@resource authority按同class的PM投影解析；literal不变，无法解析仍保留并记日志
- 源码 / 产物：benchmark/2026-10-02-u12-java-walls/src-runtime/adapter/activity/ProviderAuthorityRefs.java
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U12r2 runtime0482c9b1；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：构建/单测证明，不在本文虚报notepad/fd-client上屏；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-u12-java-walls/README.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `5df388321050d98c139216b225575abd61187571a8f7d3bc29d157a655729224`
- [ProviderAuthorityRefs.java](<../../../../westlake-harness/benchmark/2026-10-02-u12-java-walls/src-runtime/adapter/activity/ProviderAuthorityRefs.java>)：本轮读取的实现源码快照，不能独立证明已部署同源；SHA256 `7301380458abd05abfb20d08bb5469989bba59faf911e6126a93ed37b87b1891`
- [receipt-u12r2.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-java-walls/gates/receipt-u12r2.json>)：U12r2完整JAR SHA/源指纹/构建，非当前部署声明；SHA256 `b1182a8a3b57443d0f57788b81679dccde88298282d0fbe39ae8330ff6b85bd4`

### JAVA-021

**电话class→service名映射** · 系统服务

- 成员：Context.getSystemService(TelephonyManager.class), Context.getSystemService(SubscriptionManager.class), TelephonyServiceNames
- 实现：仅已存在fetcher而class无name时补phone/subscription映射
- 源码 / 产物：benchmark/2026-10-02-u12-java-walls/src-runtime/adapter/activity/TelephonyServiceNames.java
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U12r2 runtime0482c9b1；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-u12-java-walls/README.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `5df388321050d98c139216b225575abd61187571a8f7d3bc29d157a655729224`
- [TelephonyServiceNames.java](<../../../../westlake-harness/benchmark/2026-10-02-u12-java-walls/src-runtime/adapter/activity/TelephonyServiceNames.java>)：本轮读取的实现源码快照，不能独立证明已部署同源；SHA256 `b14ab13c9905c20e577e5122dbdec6c0f21926ac2e864c44fd88573f8498259c`
- [receipt-u12r2.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-java-walls/gates/receipt-u12r2.json>)：U12r2完整JAR SHA/源指纹/构建，非当前部署声明；SHA256 `b1182a8a3b57443d0f57788b81679dccde88298282d0fbe39ae8330ff6b85bd4`

### JAVA-022

**TelephonyServiceManager惰性取值** · BCP/系统服务

- 成员：TelephonyFrameworkInitializer.getTelephonyServiceManager(), TelephonyFrameworkInitializer.setTelephonyServiceManager()
- 实现：增加getter与缓存字段；setter仍原no-op；能找本地phone/isub，不变成完整system_server服务
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-02-u12-java-walls/README.md
- Android 源码：AOSP14 class/member names per report；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U12r2 stubs00b30467/615b8bbe；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：setter仍为stub，不能宣称完整初始化；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-u12-java-walls/README.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `5df388321050d98c139216b225575abd61187571a8f7d3bc29d157a655729224`
- [receipt-u12r2.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-java-walls/gates/receipt-u12r2.json>)：U12r2完整JAR SHA/源指纹/构建，非当前部署声明；SHA256 `b1182a8a3b57443d0f57788b81679dccde88298282d0fbe39ae8330ff6b85bd4`

### JAVA-023

**老版Predicate入BCP** · BCP/类加载

- 成员：com.android.internal.util.Predicate.apply(Object)
- 实现：接口从独立runtime类加载器移到boot可见stubs；只提供类型契约
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-02-u12-java-walls/README.md
- Android 源码：AOSP <=7.1 interface (report; exact tag unknown)；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U11i错误位置→U12r2 stubs；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-u12-java-walls/README.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `5df388321050d98c139216b225575abd61187571a8f7d3bc29d157a655729224`
- [receipt-u12r2.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-java-walls/gates/receipt-u12r2.json>)：U12r2完整JAR SHA/源指纹/构建，非当前部署声明；SHA256 `b1182a8a3b57443d0f57788b81679dccde88298282d0fbe39ae8330ff6b85bd4`

### JAVA-024

**GCM默认nonce旧R3失败实现** · 加密

- 成员：GcmDefaultNonce, Cipher.init(int,Key), AES/GCM/NoPadding
- 实现：U12/R3用外层Cipher包装BC delegate；Android libcore未初始化delegate，host JVM成功不能外推ART
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-03-u13-jar-v3-gcm/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U12r2/U13v2 506abe23；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：旧版本已知selftest error，不得列为通过；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [README.md](<../../../../westlake-harness/benchmark/2026-10-03-u13-jar-v3-gcm/README.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `dc30e1e70aa67fe9db86fb1d409031bef1e569cab354a0e11bea8a8c296636f2`
- [receipt-u12r2.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-java-walls/gates/receipt-u12r2.json>)：U12r2完整JAR SHA/源指纹/构建，非当前部署声明；SHA256 `b1182a8a3b57443d0f57788b81679dccde88298282d0fbe39ae8330ff6b85bd4`

### JAVA-025

**GCM默认nonce修正v3** · 加密

- 成员：GcmDefaultNonce, CipherSpi.engineInit, CipherSpi.engineDoFinal, AES/GCM/NoPadding
- 实现：直接驱动delegate CipherSpi；无参encrypt/wrap补12字节nonce/128-bit tag，显式IV/AAD透传
- 源码 / 产物：benchmark/2026-10-03-u13-jar-v3-gcm/src/adapter/core/GcmDefaultNonce.java
- Android 源码：AOSP android-14.0.0_r1 host ART (test semantics, not source of bespoke wrapper)；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U13v3 bbc3f530190fe98e2979dc4059379f8a0259d1f6ab243830347ca875cdb62f9b；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：test为host ART+板BCP，Android设备实测仍unknown；全体JCA算法不在本修复范围；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [README.md](<../../../../westlake-harness/benchmark/2026-10-03-u13-jar-v3-gcm/README.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `dc30e1e70aa67fe9db86fb1d409031bef1e569cab354a0e11bea8a8c296636f2`
- [GcmDefaultNonce.java](<../../../../westlake-harness/benchmark/2026-10-03-u13-jar-v3-gcm/src/adapter/core/GcmDefaultNonce.java>)：本轮读取的实现源码快照，不能独立证明已部署同源；SHA256 `793ee91486b17211a82b12e9398212e00b002b9d6ca331fbbd33321e7c3ed921`
- [results.json](<../../../../westlake-harness/benchmark/2026-10-03-u13-jar-v3-gcm/results.json>)：旧jar负控与v3三case/validateAead=OK；SHA256 `5fcad3723c5ac266ae1acf32be34e0c9b61654ebdbc2e071694ce7e7f0a17e85`

### JAVA-026

**NameValueCache本地ANDROID_ID** · 系统服务/设置

- 成员：Settings.Secure.getString(ContentResolver,"android_id"), WlSettingsProvider.answer, WlSettingsStub
- 实现：注入Global/Secure/System holder的call快路径；稳定16hex ID存no_backup，其余keysnull；无直接query/observer服务
- 源码 / 产物：benchmark/2026-10-02-u12-jar-plan/src/adapter/activity/WlSettingsProvider.java
- Android 源码：Westlake 1c883ad/2c46770; AOSP14 Settings named fields per report；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U12r1 3bca82c5；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Config holder未注入；直接ContentResolver查询仍OH桥，不是本地完整settings数据库；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-u12-jar-plan/README.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `6539c2db35842afc448896d8f10140d5a1cb9b063ea9ad0c99ef0d50d44d18c9`
- [WlSettingsProvider.java](<../../../../westlake-harness/benchmark/2026-10-02-u12-jar-plan/src/adapter/activity/WlSettingsProvider.java>)：本轮读取的实现源码快照，不能独立证明已部署同源；SHA256 `fd1d70e2739b948655ad5533c52299792404a17cf5bbccc859716f1b95036bba`

### JAVA-027

**本包Provider提前查询** · 内容提供者

- 成员：OwnProviderLocal.install, ContentResolver.query, IActivityManager.getContentProvider
- 实现：本包authority优先local lookup以免路由到不可连接OH DataShare；具体边界依赖OwnProviderLocal源码
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-02-u12-jar-plan/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U11j57aaaf7d63→U12r1；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：未在本轮确认所有provider跨进程/Binder行为；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-u12-jar-plan/README.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `6539c2db35842afc448896d8f10140d5a1cb9b063ea9ad0c99ef0d50d44d18c9`

### JAVA-028

**ViewDelegate写回** · WebView

- 成员：WebViewProvider.getViewDelegate(), WebView.PrivateAccess.super_setLayoutParams, WebView.PrivateAccess.super_setFrame
- 实现：有同名同参super_*则转发，其余类型零；修框架layoutParams契约，不提供网页渲染
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-j10e-jar/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：J10e3c147964；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [README.md](<../../../../westlake-harness/benchmark/2026-10-01-j10e-jar/README.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `5fdd377358dbdeb146593fb2b0f07d27426ea759f0c8e0bc6782951c643ff23a`

### JAVA-029

**CookieManager空实现** · WebView

- 成员：CookieManager.getCookie(String), CookieManager.hasCookies(boolean), WebViewFactoryProvider.getCookieManager()
- 实现：覆盖含@hide的16abstract方法；acceptCookie=true/getCookie=null/其余no-op；不是cookie持久化
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-j10e-jar/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：J10e3c147964；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [README.md](<../../../../westlake-harness/benchmark/2026-10-01-j10e-jar/README.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `5fdd377358dbdeb146593fb2b0f07d27426ea759f0c8e0bc6782951c643ff23a`

### JAVA-030

**WebSettings类型零实例** · WebView

- 成员：WebViewProvider.getSettings(), WebSettings.setJavaScriptEnabled(boolean), WebSettings.getUserAgentString()
- 实现：按AOSP14 r1生成104abstract overrides，getter类型零/setterno-op；不激活JS引擎；null String有后续非空风险
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-j10f-jar/README.md
- Android 源码：AOSP android-14.0.0_r1 WebSettings.java；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：J10f a0f8ba45；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：非空实例不等于WebView可渲染；后续安全字符串默认值需另版本证据；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [README.md](<../../../../westlake-harness/benchmark/2026-10-01-j10f-jar/README.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `2fb7e3c502186828c28a7362c15dcf1fcac10cad60315a937db2eb0594054e84`

### JAVA-031

**NWeb Java转接候选** · WebView

- 成员：OhNWebController.loadUrl, OhNWebController.evaluateJavascript, NWebCallbackSink.onPageFinished, WebViewClient.shouldInterceptRequest, OhNWebProviderFix.install
- 实现：Java controller转发backend与回调；mock19case，JNI declarations存在但此包无native实现
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-03-m2-route-a-java/README.md
- Android 源码：AOSP14 WebViewProvider signatures (report)；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：M2 candidate；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：mock不证明板上NWeb功能/绘制；尚未验native↔Java部署闭环；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [README.md](<../../../../westlake-harness/benchmark/2026-10-03-m2-route-a-java/README.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `5cb511d62c2a177a9cf957233397f61f0c51b2a795df2462ef96474ac5cccf0f`

### JAVA-032

**AndroidX WebKit支持库边界缺口** · WebView

- 成员：androidx.webkit.WebViewFeature, androidx.webkit.internal.WebViewGlueCommunicator
- 实现：记录privacybrowser在自身AndroidX触发UnsupportedOperation，缺support-library glue；不与网页绘制backend混算
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-03-u13-java-walls-2/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U13 history；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [README.md](<../../../../westlake-harness/benchmark/2026-10-03-u13-java-walls-2/README.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `5fc232ecdeef36654b072c133f254a1d4d0380537be3606f870d0b605fc5cd37`

### JAVA-033

**Activity自己的manifest theme恢复** · 资源/主题

- 成员：ActivityInfo.getThemeResource(), J10dTheme.restore(ActivityInfo), ManifestJsonFallback.activityTheme
- 实现：在所有theme覆写后、scheduleTransaction前恢复Activity主题，非alias才restore；不能用platform windowActionBar代替app androidx属性
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-j10d-jar/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：J10d57d62183；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [README.md](<../../../../westlake-harness/benchmark/2026-10-01-j10d-jar/README.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `c6f201e8a70ecd86e32cbbb895a833c27680d183379f6055a5b643d138c5b258`

### JAVA-034

**alias目标主题最终写入顺序** · 资源/主题

- 成员：AliasTargetTheme.apply(ActivityInfo), ActivityInfo.theme, AppSchedulerBridge.nativeOnScheduleLaunchAbility
- 实现：现有AliasTargetTheme在sEnrichedTheme覆写之后再调用一次；不是新manifest reader
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-03-u15-jar-v1/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U15 candidate20e748e57c6ee8bd0b97dcfff074c3a1c001dd727cbcee6a754f60a598642770；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：fd-api主题板验待证；U15旧提案needle会被后续覆写，不能两者混算；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [README.md](<../../../../westlake-harness/benchmark/2026-10-03-u15-jar-v1/README.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `980e74cb0e4d05f3602af1e715f824e357086bb9af160043442e4a52e2665a50`

### JAVA-035

**本进程bind-service回调排序** · 生命周期

- 成员：InProcessBindOrder, ServiceConnection.onServiceConnected, ActivityManagerBindProxy.postInProcessBind
- 实现：等Activity started/resumed再投递service callback，destroyed丢弃；只覆盖in-process事件
- 源码 / 产物：benchmark/2026-10-03-u14-jar-v1/src/adapter/activity/InProcessBindOrder.java
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U14 candidate0349eb83；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：完整Termux启动/terminal bootstrap未在host测试复现；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [README.md](<../../../../westlake-harness/benchmark/2026-10-03-u14-jar-v1/README.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `06e721f2603eafad2883d6f7282e1baf820a9479b30423a84b793e252346a89d`
- [InProcessBindOrder.java](<../../../../westlake-harness/benchmark/2026-10-03-u14-jar-v1/src/adapter/activity/InProcessBindOrder.java>)：本轮读取的实现源码快照，不能独立证明已部署同源；SHA256 `0b073543a31ff040ef85ccec324cbc1740ae877887158226d94c29e7ee467bdd`

### JAVA-036

**trampoline finish延迟/去重** · 生命周期

- 成员：TrampolineFinishOrder.install, IActivityTaskManager.startActivity, IActivityClientController.finishActivity, TrampolineFinishOrder.onLaunchAbility
- 实现：own-package start未达本进程时最多hold3秒，launch或timeout转交一次；其他调用透传
- 源码 / 产物：benchmark/2026-10-03-u15-jar-v1/src/adapter/activity/TrampolineFinishOrder.java
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U15 candidate20e748e5；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：host ART测试模拟OH adapter；36key预测不充作36个实测成功；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [README.md](<../../../../westlake-harness/benchmark/2026-10-03-u15-jar-v1/README.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `980e74cb0e4d05f3602af1e715f824e357086bb9af160043442e4a52e2665a50`
- [TrampolineFinishOrder.java](<../../../../westlake-harness/benchmark/2026-10-03-u15-jar-v1/src/adapter/activity/TrampolineFinishOrder.java>)：本轮读取的实现源码快照，不能独立证明已部署同源；SHA256 `1bb66fd9966e9485f1ee6d0ccd037c02d78c53e89e396fbfb2b2bf7c4d864050`

### JAVA-037

**APK网络权限投影** · 安装/权限

- 成员：android.permission.INTERNET, android.permission.ACCESS_NETWORK_STATE, oh_adapter::MapApkNetworkPermissions, module.json.requestPermissions
- 实现：uses-permission精确映射为OH INTERNET/GET_NETWORK_INFO并去重；仅这两项，不概括全部Android权限
- 源码 / 产物：unknown; implementation described in $WORKSPACES/westlake-harness-bms-deploy/benchmark/2026-09-30-installer-background-launcher/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：B89 baseline6f94d4f4/eb6824b4→background6aadb8b4/7048c7c5；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：ATM实际授予/联网结果需关联历史run，不由HAP生成单测外推；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [README.md](<../../../../westlake-harness-bms-deploy/benchmark/2026-09-30-installer-background-launcher/README.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `487fa77ba59fabb4bf7c7f90a172d0fba8ff28effb09bcf24e7317e44d27bfe9`
- [apk_network_permissions.h](<../../../../westlake-harness-bms-deploy/benchmark/2026-09-30-installer-background-launcher/cc-wiki-source/apk_network_permissions.h>)：部署构建输入的精确两权限映射与background列表；SHA256 `c68cfac4657cf24c0d1b3b0dac4d751aaddd9e7df39754524147ab066d94c16c`

### JAVA-038

**OH后台启动能力授予** · 安装/权限

- 成员：ohos.permission.START_ABILITIES_FROM_BACKGROUND, HapPolicyParams.aclRequestedList, preAuthorizationInfo, AccessTokenKit::InitHapToken
- 实现：APL_NORMAL/isSystemApp=false不变；ACL+preAuthorization+HAP声明允许pending前台期内部startActivity；是OH capability，不是放开任意权限
- 源码 / 产物：unknown; implementation described in $WORKSPACES/westlake-harness-bms-deploy/benchmark/2026-09-30-installer-background-launcher/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：libbms6aadb8b4/libapk_installer7048c7c5；部署证据：historical
- 冻结：FZ-001；关联：无
- 待补 / 限制：无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [README.md](<../../../../westlake-harness-bms-deploy/benchmark/2026-09-30-installer-background-launcher/README.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `487fa77ba59fabb4bf7c7f90a172d0fba8ff28effb09bcf24e7317e44d27bfe9`
- [frozen.json](<../../../../westlake-harness/knowledge/frozen/frozen.json>)：FZ-001完整产物SHA与4APK历史证据；SHA256 `41971d779e43c08e18c2e82c98efc9832a43959e89aaf05636d53295fbfcdb46`

### JAVA-039

**主入口优先app自身launcher** · 安装/包管理

- 成员：SelectLauncherActivity, IsAndroidLauncherActivity, BMS mainAbility
- 实现：多个launcher中优先app自身包入口，减少LeakCanary误选；无launcher等回退仍由selector定义
- 源码 / 产物：unknown; implementation described in $WORKSPACES/westlake-harness-bms-deploy/benchmark/2026-09-30-installer-background-launcher/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：7048c7c5 + donor3188a4733；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [README.md](<../../../../westlake-harness-bms-deploy/benchmark/2026-09-30-installer-background-launcher/README.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `487fa77ba59fabb4bf7c7f90a172d0fba8ff28effb09bcf24e7317e44d27bfe9`

### JAVA-040

**ARS C最高密度bitmap图标** · 安装/资源

- 成员：ResolveResourceIdToFile, ReadIconByManifest, resources.arsc
- 实现：manifest图标id经arsc解析最高密度桶；已触发位图路径，不证明所有resource配置
- 源码 / 产物：unknown; implementation described in benchmark/2026-09-28-bms-label-resolve/RESULTS-B3.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：B3 libapk_installer675536e8；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [RESULTS-B3.md](<../../../../westlake-harness/benchmark/2026-09-28-bms-label-resolve/RESULTS-B3.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `4e9230fee49d78991c5bf63e62bd3d274267ac5dd77bd176eb7147f94b56c4e5`

### JAVA-041

**adaptive-icon像素合成候选** · 安装/资源

- 成员：ComposeAdaptiveIcon, TYPE_REFERENCE foreground/background
- 实现：AXML+arsc引用，ARGB纯色背景、双线性resize、src-over；B3板上未触发adaptive分支
- 源码 / 产物：unknown; implementation described in benchmark/2026-09-28-bms-label-resolve/RESULTS-B3.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：B3 libapk_installer675536e8；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：运行时unverified，不能把位图分支验证借给adaptive分支；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [RESULTS-B3.md](<../../../../westlake-harness/benchmark/2026-09-28-bms-label-resolve/RESULTS-B3.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `4e9230fee49d78991c5bf63e62bd3d274267ac5dd77bd176eb7147f94b56c4e5`

### JAVA-042

**APK native提取精确例外** · 安装/校验

- 成员：InstalldOperator, ExtractFiles(APK_NATIVE_SO), CRC/ELF/owner/mode verification
- 实现：51e1b525为#77/#79修订版；与2c9原板回滚版差异需按选定ABI精确样例解读，不放开所有ELF
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-10-spare-installer-unify/provenance.json
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：51e1b52538b3198d2a8a3236a9479bf8512f51acc74c0d68e34acca358f39be5 vs2c9a5294；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：补丁源码recipe/archive单独绑定，libinstalls不是libapk_installer；源树未必等于冻结archive成员；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [provenance.json](<../../../../westlake-harness/benchmark/2026-10-10-spare-installer-unify/provenance.json>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `2e2b09648fe04855d843051fb9093013f9624a1c8505df98041a3a44a8795dd8`

### JAVA-043

**alarm兼容底线** · 系统服务

- 成员：Context.getSystemService("alarm"), ServiceManager.getService("alarm")
- 实现：set接受但永不投递，next-alarm为空；单一fetcher非完整Android系统服务
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-system-service-gap/provided-services.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U9 source-inventory, must cross-check deployed238ffc14；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：该来源曾低估部署B8层；机制描述只用于列明底线，不能照此判所有当前服务缺失；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [provided-services.md](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/provided-services.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `a234155bc216e38633ceb22614123e79725503f60143a5f15c499a09f3d72d41`
- [README.md](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/README.md>)：修正旧源码快照与实际部署jar不一致的限制；SHA256 `cf4e2c528dff6d601e7acb430cf1909fb19679f97adb6227ac4fcbf24d43844c`

### JAVA-044

**clipboard兼容底线** · 系统服务

- 成员：Context.getSystemService("clipboard"), ServiceManager.getService("clipboard")
- 实现：ClipData进程内保存，非跨进程全局剪贴板；单一fetcher非完整Android系统服务
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-system-service-gap/provided-services.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U9 source-inventory, must cross-check deployed238ffc14；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：该来源曾低估部署B8层；机制描述只用于列明底线，不能照此判所有当前服务缺失；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [provided-services.md](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/provided-services.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `a234155bc216e38633ceb22614123e79725503f60143a5f15c499a09f3d72d41`
- [README.md](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/README.md>)：修正旧源码快照与实际部署jar不一致的限制；SHA256 `cf4e2c528dff6d601e7acb430cf1909fb19679f97adb6227ac4fcbf24d43844c`

### JAVA-045

**account兼容底线** · 系统服务

- 成员：Context.getSystemService("account"), ServiceManager.getService("account")
- 实现：空账号/无feature/token，未登录所有平台；单一fetcher非完整Android系统服务
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-system-service-gap/provided-services.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U9 source-inventory, must cross-check deployed238ffc14；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：该来源曾低估部署B8层；机制描述只用于列明底线，不能照此判所有当前服务缺失；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [provided-services.md](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/provided-services.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `a234155bc216e38633ceb22614123e79725503f60143a5f15c499a09f3d72d41`
- [README.md](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/README.md>)：修正旧源码快照与实际部署jar不一致的限制；SHA256 `cf4e2c528dff6d601e7acb430cf1909fb19679f97adb6227ac4fcbf24d43844c`

### JAVA-046

**power兼容底线** · 系统服务

- 成员：Context.getSystemService("power"), ServiceManager.getService("power")
- 实现：interactive/no-power-save；wake-lock本地接受；单一fetcher非完整Android系统服务
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-system-service-gap/provided-services.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U9 source-inventory, must cross-check deployed238ffc14；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：该来源曾低估部署B8层；机制描述只用于列明底线，不能照此判所有当前服务缺失；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [provided-services.md](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/provided-services.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `a234155bc216e38633ceb22614123e79725503f60143a5f15c499a09f3d72d41`
- [README.md](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/README.md>)：修正旧源码快照与实际部署jar不一致的限制；SHA256 `cf4e2c528dff6d601e7acb430cf1909fb19679f97adb6227ac4fcbf24d43844c`

### JAVA-047

**uimode兼容底线** · 系统服务

- 成员：Context.getSystemService("uimode"), ServiceManager.getService("uimode")
- 实现：NORMAL/night来自Resources配置；单一fetcher非完整Android系统服务
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-system-service-gap/provided-services.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U9 source-inventory, must cross-check deployed238ffc14；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：该来源曾低估部署B8层；机制描述只用于列明底线，不能照此判所有当前服务缺失；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [provided-services.md](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/provided-services.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `a234155bc216e38633ceb22614123e79725503f60143a5f15c499a09f3d72d41`
- [README.md](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/README.md>)：修正旧源码快照与实际部署jar不一致的限制；SHA256 `cf4e2c528dff6d601e7acb430cf1909fb19679f97adb6227ac4fcbf24d43844c`

### JAVA-048

**content兼容底线** · 系统服务

- 成员：Context.getSystemService("content"), ServiceManager.getService("content")
- 实现：observer生命周期no-op，sync默认空；单一fetcher非完整Android系统服务
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-system-service-gap/provided-services.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U9 source-inventory, must cross-check deployed238ffc14；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：该来源曾低估部署B8层；机制描述只用于列明底线，不能照此判所有当前服务缺失；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [provided-services.md](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/provided-services.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `a234155bc216e38633ceb22614123e79725503f60143a5f15c499a09f3d72d41`
- [README.md](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/README.md>)：修正旧源码快照与实际部署jar不一致的限制；SHA256 `cf4e2c528dff6d601e7acb430cf1909fb19679f97adb6227ac4fcbf24d43844c`

### JAVA-049

**audio兼容底线** · 系统服务

- 成员：Context.getSystemService("audio"), ServiceManager.getService("audio")
- 实现：IAudioService类型零，不提供AudioFlinger；单一fetcher非完整Android系统服务
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-system-service-gap/provided-services.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U9 source-inventory, must cross-check deployed238ffc14；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：该来源曾低估部署B8层；机制描述只用于列明底线，不能照此判所有当前服务缺失；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [provided-services.md](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/provided-services.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `a234155bc216e38633ceb22614123e79725503f60143a5f15c499a09f3d72d41`
- [README.md](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/README.md>)：修正旧源码快照与实际部署jar不一致的限制；SHA256 `cf4e2c528dff6d601e7acb430cf1909fb19679f97adb6227ac4fcbf24d43844c`

### JAVA-050

**storage兼容底线** · 系统服务

- 成员：Context.getSystemService("storage"), ServiceManager.getService("mount")
- 实现：IStorageManager报告一个volume；其他事务空值可能造成cacheQuota=0；单一fetcher非完整Android系统服务
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-system-service-gap/provided-services.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U9 source-inventory, must cross-check deployed238ffc14；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：该来源曾低估部署B8层；机制描述只用于列明底线，不能照此判所有当前服务缺失；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [provided-services.md](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/provided-services.md>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `a234155bc216e38633ceb22614123e79725503f60143a5f15c499a09f3d72d41`
- [README.md](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/README.md>)：修正旧源码快照与实际部署jar不一致的限制；SHA256 `cf4e2c528dff6d601e7acb430cf1909fb19679f97adb6227ac4fcbf24d43844c`

### JAVA-051

**appops部署注册** · 系统服务

- 成员：Context.getSystemService("appops"), ServiceManager.getService("appops")
- 实现：B8BindExtras.SERVICES反射sCache；清单只证明注册路径，未证明全方法功能
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-system-service-gap/deployed-providers.csv
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U9 deployed JAR238ffc14；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：binder非空/注册存在不能冒充真实backend与功能验证；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [deployed-providers.csv](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/deployed-providers.csv>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `0abdaca0010714b97796cf7a73fa7c64938eb24004c0d140940e99d120d8c47b`

### JAVA-052

**locale部署注册** · 系统服务

- 成员：Context.getSystemService("locale"), ServiceManager.getService("locale")
- 实现：B8BindExtras.SERVICES反射sCache；清单只证明注册路径，未证明全方法功能
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-system-service-gap/deployed-providers.csv
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U9 deployed JAR238ffc14；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：binder非空/注册存在不能冒充真实backend与功能验证；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [deployed-providers.csv](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/deployed-providers.csv>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `0abdaca0010714b97796cf7a73fa7c64938eb24004c0d140940e99d120d8c47b`

### JAVA-053

**notification部署注册** · 系统服务

- 成员：Context.getSystemService("notification"), ServiceManager.getService("notification")
- 实现：B8BindExtras.SERVICES类型安全binder；清单只证明注册路径，未证明全方法功能
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-system-service-gap/deployed-providers.csv
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U9 deployed JAR238ffc14；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：binder非空/注册存在不能冒充真实backend与功能验证；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [deployed-providers.csv](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/deployed-providers.csv>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `0abdaca0010714b97796cf7a73fa7c64938eb24004c0d140940e99d120d8c47b`

### JAVA-054

**shortcut部署注册** · 系统服务

- 成员：Context.getSystemService("shortcut"), ServiceManager.getService("shortcut")
- 实现：WlShortcutService native接线install；清单只证明注册路径，未证明全方法功能
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-system-service-gap/deployed-providers.csv
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U9 deployed JAR238ffc14；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：binder非空/注册存在不能冒充真实backend与功能验证；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [deployed-providers.csv](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/deployed-providers.csv>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `0abdaca0010714b97796cf7a73fa7c64938eb24004c0d140940e99d120d8c47b`

### JAVA-055

**media_session部署注册** · 系统服务

- 成员：Context.getSystemService("media_session"), ServiceManager.getService("media_session")
- 实现：WlMediaSession+fetcher；mService stub；清单只证明注册路径，未证明全方法功能
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-system-service-gap/deployed-providers.csv
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U9 deployed JAR238ffc14；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：binder非空/注册存在不能冒充真实backend与功能验证；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [deployed-providers.csv](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/deployed-providers.csv>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `0abdaca0010714b97796cf7a73fa7c64938eb24004c0d140940e99d120d8c47b`

### JAVA-056

**power_exemption部署注册** · 系统服务

- 成员：Context.getSystemService("power_exemption"), ServiceManager.getService("power_exemption")
- 实现：manager+mService stub；清单只证明注册路径，未证明全方法功能
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-system-service-gap/deployed-providers.csv
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U9 deployed JAR238ffc14；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：binder非空/注册存在不能冒充真实backend与功能验证；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [deployed-providers.csv](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/deployed-providers.csv>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `0abdaca0010714b97796cf7a73fa7c64938eb24004c0d140940e99d120d8c47b`

### JAVA-057

**restrictions部署注册** · 系统服务

- 成员：Context.getSystemService("restrictions"), ServiceManager.getService("restrictions")
- 实现：empty-Bundle service；清单只证明注册路径，未证明全方法功能
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-system-service-gap/deployed-providers.csv
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U9 deployed JAR238ffc14；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：binder非空/注册存在不能冒充真实backend与功能验证；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [deployed-providers.csv](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/deployed-providers.csv>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `0abdaca0010714b97796cf7a73fa7c64938eb24004c0d140940e99d120d8c47b`

### JAVA-058

**fingerprint U9缺口** · 系统服务缺口

- 成员：Context.getSystemService("fingerprint")
- 实现：U9 gap-table没有提供记录；这是当时fetcher/模块服务缺口，静态请求数量不等于实际失败数量
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-system-service-gap/gap-table.csv
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U9 only；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：不得将此历史缺口当当前版本仍缺；未报告的APK不能补验证成功；NSD类型/服务实现另拆；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [gap-table.csv](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/gap-table.csv>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `1111e740dfae48da253264e1c94b426ce42a452e6644da860c15ed97231012a2`

### JAVA-059

**biometric U9缺口** · 系统服务缺口

- 成员：Context.getSystemService("biometric")
- 实现：U9 gap-table没有提供记录；这是当时fetcher/模块服务缺口，静态请求数量不等于实际失败数量
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-system-service-gap/gap-table.csv
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U9 only；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：不得将此历史缺口当当前版本仍缺；未报告的APK不能补验证成功；NSD类型/服务实现另拆；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [gap-table.csv](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/gap-table.csv>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `1111e740dfae48da253264e1c94b426ce42a452e6644da860c15ed97231012a2`

### JAVA-060

**media_metrics U9缺口** · 系统服务缺口

- 成员：Context.getSystemService("media_metrics")
- 实现：U9 gap-table没有提供记录；这是当时fetcher/模块服务缺口，静态请求数量不等于实际失败数量
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-system-service-gap/gap-table.csv
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U9 only；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：不得将此历史缺口当当前版本仍缺；未报告的APK不能补验证成功；NSD类型/服务实现另拆；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [gap-table.csv](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/gap-table.csv>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `1111e740dfae48da253264e1c94b426ce42a452e6644da860c15ed97231012a2`

### JAVA-061

**grammatical_inflection U9缺口** · 系统服务缺口

- 成员：Context.getSystemService("grammatical_inflection")
- 实现：U9 gap-table没有提供记录；这是当时fetcher/模块服务缺口，静态请求数量不等于实际失败数量
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-system-service-gap/gap-table.csv
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U9 only；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：不得将此历史缺口当当前版本仍缺；未报告的APK不能补验证成功；NSD类型/服务实现另拆；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [gap-table.csv](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/gap-table.csv>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `1111e740dfae48da253264e1c94b426ce42a452e6644da860c15ed97231012a2`

### JAVA-062

**bluetooth U9缺口** · 系统服务缺口

- 成员：Context.getSystemService("bluetooth")
- 实现：U9 gap-table没有提供记录；这是当时fetcher/模块服务缺口，静态请求数量不等于实际失败数量
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-system-service-gap/gap-table.csv
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U9 only；部署证据：candidate
- 冻结：未登记；关联：JAVA-093, JAVA-094, JAVA-095
- 待补 / 限制：不得将此历史缺口当当前版本仍缺；未报告的APK不能补验证成功；NSD类型/服务实现另拆；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [gap-table.csv](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/gap-table.csv>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `1111e740dfae48da253264e1c94b426ce42a452e6644da860c15ed97231012a2`

### JAVA-063

**batterymanager U9缺口** · 系统服务缺口

- 成员：Context.getSystemService("batterymanager")
- 实现：U9 gap-table没有提供记录；这是当时fetcher/模块服务缺口，静态请求数量不等于实际失败数量
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-system-service-gap/gap-table.csv
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U9 only；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：不得将此历史缺口当当前版本仍缺；未报告的APK不能补验证成功；NSD类型/服务实现另拆；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [gap-table.csv](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/gap-table.csv>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `1111e740dfae48da253264e1c94b426ce42a452e6644da860c15ed97231012a2`

### JAVA-064

**storagestats U9缺口** · 系统服务缺口

- 成员：Context.getSystemService("storagestats")
- 实现：U9 gap-table没有提供记录；这是当时fetcher/模块服务缺口，静态请求数量不等于实际失败数量
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-system-service-gap/gap-table.csv
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U9 only；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：不得将此历史缺口当当前版本仍缺；未报告的APK不能补验证成功；NSD类型/服务实现另拆；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [gap-table.csv](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/gap-table.csv>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `1111e740dfae48da253264e1c94b426ce42a452e6644da860c15ed97231012a2`

### JAVA-065

**wifip2p U9缺口** · 系统服务缺口

- 成员：Context.getSystemService("wifip2p")
- 实现：U9 gap-table没有提供记录；这是当时fetcher/模块服务缺口，静态请求数量不等于实际失败数量
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-system-service-gap/gap-table.csv
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U9 only；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：不得将此历史缺口当当前版本仍缺；未报告的APK不能补验证成功；NSD类型/服务实现另拆；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [gap-table.csv](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/gap-table.csv>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `1111e740dfae48da253264e1c94b426ce42a452e6644da860c15ed97231012a2`

### JAVA-066

**usb U9缺口** · 系统服务缺口

- 成员：Context.getSystemService("usb")
- 实现：U9 gap-table没有提供记录；这是当时fetcher/模块服务缺口，静态请求数量不等于实际失败数量
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-system-service-gap/gap-table.csv
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U9 only；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：不得将此历史缺口当当前版本仍缺；未报告的APK不能补验证成功；NSD类型/服务实现另拆；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [gap-table.csv](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/gap-table.csv>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `1111e740dfae48da253264e1c94b426ce42a452e6644da860c15ed97231012a2`

### JAVA-067

**device_policy U9缺口** · 系统服务缺口

- 成员：Context.getSystemService("device_policy")
- 实现：U9 gap-table没有提供记录；这是当时fetcher/模块服务缺口，静态请求数量不等于实际失败数量
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-system-service-gap/gap-table.csv
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U9 only；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：不得将此历史缺口当当前版本仍缺；未报告的APK不能补验证成功；NSD类型/服务实现另拆；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [gap-table.csv](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/gap-table.csv>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `1111e740dfae48da253264e1c94b426ce42a452e6644da860c15ed97231012a2`

### JAVA-068

**dropbox U9缺口** · 系统服务缺口

- 成员：Context.getSystemService("dropbox")
- 实现：U9 gap-table没有提供记录；这是当时fetcher/模块服务缺口，静态请求数量不等于实际失败数量
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-system-service-gap/gap-table.csv
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U9 only；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：不得将此历史缺口当当前版本仍缺；未报告的APK不能补验证成功；NSD类型/服务实现另拆；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [gap-table.csv](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/gap-table.csv>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `1111e740dfae48da253264e1c94b426ce42a452e6644da860c15ed97231012a2`

### JAVA-069

**servicediscovery U9缺口** · 系统服务缺口

- 成员：Context.getSystemService("servicediscovery")
- 实现：U9 gap-table没有提供记录；这是当时fetcher/模块服务缺口，静态请求数量不等于实际失败数量
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-system-service-gap/gap-table.csv
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U9 only；部署证据：candidate
- 冻结：未登记；关联：JAVA-090, JAVA-091, JAVA-092
- 待补 / 限制：不得将此历史缺口当当前版本仍缺；未报告的APK不能补验证成功；NSD类型/服务实现另拆；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推；U15只补NSD类型/值对象，5行为仍unsupported且service null，不能变完整支持。

- [gap-table.csv](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/gap-table.csv>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `1111e740dfae48da253264e1c94b426ce42a452e6644da860c15ed97231012a2`

### JAVA-070

**usagestats U9缺口** · 系统服务缺口

- 成员：Context.getSystemService("usagestats")
- 实现：U9 gap-table没有提供记录；这是当时fetcher/模块服务缺口，静态请求数量不等于实际失败数量
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-system-service-gap/gap-table.csv
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U9 only；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：不得将此历史缺口当当前版本仍缺；未报告的APK不能补验证成功；NSD类型/服务实现另拆；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [gap-table.csv](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/gap-table.csv>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `1111e740dfae48da253264e1c94b426ce42a452e6644da860c15ed97231012a2`

### JAVA-071

**crossprofileapps U9缺口** · 系统服务缺口

- 成员：Context.getSystemService("crossprofileapps")
- 实现：U9 gap-table没有提供记录；这是当时fetcher/模块服务缺口，静态请求数量不等于实际失败数量
- 源码 / 产物：unknown; implementation described in benchmark/2026-10-01-system-service-gap/gap-table.csv
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U9 only；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：不得将此历史缺口当当前版本仍缺；未报告的APK不能补验证成功；NSD类型/服务实现另拆；无本项 Android 设备对照、API level/targetSdk 兼容区间直接证据；保持 unknown；当前部署是否为该历史/候选版本未核，不由最新目录名外推

- [gap-table.csv](<../../../../westlake-harness/benchmark/2026-10-01-system-service-gap/gap-table.csv>)：具体实现/边界/历史版本；本轮只读，未重判截图；SHA256 `1111e740dfae48da253264e1c94b426ce42a452e6644da860c15ed97231012a2`

### JAVA-072

**ConnectivityManager成员补全** · BCP/网络

- 成员：Landroid/net/ConnectivityManager;->addDefaultNetworkActiveListener(Landroid/net/ConnectivityManager$OnNetworkActiveListener;)V, Landroid/net/ConnectivityManager;->getAllNetworkInfo()[Landroid/net/NetworkInfo;, Landroid/net/ConnectivityManager;->getBoundNetworkForProcess()Landroid/net/Network;, Landroid/net/ConnectivityManager;->getNetworkInfo(I)Landroid/net/NetworkInfo;, Landroid/net/ConnectivityManager;->getRestrictBackgroundStatus()I, Landroid/net/ConnectivityManager;->isDefaultNetworkActive()Z, Landroid/net/ConnectivityManager;->registerDefaultNetworkCallback(Landroid/net/ConnectivityManager$NetworkCallback;Landroid/os/Handler;)V, Landroid/net/ConnectivityManager;->registerNetworkCallback(Landroid/net/NetworkRequest;Landroid/net/ConnectivityManager$NetworkCallback;Landroid/os/Handler;)V, Landroid/net/ConnectivityManager;->removeDefaultNetworkActiveListener(Landroid/net/ConnectivityManager$OnNetworkActiveListener;)V, Landroid/net/ConnectivityManager;->reportNetworkConnectivity(Landroid/net/Network;Z)V, Landroid/net/ConnectivityManager;->requestNetwork(Landroid/net/NetworkRequest;Landroid/net/ConnectivityManager$NetworkCallback;I)V
- 实现：Handler/timeout overload委托已存在方法；从active network派生info/active；listeners no-op、restriction固定DISABLED；不是完整网络管理
- 源码 / 产物：benchmark/2026-10-02-android-net-stub-members/donor/android/net/ConnectivityManager.java
- Android 源码：AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：138新增members是静态链接覆盖，不是138个功能实测；其它缺失members48项仍在扫描残表，未分类为实现；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `ddac1392df77f58b09de036a0d9f3cfc5960c725dc7609f1529f40dbac977a0a`
- [ConnectivityManager.java](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/donor/android/net/ConnectivityManager.java>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `245d35c0855aedbb498d29f99b5a44a1da13cbfae49f0c9c95b8defe08950ce5`
- [members.tsv](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/members.tsv>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `e9fc0b1282daf61079ff6d4f906abc124d5d2c3ea03e7666fd2a0341f8af2c31`
- [receipt-u12r2.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-java-walls/gates/receipt-u12r2.json>)：U12r2完整JAR SHA/源指纹/构建，非当前部署声明；SHA256 `b1182a8a3b57443d0f57788b81679dccde88298282d0fbe39ae8330ff6b85bd4`

### JAVA-073

**InetAddresses成员补全** · BCP/网络

- 成员：Landroid/net/InetAddresses;->parseNumericAddress(Ljava/lang/String;)Ljava/net/InetAddress;, Landroid/net/InetAddresses;->isNumericAddress(Ljava/lang/String;)Z
- 实现：parseNumericAddress按AOSP数值IP解析入口；不等同DNS/绑定网络语义
- 源码 / 产物：benchmark/2026-10-02-android-net-stub-members/donor/android/net/InetAddresses.java
- Android 源码：AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：138新增members是静态链接覆盖，不是138个功能实测；其它缺失members48项仍在扫描残表，未分类为实现；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `ddac1392df77f58b09de036a0d9f3cfc5960c725dc7609f1529f40dbac977a0a`
- [InetAddresses.java](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/donor/android/net/InetAddresses.java>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `ecbcdc924b0422d2ff9489fbfa05db111cf396b69f8afac36b6fe1a70bffd6c5`
- [members.tsv](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/members.tsv>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `e9fc0b1282daf61079ff6d4f906abc124d5d2c3ea03e7666fd2a0341f8af2c31`
- [receipt-u12r2.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-java-walls/gates/receipt-u12r2.json>)：U12r2完整JAR SHA/源指纹/构建，非当前部署声明；SHA256 `b1182a8a3b57443d0f57788b81679dccde88298282d0fbe39ae8330ff6b85bd4`

### JAVA-074

**IpPrefix成员补全** · BCP/网络

- 成员：Landroid/net/IpPrefix;->getAddress()Ljava/net/InetAddress;, Landroid/net/IpPrefix;->getPrefixLength()I
- 实现：无后备状态时default getter；非完整前缀语义
- 源码 / 产物：benchmark/2026-10-02-android-net-stub-members/donor/android/net/IpPrefix.java
- Android 源码：AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：138新增members是静态链接覆盖，不是138个功能实测；其它缺失members48项仍在扫描残表，未分类为实现；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `ddac1392df77f58b09de036a0d9f3cfc5960c725dc7609f1529f40dbac977a0a`
- [IpPrefix.java](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/donor/android/net/IpPrefix.java>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `70abfc4eb9b0fab89d45441dd6cdcc3c77cde875e132cf0c7afd3b398679e820`
- [members.tsv](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/members.tsv>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `e9fc0b1282daf61079ff6d4f906abc124d5d2c3ea03e7666fd2a0341f8af2c31`
- [receipt-u12r2.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-java-walls/gates/receipt-u12r2.json>)：U12r2完整JAR SHA/源指纹/构建，非当前部署声明；SHA256 `b1182a8a3b57443d0f57788b81679dccde88298282d0fbe39ae8330ff6b85bd4`

### JAVA-075

**LinkAddress成员补全** · BCP/网络

- 成员：Landroid/net/LinkAddress;->getAddress()Ljava/net/InetAddress;
- 实现：无后备状态时default getter
- 源码 / 产物：benchmark/2026-10-02-android-net-stub-members/donor/android/net/LinkAddress.java
- Android 源码：AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：138新增members是静态链接覆盖，不是138个功能实测；其它缺失members48项仍在扫描残表，未分类为实现；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `ddac1392df77f58b09de036a0d9f3cfc5960c725dc7609f1529f40dbac977a0a`
- [LinkAddress.java](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/donor/android/net/LinkAddress.java>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `364dec577131ea5cfcdb3e453198a2246406be7bdf1b7e47798f74d0265d5d71`
- [members.tsv](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/members.tsv>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `e9fc0b1282daf61079ff6d4f906abc124d5d2c3ea03e7666fd2a0341f8af2c31`
- [receipt-u12r2.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-java-walls/gates/receipt-u12r2.json>)：U12r2完整JAR SHA/源指纹/构建，非当前部署声明；SHA256 `b1182a8a3b57443d0f57788b81679dccde88298282d0fbe39ae8330ff6b85bd4`

### JAVA-076

**LinkProperties成员补全** · BCP/网络

- 成员：Landroid/net/LinkProperties;->getDnsServers()Ljava/util/List;, Landroid/net/LinkProperties;->getDomains()Ljava/lang/String;, Landroid/net/LinkProperties;->getLinkAddresses()Ljava/util/List;, Landroid/net/LinkProperties;->getPrivateDnsServerName()Ljava/lang/String;, Landroid/net/LinkProperties;->getRoutes()Ljava/util/List;, Landroid/net/LinkProperties;->isPrivateDnsActive()Z, Landroid/net/LinkProperties;->getInterfaceName()Ljava/lang/String;, Landroid/net/LinkProperties;->getDhcpServerAddress()Ljava/net/Inet4Address;, Landroid/net/LinkProperties;->getHttpProxy()Landroid/net/ProxyInfo;
- 实现：默认构造对象空list/null；无真实链路枚举
- 源码 / 产物：benchmark/2026-10-02-android-net-stub-members/donor/android/net/LinkProperties.java
- Android 源码：AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：138新增members是静态链接覆盖，不是138个功能实测；其它缺失members48项仍在扫描残表，未分类为实现；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `ddac1392df77f58b09de036a0d9f3cfc5960c725dc7609f1529f40dbac977a0a`
- [LinkProperties.java](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/donor/android/net/LinkProperties.java>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `89cebf30f3072bb7c2d278c13e35119e55dfe23617ee08fa60ceadd540021e93`
- [members.tsv](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/members.tsv>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `e9fc0b1282daf61079ff6d4f906abc124d5d2c3ea03e7666fd2a0341f8af2c31`
- [receipt-u12r2.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-java-walls/gates/receipt-u12r2.json>)：U12r2完整JAR SHA/源指纹/构建，非当前部署声明；SHA256 `b1182a8a3b57443d0f57788b81679dccde88298282d0fbe39ae8330ff6b85bd4`

### JAVA-077

**Network成员补全** · BCP/网络

- 成员：Landroid/net/Network;->bindSocket(Ljava/net/Socket;)V, Landroid/net/Network;->fromNetworkHandle(J)Landroid/net/Network;, Landroid/net/Network;->getAllByName(Ljava/lang/String;)[Ljava/net/InetAddress;, Landroid/net/Network;->getNetworkHandle()J, Landroid/net/Network;->openConnection(Ljava/net/URL;)Ljava/net/URLConnection;, Landroid/net/Network;->getSocketFactory()Ljavax/net/SocketFactory;
- 实现：default-network URL/socket/DNS；handle为NETID_UNSET0，fromNetworkHandle校验；不绑定真实netId
- 源码 / 产物：benchmark/2026-10-02-android-net-stub-members/donor/android/net/Network.java
- Android 源码：AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：138新增members是静态链接覆盖，不是138个功能实测；其它缺失members48项仍在扫描残表，未分类为实现；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `ddac1392df77f58b09de036a0d9f3cfc5960c725dc7609f1529f40dbac977a0a`
- [Network.java](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/donor/android/net/Network.java>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `a6dce9bbbb3e84c0baf216f50eefedec6da97422be65e6db74c27150d4370ed4`
- [members.tsv](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/members.tsv>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `e9fc0b1282daf61079ff6d4f906abc124d5d2c3ea03e7666fd2a0341f8af2c31`
- [receipt-u12r2.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-java-walls/gates/receipt-u12r2.json>)：U12r2完整JAR SHA/源指纹/构建，非当前部署声明；SHA256 `b1182a8a3b57443d0f57788b81679dccde88298282d0fbe39ae8330ff6b85bd4`

### JAVA-078

**NetworkCapabilities成员补全** · BCP/网络

- 成员：Landroid/net/NetworkCapabilities;->getTransportInfo()Landroid/net/TransportInfo;
- 实现：缺状态时默认null TransportInfo等，不当真实能力探测
- 源码 / 产物：benchmark/2026-10-02-android-net-stub-members/donor/android/net/NetworkCapabilities.java
- Android 源码：AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：138新增members是静态链接覆盖，不是138个功能实测；其它缺失members48项仍在扫描残表，未分类为实现；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `ddac1392df77f58b09de036a0d9f3cfc5960c725dc7609f1529f40dbac977a0a`
- [NetworkCapabilities.java](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/donor/android/net/NetworkCapabilities.java>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `3beb996ca5383705276f55fbf003b248aded7a1f8d5ec6c1c43dcdd470fe1b54`
- [members.tsv](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/members.tsv>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `e9fc0b1282daf61079ff6d4f906abc124d5d2c3ea03e7666fd2a0341f8af2c31`
- [receipt-u12r2.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-java-walls/gates/receipt-u12r2.json>)：U12r2完整JAR SHA/源指纹/构建，非当前部署声明；SHA256 `b1182a8a3b57443d0f57788b81679dccde88298282d0fbe39ae8330ff6b85bd4`

### JAVA-079

**NetworkInfo$DetailedState成员补全** · BCP/网络

- 成员：Landroid/net/NetworkInfo$DetailedState;->BLOCKED:Landroid/net/NetworkInfo$DetailedState;, Landroid/net/NetworkInfo$DetailedState;->CONNECTING:Landroid/net/NetworkInfo$DetailedState;, Landroid/net/NetworkInfo$DetailedState;->IDLE:Landroid/net/NetworkInfo$DetailedState;, Landroid/net/NetworkInfo$DetailedState;->SCANNING:Landroid/net/NetworkInfo$DetailedState;, Landroid/net/NetworkInfo$DetailedState;->AUTHENTICATING:Landroid/net/NetworkInfo$DetailedState;, Landroid/net/NetworkInfo$DetailedState;->OBTAINING_IPADDR:Landroid/net/NetworkInfo$DetailedState;, Landroid/net/NetworkInfo$DetailedState;->CONNECTED:Landroid/net/NetworkInfo$DetailedState;, Landroid/net/NetworkInfo$DetailedState;->SUSPENDED:Landroid/net/NetworkInfo$DetailedState;, Landroid/net/NetworkInfo$DetailedState;->DISCONNECTING:Landroid/net/NetworkInfo$DetailedState;, Landroid/net/NetworkInfo$DetailedState;->DISCONNECTED:Landroid/net/NetworkInfo$DetailedState;, Landroid/net/NetworkInfo$DetailedState;->FAILED:Landroid/net/NetworkInfo$DetailedState;, Landroid/net/NetworkInfo$DetailedState;->VERIFYING_POOR_LINK:Landroid/net/NetworkInfo$DetailedState;, Landroid/net/NetworkInfo$DetailedState;->CAPTIVE_PORTAL_CHECK:Landroid/net/NetworkInfo$DetailedState;
- 实现：13个AOSP常量名与==实例比较；保留plain class，不重塑为Enum
- 源码 / 产物：benchmark/2026-10-02-android-net-stub-members/donor/android/net/NetworkInfo.java
- Android 源码：AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：138新增members是静态链接覆盖，不是138个功能实测；其它缺失members48项仍在扫描残表，未分类为实现；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `ddac1392df77f58b09de036a0d9f3cfc5960c725dc7609f1529f40dbac977a0a`
- [NetworkInfo.java](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/donor/android/net/NetworkInfo.java>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `f04ad8c7353c59336ce61930442e7845a84e58356e518707d44d9f58692926e4`
- [members.tsv](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/members.tsv>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `e9fc0b1282daf61079ff6d4f906abc124d5d2c3ea03e7666fd2a0341f8af2c31`
- [receipt-u12r2.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-java-walls/gates/receipt-u12r2.json>)：U12r2完整JAR SHA/源指纹/构建，非当前部署声明；SHA256 `b1182a8a3b57443d0f57788b81679dccde88298282d0fbe39ae8330ff6b85bd4`

### JAVA-080

**NetworkInfo成员补全** · BCP/网络

- 成员：Landroid/net/NetworkInfo;->getDetailedState()Landroid/net/NetworkInfo$DetailedState;, Landroid/net/NetworkInfo;->getExtraInfo()Ljava/lang/String;, Landroid/net/NetworkInfo;->getReason()Ljava/lang/String;, Landroid/net/NetworkInfo;->getSubtype()I, Landroid/net/NetworkInfo;->getSubtypeName()Ljava/lang/String;, Landroid/net/NetworkInfo;->getTypeName()Ljava/lang/String;, Landroid/net/NetworkInfo;->isFailover()Z
- 实现：从虚getType/isConnected派生typeName/detailedState；subtype固定UNKNOWN；其余空/默认
- 源码 / 产物：benchmark/2026-10-02-android-net-stub-members/donor/android/net/NetworkInfo.java
- Android 源码：AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：138新增members是静态链接覆盖，不是138个功能实测；其它缺失members48项仍在扫描残表，未分类为实现；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `ddac1392df77f58b09de036a0d9f3cfc5960c725dc7609f1529f40dbac977a0a`
- [NetworkInfo.java](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/donor/android/net/NetworkInfo.java>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `f04ad8c7353c59336ce61930442e7845a84e58356e518707d44d9f58692926e4`
- [members.tsv](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/members.tsv>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `e9fc0b1282daf61079ff6d4f906abc124d5d2c3ea03e7666fd2a0341f8af2c31`
- [receipt-u12r2.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-java-walls/gates/receipt-u12r2.json>)：U12r2完整JAR SHA/源指纹/构建，非当前部署声明；SHA256 `b1182a8a3b57443d0f57788b81679dccde88298282d0fbe39ae8330ff6b85bd4`

### JAVA-081

**RouteInfo成员补全** · BCP/网络

- 成员：Landroid/net/RouteInfo;->getDestination()Landroid/net/IpPrefix;, Landroid/net/RouteInfo;->getGateway()Ljava/net/InetAddress;, Landroid/net/RouteInfo;->getInterface()Ljava/lang/String;
- 实现：默认对象null字段；非真实路由表
- 源码 / 产物：benchmark/2026-10-02-android-net-stub-members/donor/android/net/RouteInfo.java
- Android 源码：AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：138新增members是静态链接覆盖，不是138个功能实测；其它缺失members48项仍在扫描残表，未分类为实现；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `ddac1392df77f58b09de036a0d9f3cfc5960c725dc7609f1529f40dbac977a0a`
- [RouteInfo.java](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/donor/android/net/RouteInfo.java>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `2ca1cc0a8b0ada39d296356adbb5f280c09807da626cae92940328cbbb32e4f0`
- [members.tsv](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/members.tsv>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `e9fc0b1282daf61079ff6d4f906abc124d5d2c3ea03e7666fd2a0341f8af2c31`
- [receipt-u12r2.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-java-walls/gates/receipt-u12r2.json>)：U12r2完整JAR SHA/源指纹/构建，非当前部署声明；SHA256 `b1182a8a3b57443d0f57788b81679dccde88298282d0fbe39ae8330ff6b85bd4`

### JAVA-082

**TrafficStats成员补全** · BCP/网络

- 成员：Landroid/net/TrafficStats;->getMobileRxBytes()J, Landroid/net/TrafficStats;->getMobileTxBytes()J, Landroid/net/TrafficStats;->getThreadStatsTag()I, Landroid/net/TrafficStats;->getThreadStatsUid()I, Landroid/net/TrafficStats;->getTotalRxBytes()J, Landroid/net/TrafficStats;->getTotalTxBytes()J, Landroid/net/TrafficStats;->getUidRxBytes(I)J, Landroid/net/TrafficStats;->getUidTxBytes(I)J, Landroid/net/TrafficStats;->tagSocket(Ljava/net/Socket;)V, Landroid/net/TrafficStats;->clearThreadStatsTag()V, Landroid/net/TrafficStats;->incrementOperationCount(I)V, Landroid/net/TrafficStats;->incrementOperationCount(II)V, Landroid/net/TrafficStats;->tagDatagramSocket(Ljava/net/DatagramSocket;)V, Landroid/net/TrafficStats;->untagDatagramSocket(Ljava/net/DatagramSocket;)V, Landroid/net/TrafficStats;->untagSocket(Ljava/net/Socket;)V
- 实现：统计计数/uid/tag返回-1，tag/untag/operationcount no-op；没有流量采集
- 源码 / 产物：benchmark/2026-10-02-android-net-stub-members/donor/android/net/TrafficStats.java
- Android 源码：AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：138新增members是静态链接覆盖，不是138个功能实测；其它缺失members48项仍在扫描残表，未分类为实现；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `ddac1392df77f58b09de036a0d9f3cfc5960c725dc7609f1529f40dbac977a0a`
- [TrafficStats.java](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/donor/android/net/TrafficStats.java>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `67f92ea75f14d770016b8aff6e325df320db19b3ecb7534e20a87488b77f4786`
- [members.tsv](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/members.tsv>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `e9fc0b1282daf61079ff6d4f906abc124d5d2c3ea03e7666fd2a0341f8af2c31`
- [receipt-u12r2.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-java-walls/gates/receipt-u12r2.json>)：U12r2完整JAR SHA/源指纹/构建，非当前部署声明；SHA256 `b1182a8a3b57443d0f57788b81679dccde88298282d0fbe39ae8330ff6b85bd4`

### JAVA-083

**ScanResult成员补全** · BCP/网络

- 成员：Landroid/net/wifi/ScanResult;-><init>(Landroid/net/wifi/ScanResult;)V, Landroid/net/wifi/ScanResult;->BSSID:Ljava/lang/String;, Landroid/net/wifi/ScanResult;->SSID:Ljava/lang/String;, Landroid/net/wifi/ScanResult;->capabilities:Ljava/lang/String;, Landroid/net/wifi/ScanResult;->frequency:I, Landroid/net/wifi/ScanResult;->level:I, Landroid/net/wifi/ScanResult;->timestamp:J, Landroid/net/wifi/ScanResult;->venueName:Ljava/lang/CharSequence;, Landroid/net/wifi/ScanResult;->centerFreq0:I, Landroid/net/wifi/ScanResult;->channelWidth:I
- 实现：补public字段及复制构造签名；并不实现扫描
- 源码 / 产物：benchmark/2026-10-02-android-net-stub-members/donor/android/net/wifi/ScanResult.java
- Android 源码：AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：138新增members是静态链接覆盖，不是138个功能实测；其它缺失members48项仍在扫描残表，未分类为实现；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `ddac1392df77f58b09de036a0d9f3cfc5960c725dc7609f1529f40dbac977a0a`
- [ScanResult.java](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/donor/android/net/wifi/ScanResult.java>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `f876d0b07b03e690b980cdd6162dc06b0ae201756b8ee36fd9b6d088095e530d`
- [members.tsv](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/members.tsv>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `e9fc0b1282daf61079ff6d4f906abc124d5d2c3ea03e7666fd2a0341f8af2c31`
- [receipt-u12r2.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-java-walls/gates/receipt-u12r2.json>)：U12r2完整JAR SHA/源指纹/构建，非当前部署声明；SHA256 `b1182a8a3b57443d0f57788b81679dccde88298282d0fbe39ae8330ff6b85bd4`

### JAVA-084

**WifiInfo成员补全** · BCP/网络

- 成员：Landroid/net/wifi/WifiInfo;->describeContents()I, Landroid/net/wifi/WifiInfo;->getAffiliatedMloLinks()Ljava/util/List;, Landroid/net/wifi/WifiInfo;->getApMldMacAddress()Landroid/net/MacAddress;, Landroid/net/wifi/WifiInfo;->getApMloLinkId()I, Landroid/net/wifi/WifiInfo;->getApplicableRedactions()J, Landroid/net/wifi/WifiInfo;->getAssociatedMloLinks()Ljava/util/List;, Landroid/net/wifi/WifiInfo;->getBSSID()Ljava/lang/String;, Landroid/net/wifi/WifiInfo;->getCurrentSecurityType()I, Landroid/net/wifi/WifiInfo;->getFrequency()I, Landroid/net/wifi/WifiInfo;->getHiddenSSID()Z, Landroid/net/wifi/WifiInfo;->getInformationElements()Ljava/util/List;, Landroid/net/wifi/WifiInfo;->getIpAddress()I, Landroid/net/wifi/WifiInfo;->getLinkSpeed()I, Landroid/net/wifi/WifiInfo;->getMacAddress()Ljava/lang/String;, Landroid/net/wifi/WifiInfo;->getMaxSupportedRxLinkSpeedMbps()I, Landroid/net/wifi/WifiInfo;->getMaxSupportedTxLinkSpeedMbps()I, Landroid/net/wifi/WifiInfo;->getNetworkId()I, Landroid/net/wifi/WifiInfo;->getPasspointFqdn()Ljava/lang/String;, Landroid/net/wifi/WifiInfo;->getPasspointProviderFriendlyName()Ljava/lang/String;, Landroid/net/wifi/WifiInfo;->getRssi()I, Landroid/net/wifi/WifiInfo;->getRxLinkSpeedMbps()I, Landroid/net/wifi/WifiInfo;->getSSID()Ljava/lang/String;, Landroid/net/wifi/WifiInfo;->getSubscriptionId()I, Landroid/net/wifi/WifiInfo;->getSupplicantState()Landroid/net/wifi/SupplicantState;, Landroid/net/wifi/WifiInfo;->getTxLinkSpeedMbps()I, Landroid/net/wifi/WifiInfo;->getWifiStandard()I, Landroid/net/wifi/WifiInfo;->isRestricted()Z, Landroid/net/wifi/WifiInfo;->makeCopy(J)Landroid/net/wifi/WifiInfo;, Landroid/net/wifi/WifiInfo;->writeToParcel(Landroid/os/Parcel;I)V
- 实现：默认未连接对象、unknown ssid/INVALID_RSSI/redactions；不是真WiFi状态
- 源码 / 产物：benchmark/2026-10-02-android-net-stub-members/donor/android/net/wifi/WifiInfo.java
- Android 源码：AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：138新增members是静态链接覆盖，不是138个功能实测；其它缺失members48项仍在扫描残表，未分类为实现；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `ddac1392df77f58b09de036a0d9f3cfc5960c725dc7609f1529f40dbac977a0a`
- [WifiInfo.java](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/donor/android/net/wifi/WifiInfo.java>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `eb4d246a604e244c0527190698ffa2318f67b522b54dfef817a64b7e3ba5e3bc`
- [members.tsv](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/members.tsv>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `e9fc0b1282daf61079ff6d4f906abc124d5d2c3ea03e7666fd2a0341f8af2c31`
- [receipt-u12r2.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-java-walls/gates/receipt-u12r2.json>)：U12r2完整JAR SHA/源指纹/构建，非当前部署声明；SHA256 `b1182a8a3b57443d0f57788b81679dccde88298282d0fbe39ae8330ff6b85bd4`

### JAVA-085

**WifiManager成员补全** · BCP/网络

- 成员：Landroid/net/wifi/WifiManager;->addSuggestionConnectionStatusListener(Ljava/util/concurrent/Executor;Landroid/net/wifi/WifiManager$SuggestionConnectionStatusListener;)V, Landroid/net/wifi/WifiManager;->calculateSignalLevel(II)I, Landroid/net/wifi/WifiManager;->createMulticastLock(Ljava/lang/String;)Landroid/net/wifi/WifiManager$MulticastLock;, Landroid/net/wifi/WifiManager;->createWifiLock(Ljava/lang/String;)Landroid/net/wifi/WifiManager$WifiLock;, Landroid/net/wifi/WifiManager;->getConfiguredNetworks()Ljava/util/List;, Landroid/net/wifi/WifiManager;->getConnectionInfo()Landroid/net/wifi/WifiInfo;, Landroid/net/wifi/WifiManager;->getDhcpInfo()Landroid/net/DhcpInfo;, Landroid/net/wifi/WifiManager;->getScanResults()Ljava/util/List;, Landroid/net/wifi/WifiManager;->getWifiState()I, Landroid/net/wifi/WifiManager;->isWifiEnabled()Z, Landroid/net/wifi/WifiManager;->setWifiEnabled(Z)Z, Landroid/net/wifi/WifiManager;->startScan()Z, Landroid/net/wifi/WifiManager;->createWifiLock(ILjava/lang/String;)Landroid/net/wifi/WifiManager$WifiLock;, Landroid/net/wifi/WifiManager;->is5GHzBandSupported()Z, Landroid/net/wifi/WifiManager;->is6GHzBandSupported()Z
- 实现：无IWifiManager时默认值/空list；无radio扫描/锁/开关实际效果
- 源码 / 产物：benchmark/2026-10-02-android-net-stub-members/donor/android/net/wifi/WifiManager.java
- Android 源码：AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：138新增members是静态链接覆盖，不是138个功能实测；其它缺失members48项仍在扫描残表，未分类为实现；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `ddac1392df77f58b09de036a0d9f3cfc5960c725dc7609f1529f40dbac977a0a`
- [WifiManager.java](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/donor/android/net/wifi/WifiManager.java>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `282daa1c8b20ef25d177f26d7060d75c20e2244a2b7453d4faf7cabcf305356a`
- [members.tsv](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/members.tsv>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `e9fc0b1282daf61079ff6d4f906abc124d5d2c3ea03e7666fd2a0341f8af2c31`
- [receipt-u12r2.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-java-walls/gates/receipt-u12r2.json>)：U12r2完整JAR SHA/源指纹/构建，非当前部署声明；SHA256 `b1182a8a3b57443d0f57788b81679dccde88298282d0fbe39ae8330ff6b85bd4`

### JAVA-086

**NetworkRequest成员补全** · BCP/网络

- 成员：Landroid/net/NetworkRequest;->getCapabilities()[I, Landroid/net/NetworkRequest;->getTransportTypes()[I, Landroid/net/NetworkRequest;->hasCapability(I)Z, Landroid/net/NetworkRequest;->hasTransport(I)Z, Landroid/net/NetworkRequest;->canBeSatisfiedBy(Landroid/net/NetworkCapabilities;)Z
- 实现：无要求请求的默认逻辑；不是完整request注册或匹配状态
- 源码 / 产物：benchmark/2026-10-02-android-net-stub-members/donor/android/net/NetworkRequest.java
- Android 源码：AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：138新增members是静态链接覆盖，不是138个功能实测；其它缺失members48项仍在扫描残表，未分类为实现；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `ddac1392df77f58b09de036a0d9f3cfc5960c725dc7609f1529f40dbac977a0a`
- [NetworkRequest.java](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/donor/android/net/NetworkRequest.java>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `7f616f13b6fbe4c2e1cd1bdd72cd4fc26e65ed2364b40da8139295f770c93903`
- [members.tsv](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/members.tsv>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `e9fc0b1282daf61079ff6d4f906abc124d5d2c3ea03e7666fd2a0341f8af2c31`
- [receipt-u12r2.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-java-walls/gates/receipt-u12r2.json>)：U12r2完整JAR SHA/源指纹/构建，非当前部署声明；SHA256 `b1182a8a3b57443d0f57788b81679dccde88298282d0fbe39ae8330ff6b85bd4`

### JAVA-087

**NetworkRequest$Builder成员补全** · BCP/网络

- 成员：Landroid/net/NetworkRequest$Builder;->setIncludeOtherUidNetworks(Z)Landroid/net/NetworkRequest$Builder;
- 实现：新增builder选项安全默认，不真实纳入other-UID网络
- 源码 / 产物：benchmark/2026-10-02-android-net-stub-members/donor/android/net/NetworkRequest.java
- Android 源码：AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：138新增members是静态链接覆盖，不是138个功能实测；其它缺失members48项仍在扫描残表，未分类为实现；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `ddac1392df77f58b09de036a0d9f3cfc5960c725dc7609f1529f40dbac977a0a`
- [NetworkRequest.java](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/donor/android/net/NetworkRequest.java>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `7f616f13b6fbe4c2e1cd1bdd72cd4fc26e65ed2364b40da8139295f770c93903`
- [members.tsv](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/members.tsv>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `e9fc0b1282daf61079ff6d4f906abc124d5d2c3ea03e7666fd2a0341f8af2c31`
- [receipt-u12r2.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-java-walls/gates/receipt-u12r2.json>)：U12r2完整JAR SHA/源指纹/构建，非当前部署声明；SHA256 `b1182a8a3b57443d0f57788b81679dccde88298282d0fbe39ae8330ff6b85bd4`

### JAVA-088

**WifiConfiguration成员补全** · BCP/网络

- 成员：Landroid/net/wifi/WifiConfiguration;->SSID:Ljava/lang/String;, Landroid/net/wifi/WifiConfiguration;->hiddenSSID:Z, Landroid/net/wifi/WifiConfiguration;->getHttpProxy()Landroid/net/ProxyInfo;
- 实现：成员表证明名字/签名存在；本轮未完整逐body审计，留unknown
- 源码 / 产物：benchmark/2026-10-02-android-net-stub-members/donor/android/net/wifi/WifiConfiguration.java
- Android 源码：AOSP android-14.0.0_r1 Connectivity bd692130 / Wifi82d2b854 donors+safe defaults；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：T8 base2f365a75→3a12918a; U12r2→615b8bbe lineage；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：138新增members是静态链接覆盖，不是138个功能实测；其它缺失members48项仍在扫描残表，未分类为实现；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `ddac1392df77f58b09de036a0d9f3cfc5960c725dc7609f1529f40dbac977a0a`
- [WifiConfiguration.java](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/donor/android/net/wifi/WifiConfiguration.java>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `18664c80905db42eb6a25ec9f64fea014b5b98dcc8f54e8405becf0cf245dce0`
- [members.tsv](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/members.tsv>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `e9fc0b1282daf61079ff6d4f906abc124d5d2c3ea03e7666fd2a0341f8af2c31`
- [receipt-u12r2.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-java-walls/gates/receipt-u12r2.json>)：U12r2完整JAR SHA/源指纹/构建，非当前部署声明；SHA256 `b1182a8a3b57443d0f57788b81679dccde88298282d0fbe39ae8330ff6b85bd4`

### JAVA-089

**签名依赖类新增** · BCP/网络

- 成员：Landroid/net/ConnectivityManager$OnNetworkActiveListener;, Landroid/net/DhcpInfo;, Landroid/net/DhcpInfo$1;, Landroid/net/wifi/SupplicantState;, Landroid/net/wifi/SupplicantState$1;, Landroid/net/wifi/WifiManager$WifiLock;, Landroid/net/wifi/WifiManager$MulticastLock;, Landroid/net/wifi/WifiManager$SuggestionConnectionStatusListener;
- 实现：8个签名依赖类型保证resolve；逐类型行为另见donor，不因class可load判有硬件服务
- 源码 / 产物：unknown; source/build identification missing; report benchmark/2026-10-02-android-net-stub-members/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：net-stubs-members-v1；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `ddac1392df77f58b09de036a0d9f3cfc5960c725dc7609f1529f40dbac977a0a`
- [members.tsv](<../../../../westlake-harness/benchmark/2026-10-02-android-net-stub-members/members.tsv>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `e9fc0b1282daf61079ff6d4f906abc124d5d2c3ea03e7666fd2a0341f8af2c31`

### JAVA-090

**NSD接口/监听器类型** · BCP/网络

- 成员：android.net.nsd.NsdManager$DiscoveryListener, android.net.nsd.NsdManager$RegistrationListener, android.net.nsd.NsdManager$ResolveListener
- 实现：AOSP监听器接口/默认回调保持原样，修Unresolved Reference verifier shape；不建立mdns后端
- 源码 / 产物：benchmark/2026-10-03-u15-stubs-nsd/stubs/donor/android/net/nsd/NsdManager.java
- Android 源码：android-14.0.0_r1 Connectivity bd692130；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U15 candidate94a949053ec8c5a520a9a228b64ae8adb861977f92a6b5f63fa689214c4628fe；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：immich受益只是host ART linking测试；未来libcronet墙另存；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验

- [README.md](<../../../../westlake-harness/benchmark/2026-10-03-u15-stubs-nsd/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `f91dec2dab110bb5fc5e02123e0e5597212e0de75cbc30aeb14cb0a672104bc5`
- [NsdManager.java](<../../../../westlake-harness/benchmark/2026-10-03-u15-stubs-nsd/stubs/donor/android/net/nsd/NsdManager.java>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `61c0dff8b1d92c74f2ab1b84e2897cb9b3ab90f88ef216e7c519d1a2b34aff70`
- [host-art-runs.txt](<../../../../westlake-harness/benchmark/2026-10-03-u15-stubs-nsd/evidence/host-art-runs.txt>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `e906fcb41dc37c04cc8cb8cdd96eac4c900f2dafcfa80bc25063fcb9913487b6`

### JAVA-091

**NSD服务信息值对象** · BCP/网络

- 成员：NsdServiceInfo.getServiceName(), NsdServiceInfo.setServiceType(String), NsdServiceInfo.getHost(), NsdServiceInfo.setPort(int), NsdServiceInfo.getAttributes(), NsdServiceInfo.setAttribute(String,String)
- 实现：NsdServiceInfo AOSP文件逐字采用，getter/setter/Parcelable；值对象真实，不是发现服务
- 源码 / 产物：benchmark/2026-10-03-u15-stubs-nsd/stubs/donor/android/net/nsd/NsdServiceInfo.java
- Android 源码：android-14.0.0_r1 Connectivity bd692130；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U15 candidate94a94905；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验

- [README.md](<../../../../westlake-harness/benchmark/2026-10-03-u15-stubs-nsd/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `f91dec2dab110bb5fc5e02123e0e5597212e0de75cbc30aeb14cb0a672104bc5`
- [NsdServiceInfo.java](<../../../../westlake-harness/benchmark/2026-10-03-u15-stubs-nsd/stubs/donor/android/net/nsd/NsdServiceInfo.java>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `f9173b9b7bf36aeb9b80e4990893aaa212ac51777b29399b8a730ce76a417cad`
- [host-art-runs.txt](<../../../../westlake-harness/benchmark/2026-10-03-u15-stubs-nsd/evidence/host-art-runs.txt>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `e906fcb41dc37c04cc8cb8cdd96eac4c900f2dafcfa80bc25063fcb9913487b6`

### JAVA-092

**NSD行为明确unsupported** · BCP/网络

- 成员：NsdManager.discoverServices(String,int,DiscoveryListener), NsdManager.registerService(NsdServiceInfo,int,RegistrationListener), NsdManager.resolveService(NsdServiceInfo,ResolveListener), NsdManager.stopServiceDiscovery(DiscoveryListener), NsdManager.unregisterService(RegistrationListener)
- 实现：5methods保持AOSP签名但抛UnsupportedOperationException；manager不可实例化；无服务注册
- 源码 / 产物：benchmark/2026-10-03-u15-stubs-nsd/stubs/donor/android/net/nsd/NsdManager.java
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U15 candidate94a94905；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Context.getSystemService("servicediscovery")仍null；不算mDNS已实现；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验

- [README.md](<../../../../westlake-harness/benchmark/2026-10-03-u15-stubs-nsd/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `f91dec2dab110bb5fc5e02123e0e5597212e0de75cbc30aeb14cb0a672104bc5`
- [NsdManager.java](<../../../../westlake-harness/benchmark/2026-10-03-u15-stubs-nsd/stubs/donor/android/net/nsd/NsdManager.java>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `61c0dff8b1d92c74f2ab1b84e2897cb9b3ab90f88ef216e7c519d1a2b34aff70`

### JAVA-093

**BLE callback原版类型** · BCP/蓝牙

- 成员：android.bluetooth.le.ScanCallback.onScanResult(int,ScanResult), android.bluetooth.le.ScanCallback.onBatchScanResults(List), android.bluetooth.le.ScanCallback.onScanFailed(int)
- 实现：AOSP原版abstract callback及ScanFailed annotation；空default callback是上游契约，不提供BLE扫描
- 源码 / 产物：benchmark/2026-10-03-bt-le-scancallback/stubs/donor/android/bluetooth/le/ScanCallback.java
- Android 源码：android-14.0.0_r1 Bluetooth cbb30d72；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U14 stubs87cf65cc；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：fd-plus仅历史bind缺类+候选host test；不借为实际蓝牙功能；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验

- [README.md](<../../../../westlake-harness/benchmark/2026-10-03-bt-le-scancallback/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `5d47dd3c2335bb1f80b783dc1adabfd27ba7ca8a91dfb9c850d453e0839e4805`
- [ScanCallback.java](<../../../../westlake-harness/benchmark/2026-10-03-bt-le-scancallback/stubs/donor/android/bluetooth/le/ScanCallback.java>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `eae1a43c088ebceea9f21c3f7316e886f11cd5f129132b5a47c4d37d9a68c60f`
- [bt-inventory.json](<../../../../westlake-harness/benchmark/2026-10-03-bt-le-scancallback/bt-inventory.json>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `2d40ae9233043698bf09166697c181f09292123e5ad380af6c9119903d1611b2`

### JAVA-094

**android/bluetooth/le/尚缺类型** · BCP/蓝牙缺口

- 成员：android.bluetooth.le.AdvertiseCallback, android.bluetooth.le.AdvertiseData, android.bluetooth.le.AdvertiseData$Builder, android.bluetooth.le.AdvertiseSettings, android.bluetooth.le.AdvertiseSettings$Builder, android.bluetooth.le.AdvertisingSet, android.bluetooth.le.AdvertisingSetCallback, android.bluetooth.le.AdvertisingSetParameters, android.bluetooth.le.AdvertisingSetParameters$Builder, android.bluetooth.le.BluetoothLeAdvertiser, android.bluetooth.le.BluetoothLeScanner, android.bluetooth.le.PeriodicAdvertisingParameters, android.bluetooth.le.PeriodicAdvertisingParameters$Builder, android.bluetooth.le.ScanCallback, android.bluetooth.le.ScanSettings, android.bluetooth.le.ScanSettings$Builder, android.bluetooth.le.TransportBlock, android.bluetooth.le.TransportDiscoveryData
- 实现：历史U10.1T8/U12/U13 BCP类型差集；ScanCallback后补见独立行，不泛称整个Bluetooth完整
- 源码 / 产物：unknown; source/build identification missing; report benchmark/2026-10-03-bt-le-scancallback/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：BCP2f365a75/615b8bbe vs android34 SDK；部署证据：candidate
- 冻结：未登记；关联：JAVA-093
- 待补 / 限制：缺类静态引用87keys是上界，仅fd-plus有历史缺类致命；API34在此是inventory reference，非所有API被测支持；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验；含后续已补ScanCallback的旧BCP差集，不能当U14后现态差集。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-03-bt-le-scancallback/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `5d47dd3c2335bb1f80b783dc1adabfd27ba7ca8a91dfb9c850d453e0839e4805`
- [bt-inventory.json](<../../../../westlake-harness/benchmark/2026-10-03-bt-le-scancallback/bt-inventory.json>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `2d40ae9233043698bf09166697c181f09292123e5ad380af6c9119903d1611b2`

### JAVA-095

**android/bluetooth/尚缺类型** · BCP/蓝牙缺口

- 成员：android.bluetooth.BluetoothA2dp, android.bluetooth.BluetoothAdapter, android.bluetooth.BluetoothAdapter$LeScanCallback, android.bluetooth.BluetoothAssignedNumbers, android.bluetooth.BluetoothClass, android.bluetooth.BluetoothClass$Device, android.bluetooth.BluetoothClass$Device$Major, android.bluetooth.BluetoothClass$Service, android.bluetooth.BluetoothCodecStatus, android.bluetooth.BluetoothCodecStatus$Builder, android.bluetooth.BluetoothCsipSetCoordinator, android.bluetooth.BluetoothGatt, android.bluetooth.BluetoothGattCallback, android.bluetooth.BluetoothGattCharacteristic, android.bluetooth.BluetoothGattDescriptor, android.bluetooth.BluetoothGattServer, android.bluetooth.BluetoothGattServerCallback, android.bluetooth.BluetoothGattService, android.bluetooth.BluetoothHeadset, android.bluetooth.BluetoothHealth, android.bluetooth.BluetoothHealthAppConfiguration, android.bluetooth.BluetoothHealthCallback, android.bluetooth.BluetoothHearingAid, android.bluetooth.BluetoothHidDevice, android.bluetooth.BluetoothHidDevice$Callback, android.bluetooth.BluetoothHidDeviceAppQosSettings, android.bluetooth.BluetoothHidDeviceAppSdpSettings, android.bluetooth.BluetoothLeAudio, android.bluetooth.BluetoothLeAudioCodecStatus, android.bluetooth.BluetoothManager, android.bluetooth.BluetoothProfile, android.bluetooth.BluetoothProfile$ServiceListener, android.bluetooth.BluetoothServerSocket, android.bluetooth.BluetoothSocket, android.bluetooth.BluetoothSocketException, android.bluetooth.BluetoothStatusCodes
- 实现：历史U10.1T8/U12/U13 BCP类型差集；ScanCallback后补见独立行，不泛称整个Bluetooth完整
- 源码 / 产物：unknown; source/build identification missing; report benchmark/2026-10-03-bt-le-scancallback/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：BCP2f365a75/615b8bbe vs android34 SDK；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：缺类静态引用87keys是上界，仅fd-plus有历史缺类致命；API34在此是inventory reference，非所有API被测支持；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验

- [README.md](<../../../../westlake-harness/benchmark/2026-10-03-bt-le-scancallback/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `5d47dd3c2335bb1f80b783dc1adabfd27ba7ca8a91dfb9c850d453e0839e4805`
- [bt-inventory.json](<../../../../westlake-harness/benchmark/2026-10-03-bt-le-scancallback/bt-inventory.json>)：精确源码/成员/测试或产物回执（不是部署声明）；SHA256 `2d40ae9233043698bf09166697c181f09292123e5ad380af6c9119903d1611b2`

### JAVA-096

**生命周期:task-root/本包task** · source-build / 生命周期

- 成员：Activity.isTaskRoot(), IActivityTaskManager.getTaskForActivity, getRunningTasks, getAppTasks, getRecentTasks
- 实现：记录应用的一个task，修-1/空返回；不是完整任务栈；只属于source-build/host路线，绝不套U13/128签认
- 源码 / 产物：unknown; source/build identification missing; report benchmark/2026-10-04-r84-silent-answers/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：r84 builds81/84；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验；members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-04-r84-silent-answers/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `068b14d4192fed36fa98a68079321606ec22bf39d20af1db9aa6ff11d0d799e1`

### JAVA-097

**生命周期:本进程started services** · source-build / 生命周期

- 成员：Context.startService, Context.startForegroundService, Service.onStartCommand, Context.stopService
- 实现：服务创建一次，每次start分发onStartCommand并按AOSPstop规则处理；只属于source-build/host路线，绝不套U13/128签认
- 源码 / 产物：unknown; source/build identification missing; report benchmark/2026-10-04-r84-silent-answers/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：r84 build84；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：243静态调用keys不是243功能验证；源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验；members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-04-r84-silent-answers/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `068b14d4192fed36fa98a68079321606ec22bf39d20af1db9aa6ff11d0d799e1`

### JAVA-098

**生命周期:本包broadcast** · source-build / 生命周期

- 成员：Context.registerReceiver, Context.sendBroadcast, Intent.ACTION_BATTERY_CHANGED
- 实现：保存receiver并按匹配派发本包广播；有sticky默认，不提供完整跨进程广播；只属于source-build/host路线，绝不套U13/128签认
- 源码 / 产物：unknown; source/build identification missing; report benchmark/2026-10-04-r84-silent-answers/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：r84 build84；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验；members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-04-r84-silent-answers/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `068b14d4192fed36fa98a68079321606ec22bf39d20af1db9aa6ff11d0d799e1`

### JAVA-099

**系统服务:MemoryInfo** · source-build / 系统服务

- 成员：ActivityManager.getMemoryInfo(ActivityManager.MemoryInfo)
- 实现：从/proc/meminfo与ProcessList levels填内存数据；替代不写out结构的桩；只属于source-build/host路线，绝不套U13/128签认
- 源码 / 产物：unknown; source/build identification missing; report benchmark/2026-10-04-r84-silent-answers/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：r84 build84；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验；members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-04-r84-silent-answers/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `068b14d4192fed36fa98a68079321606ec22bf39d20af1db9aa6ff11d0d799e1`

### JAVA-100

**资源:Application labelRes保持** · source-build / 资源

- 成员：ApplicationInfo.labelRes, PackageManager.getApplicationLabel(ApplicationInfo)
- 实现：不在launch清空Android资源ID，修labelRes为0的标签路径；只属于source-build/host路线，绝不套U13/128签认
- 源码 / 产物：unknown; source/build identification missing; report benchmark/2026-10-04-r84-silent-answers/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：r84 build82/83；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验；members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-04-r84-silent-answers/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `068b14d4192fed36fa98a68079321606ec22bf39d20af1db9aa6ff11d0d799e1`

### JAVA-101

**系统服务:cache quota默认** · source-build / 系统服务

- 成员：StorageManager.getCacheQuotaBytes(UUID)
- 实现：StorageStatsService以64MiB默认回答；不是实时空间配额系统；只属于source-build/host路线，绝不套U13/128签认
- 源码 / 产物：unknown; source/build identification missing; report benchmark/2026-10-04-r84-silent-answers/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：r84 build82；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验；members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-04-r84-silent-answers/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `068b14d4192fed36fa98a68079321606ec22bf39d20af1db9aa6ff11d0d799e1`

### JAVA-102

**内容提供者:authority manifest顺序** · source-build / 内容提供者

- 成员：ProviderInfo.authority, ContentProvider.attachInfo
- 实现：manifest顺序占authority，避开disabled provider抢占；只报告本包机制；只属于source-build/host路线，绝不套U13/128签认
- 源码 / 产物：unknown; source/build identification missing; report benchmark/2026-10-04-r84-silent-answers/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：r84 build82/83；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验；members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-04-r84-silent-answers/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `068b14d4192fed36fa98a68079321606ec22bf39d20af1db9aa6ff11d0d799e1`

### JAVA-103

**生命周期:异步本包launch与Intent保留** · source-build / 生命周期

- 成员：Activity.startActivity(Intent), Intent.getAction(), Intent.getComponent()
- 实现：own activity在caller当前消息后启动，传app自己的Intent而非OH前缀action；只属于source-build/host路线，绝不套U13/128签认
- 源码 / 产物：unknown; source/build identification missing; report benchmark/2026-10-04-r84-silent-answers/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：r84 builds82/84/85；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验；members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-04-r84-silent-answers/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `068b14d4192fed36fa98a68079321606ec22bf39d20af1db9aa6ff11d0d799e1`

### JAVA-104

**文件空间:libcore真实查询** · source-build / 文件空间

- 成员：java.io.File.getTotalSpace(), java.io.File.getFreeSpace(), java.io.File.getUsableSpace(), UnixFileSystem.getSpace0
- 实现：missing-natives将libcore statvfs实现覆写return0 runtime stub；JNI交叉给native shard；只属于source-build/host路线，绝不套U13/128签认
- 源码 / 产物：unknown; source/build identification missing; report benchmark/2026-10-04-r84-silent-answers/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：r84 runtime override；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：native绑定winner/TU/产物SHA需native shard补，不由Java导出推功能；源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验；members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-04-r84-silent-answers/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `068b14d4192fed36fa98a68079321606ec22bf39d20af1db9aa6ff11d0d799e1`

### JAVA-105

**资源/窗口:global Configuration** · source-build / 资源/窗口

- 成员：android.content.res.Configuration, WindowManager.getCurrentWindowMetrics()
- 实现：每窗使用display global configuration，修bind-time bounds为0；确切bridge method/TU未知；只属于source-build/host路线，绝不套U13/128签认
- 源码 / 产物：unknown; source/build identification missing; report benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：r86 builds86–90；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验；members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `8fead435a562ce14e905f13943493bfae84a0795db2c8dc16e11d67c67f81aa4`

### JAVA-106

**生命周期:本包implicit intent** · source-build / 生命周期

- 成员：Activity.startActivity(Intent), Intent.setAction(String), PackageManager.resolveActivity(Intent,int)
- 实现：为app自己activities解析implicit intents；不承诺跨app resolver完整；只属于source-build/host路线，绝不套U13/128签认
- 源码 / 产物：unknown; source/build identification missing; report benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：r86 builds86–90；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验；members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `8fead435a562ce14e905f13943493bfae84a0795db2c8dc16e11d67c67f81aa4`

### JAVA-107

**生命周期:onPostCreate与launch transaction** · source-build / 生命周期

- 成员：Activity.onPostCreate(Bundle), android.app.servertransaction.LaunchActivityItem, android.app.servertransaction.StartActivityItem
- 实现：launch transaction带start，确保onPostCreate；本地init调用链未绑定到产物；只属于source-build/host路线，绝不套U13/128签认
- 源码 / 产物：unknown; source/build identification missing; report benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：r86 builds86–90；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验；members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `8fead435a562ce14e905f13943493bfae84a0795db2c8dc16e11d67c67f81aa4`

### JAVA-108

**窗口/输入:SurfaceView焦点组** · source-build / 窗口/输入

- 成员：android.view.SurfaceView, Window.hasWindowFocus()
- 实现：父window与SurfaceViews的OH windows作为一个focus group；native部分由native shard对齐；只属于source-build/host路线，绝不套U13/128签认
- 源码 / 产物：unknown; source/build identification missing; report benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：r86 builds86–90；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验；members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `8fead435a562ce14e905f13943493bfae84a0795db2c8dc16e11d67c67f81aa4`

### JAVA-109

**权限:runtime request回调** · source-build / 权限

- 成员：Activity.requestPermissions(String[],int), Activity.onRequestPermissionsResult(int,String[],int[])
- 实现：in-process回答permission requests；报告未列所有结果/授权策略，不推成全授权；只属于source-build/host路线，绝不套U13/128签认
- 源码 / 产物：unknown; source/build identification missing; report benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：r86 builds86–90；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验；members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `8fead435a562ce14e905f13943493bfae84a0795db2c8dc16e11d67c67f81aa4`

### JAVA-110

**系统服务:Android15 CEunlock名称** · source-build / 系统服务

- 成员：android.os.IUserManager
- 实现：README只称按Android15名称回答credential-encrypted unlock；精确method名/源码尚无直接证据，不能猜；只属于source-build/host路线，绝不套U13/128签认
- 源码 / 产物：unknown; source/build identification missing; report benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：r86 builds86–90；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：精确CEunlock member名待来源补；本项保留unknown；源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验；members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `8fead435a562ce14e905f13943493bfae84a0795db2c8dc16e11d67c67f81aa4`

### JAVA-111

**生命周期:direct resume只一次** · source-build / 生命周期

- 成员：Activity.onResume(), android.app.servertransaction.ResumeActivityItem
- 实现：direct launch仅在launch transaction resume，消重复报告；只属于source-build/host路线，绝不套U13/128签认
- 源码 / 产物：unknown; source/build identification missing; report benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：r86 build92；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：build90重复resume旧行为保留为前史，不混新实现；源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验；members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `8fead435a562ce14e905f13943493bfae84a0795db2c8dc16e11d67c67f81aa4`

### JAVA-112

**权限/标识:序列号按Android拒绝** · source-build / 权限/标识

- 成员：Build.getSerial(), ServiceManager.getService("device_identifiers")
- 实现：in-process service拒getSerial并抛SecurityException，插件可catch；不伪造serial；只属于source-build/host路线，绝不套U13/128签认
- 源码 / 产物：unknown; source/build identification missing; report benchmark/2026-10-06-r87-input-gles3-and-services/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：r87 builds91–95；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验；members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-06-r87-input-gles3-and-services/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `59b7a9c9fd0651c84d247023ec62c5e8392b101bbcd17f00f991a4924fc5238f`

### JAVA-113

**系统服务:LauncherApps本用户回答** · source-build / 系统服务

- 成员：Context.getSystemService(LauncherApps.class), LauncherApps.getActivityList(String,UserHandle)
- 实现：in-process LauncherApps能枚举本用户profile/launcher；透明window仍可能只见host；只属于source-build/host路线，绝不套U13/128签认
- 源码 / 产物：unknown; source/build identification missing; report benchmark/2026-10-06-r87-input-gles3-and-services/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：r87 builds91–95；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验；members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-06-r87-input-gles3-and-services/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `59b7a9c9fd0651c84d247023ec62c5e8392b101bbcd17f00f991a4924fc5238f`

### JAVA-114

**系统服务:User profile group** · source-build / 系统服务

- 成员：UserManager.getProfileIds(int,boolean), UserManager.getUserProfiles()
- 实现：给app唯一用户profile group回答；不当多用户管理完整实现；只属于source-build/host路线，绝不套U13/128签认
- 源码 / 产物：unknown; source/build identification missing; report benchmark/2026-10-06-r87-input-gles3-and-services/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：r87 builds91–95；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验；members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-06-r87-input-gles3-and-services/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `59b7a9c9fd0651c84d247023ec62c5e8392b101bbcd17f00f991a4924fc5238f`

### JAVA-115

**安装/入口:相对Activity名展开** · source-build / 安装/入口

- 成员：android.content.pm.ActivityInfo.name
- 实现：launcher展开manifest相对package的Activity名；具体源码method待追证；只属于source-build/host路线，绝不套U13/128签认；未证明源码调用ComponentName.createRelative。
- 源码 / 产物：unknown; source/build identification missing; report benchmark/2026-10-06-r87-input-gles3-and-services/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：r87 launcher；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：ComponentName.createRelative为对应Android契约名，README不证明实现调用它；源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验；members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-06-r87-input-gles3-and-services/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `59b7a9c9fd0651c84d247023ec62c5e8392b101bbcd17f00f991a4924fc5238f`

### JAVA-116

**权限/音频:host microphone声明** · source-build / 权限/音频

- 成员：ohos.permission.MICROPHONE, AudioRecord.startRecording()
- 实现：执行OH录音call的是host；host申请MICROPHONE并原UID覆盖安装，非只Android APK声明即可；只属于source-build/host路线，绝不套U13/128签认
- 源码 / 产物：unknown; source/build identification missing; report benchmark/2026-10-06-r87-input-gles3-and-services/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：r87 host application；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：host HAP与运行时SHA待引用该路线receipt；reported listens不改成本轮功能测试；源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验；members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-06-r87-input-gles3-and-services/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `59b7a9c9fd0651c84d247023ec62c5e8392b101bbcd17f00f991a4924fc5238f`

### JAVA-117

**时间:默认时区supplier** · source-build / 时间

- 成员：com.android.internal.os.RuntimeInit.commonInit(), java.util.TimeZone.getDefault(), persist.sys.timezone, persist.time.timezone
- 实现：common init安装Android同型supplier，读取persist.sys.timezone后回退OH persist.time.timezone，避免所有appUTC；只属于source-build/host路线，绝不套U13/128签认
- 源码 / 产物：unknown; source/build identification missing; report benchmark/2026-10-07-r88-routing-and-time-zone/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：r88 build96；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：报告只列clocks/calendars整类，不能造具体APK成功对象；源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验；members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-07-r88-routing-and-time-zone/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `33823ac5b24f20203546dad3ca5934a92f52244840943c36ced1ca8eeaac77b8`

### JAVA-118

**系统服务:VPN未同意答案** · source-build / 系统服务

- 成员：ServiceManager.getService("vpn_management"), VpnService.prepare(Context)
- 实现：in-process返回用户尚未同意该app VPN的Android状态；不当VPN隧道已工作；只属于source-build/host路线，绝不套U13/128签认
- 源码 / 产物：unknown; source/build identification missing; report benchmark/2026-10-08-r89-services-and-batches/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：r89 build99；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验；members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-08-r89-services-and-batches/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `b5c2a8438ce481743c34ef265b2413425edaf709cb4217bb166d81f3ac4d5ef3`

### JAVA-119

**加密:legacy KeyPairGeneratorSpec** · source-build / 加密

- 成员：android.security.KeyPairGeneratorSpec, KeyPairGenerator.initialize(AlgorithmParameterSpec), AndroidKeyStore
- 实现：in-process provider转旧spec为支持的参数，保留Android语义；算法/持久化范围未全部证明；只属于source-build/host路线，绝不套U13/128签认
- 源码 / 产物：unknown; source/build identification missing; report benchmark/2026-10-08-r89-services-and-batches/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：r89 build99；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验；members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-08-r89-services-and-batches/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `b5c2a8438ce481743c34ef265b2413425edaf709cb4217bb166d81f3ac4d5ef3`

### JAVA-120

**包管理:platform android包** · source-build / 包管理

- 成员：PackageManager.getPackageInfo("android",int), PackageManager.getApplicationInfo("android",int)
- 实现：PM能回答platform package android，修服务调用NameNotFound；不从此泛称安装任意system包；只属于source-build/host路线，绝不套U13/128签认
- 源码 / 产物：unknown; source/build identification missing; report benchmark/2026-10-08-r89-services-and-batches/README.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：r89 build99；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：源码快照/TU与产物完整SHA尚需该路线receipt定位；本轮只提供原报告路径+SHA；Android API level/APK targetSdk/Android设备对照/OH精确ROM无本项直接证据时unknown，不推广平台兼容范围；源码路线、候选、历史验证与当前部署分开，未做本轮设备核验；members是Android入口/类/接口；README未列实现TU的部分不声明已审源码同源。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-08-r89-services-and-batches/README.md>)：来源具体方法、实现边界及历史/候选证据；SHA256 `b5c2a8438ce481743c34ef265b2413425edaf709cb4217bb166d81f3ac4d5ef3`

### NATIVE-001

**libEGL.so：当时缺口** · NDK静态基线

- 成员：eglCreateNativeClientBufferANDROID, eglGetSystemTimeFrequencyNV, eglGetSystemTimeNV
- 实现：仅对API33 stub核dynsym；本组3名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libEGL.so ELF=unknown；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-002

**libEGL.so：当时导出，功能未知** · NDK静态基线

- 成员：eglBindAPI, eglBindTexImage, eglChooseConfig, eglClientWaitSync, eglClientWaitSyncKHR, eglCopyBuffers, eglCreateContext, eglCreateImage, eglCreateImageKHR, eglCreatePbufferFromClientBuffer, eglCreatePbufferSurface, eglCreatePixmapSurface
- 实现：仅对API33 stub核dynsym；本组70名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=oh；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libEGL.so ELF=96bc14217ceb3536440e97b53e80228106cb57fe95a3e17570bdefbdb76d49a5；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-003

**libGLESv1_CM.so：当时缺口** · NDK静态基线

- 成员：glAlphaFunc, glAlphaFuncx, glAlphaFuncxOES, glBindFramebufferOES, glBindRenderbufferOES, glBlendEquationOES, glBlendEquationSeparateOES, glBlendFuncSeparateOES, glCheckFramebufferStatusOES, glClearColorx, glClearColorxOES, glClearDepthfOES
- 实现：仅对API33 stub核dynsym；本组180名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libGLESv1_CM.so ELF=unknown；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-004

**libGLESv1_CM.so：当时导出，功能未知** · NDK静态基线

- 成员：glActiveTexture, glBindBuffer, glBindTexture, glBindVertexArrayOES, glBlendFunc, glBufferData, glBufferSubData, glClear, glClearColor, glClearDepthf, glClearStencil, glColorMask
- 实现：仅对API33 stub核dynsym；本组98名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=oh；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libGLESv1_CM.so ELF=unknown；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-005

**libGLESv2.so：当时导出，功能未知** · NDK静态基线

- 成员：glActiveTexture, glAttachShader, glBeginPerfMonitorAMD, glBindAttribLocation, glBindBuffer, glBindFramebuffer, glBindRenderbuffer, glBindTexture, glBindVertexArrayOES, glBlendColor, glBlendEquation, glBlendEquationSeparate
- 实现：仅对API33 stub核dynsym；本组204名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=oh；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libGLESv2.so ELF=5b4f734b081a4067ce36552085952268a4c72034107bae41df0222625a6e2319；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-006

**libGLESv3.so：当时导出，功能未知** · NDK静态基线

- 成员：glActiveShaderProgram, glActiveTexture, glAttachShader, glBeginQuery, glBeginTransformFeedback, glBindAttribLocation, glBindBuffer, glBindBufferBase, glBindBufferRange, glBindFramebuffer, glBindImageTexture, glBindProgramPipeline
- 实现：仅对API33 stub核dynsym；本组418名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=oh；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libGLESv3.so ELF=859a05be01f426ef7cffb7fb3cd61a7c7b45aa718210411b6d5af9b0fbed6255；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-007

**libOpenMAXAL.so：当时缺口** · NDK静态基线

- 成员：XA_IID_ANDROIDBUFFERQUEUESOURCE, XA_IID_AUDIODECODERCAPABILITIES, XA_IID_AUDIOENCODER, XA_IID_AUDIOENCODERCAPABILITIES, XA_IID_AUDIOIODEVICECAPABILITIES, XA_IID_CAMERA, XA_IID_CAMERACAPABILITIES, XA_IID_CONFIGEXTENSION, XA_IID_DEVICEVOLUME, XA_IID_DYNAMICINTERFACEMANAGEMENT, XA_IID_DYNAMICSOURCE, XA_IID_ENGINE
- 实现：仅对API33 stub核dynsym；本组44名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libOpenMAXAL.so ELF=unknown；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-008

**libOpenSLES.so：当时缺口** · NDK静态基线

- 成员：SL_IID_ANDROIDACOUSTICECHOCANCELLATION, SL_IID_ANDROIDAUTOMATICGAINCONTROL, SL_IID_ANDROIDBUFFERQUEUESOURCE, SL_IID_ANDROIDCONFIGURATION, SL_IID_ANDROIDEFFECT, SL_IID_ANDROIDEFFECTCAPABILITIES, SL_IID_ANDROIDEFFECTSEND, SL_IID_ANDROIDNOISESUPPRESSION, SL_IID_ANDROIDSIMPLEBUFFERQUEUE, slQueryNumSupportedEngineInterfaces, slQuerySupportedEngineInterfaces
- 实现：仅对API33 stub核dynsym；本组11名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libOpenSLES.so ELF=unknown；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-009

**libOpenSLES.so：当时导出，功能未知** · NDK静态基线

- 成员：SL_IID_3DCOMMIT, SL_IID_3DDOPPLER, SL_IID_3DGROUPING, SL_IID_3DLOCATION, SL_IID_3DMACROSCOPIC, SL_IID_3DSOURCE, SL_IID_AUDIODECODERCAPABILITIES, SL_IID_AUDIOENCODER, SL_IID_AUDIOENCODERCAPABILITIES, SL_IID_AUDIOIODEVICECAPABILITIES, SL_IID_BASSBOOST, SL_IID_BUFFERQUEUE
- 实现：仅对API33 stub核dynsym；本组45名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=oh；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libOpenSLES.so ELF=05d8ac90dbced47c8b47275a5d978bc922d4d8f6f84cd3df1b456633ae6d1100；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-010

**libaaudio.so：当时缺口** · NDK静态基线

- 成员：AAudioStreamBuilder_delete, AAudioStreamBuilder_openStream, AAudioStreamBuilder_setAllowedCapturePolicy, AAudioStreamBuilder_setAttributionTag, AAudioStreamBuilder_setBufferCapacityInFrames, AAudioStreamBuilder_setChannelCount, AAudioStreamBuilder_setChannelMask, AAudioStreamBuilder_setContentType, AAudioStreamBuilder_setDataCallback, AAudioStreamBuilder_setDeviceId, AAudioStreamBuilder_setDirection, AAudioStreamBuilder_setErrorCallback
- 实现：仅对API33 stub核dynsym；本组67名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libaaudio.so ELF=unknown；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-011

**libamidi.so：当时缺口** · NDK静态基线

- 成员：AMidiDevice_fromJava, AMidiDevice_getDefaultProtocol, AMidiDevice_getNumInputPorts, AMidiDevice_getNumOutputPorts, AMidiDevice_getType, AMidiDevice_release, AMidiInputPort_close, AMidiInputPort_open, AMidiInputPort_send, AMidiInputPort_sendFlush, AMidiInputPort_sendWithTimestamp, AMidiOutputPort_close
- 实现：仅对API33 stub核dynsym；本组14名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libamidi.so ELF=unknown；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-012

**libandroid.so：当时缺口** · NDK静态基线

- 成员：AAssetDir_close, AAssetDir_getNextFileName, AAssetDir_rewind, AAssetManager_fromJava, AAssetManager_open, AAssetManager_openDir, AAsset_close, AAsset_getBuffer, AAsset_getLength, AAsset_getLength64, AAsset_getRemainingLength, AAsset_getRemainingLength64
- 实现：仅对API33 stub核dynsym；本组277名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有37名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libandroid.so ELF=unknown；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-013

**libandroid.so：当时导出，功能未知** · NDK静态基线

- 成员：AChoreographerFrameCallbackData_getFrameTimeNanos, AChoreographerFrameCallbackData_getFrameTimelineDeadlineNanos, AChoreographerFrameCallbackData_getFrameTimelineExpectedPresentationTimeNanos, AChoreographerFrameCallbackData_getFrameTimelineVsyncId, AChoreographerFrameCallbackData_getFrameTimelinesLength, AChoreographerFrameCallbackData_getPreferredFrameTimelineIndex, AChoreographer_getInstance, AChoreographer_postFrameCallback, AChoreographer_postFrameCallback64, AChoreographer_postVsyncCallback, AChoreographer_registerRefreshRateCallback, AChoreographer_unregisterRefreshRateCallback
- 实现：仅对API33 stub核dynsym；本组46名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=westlake；source-build另profile有4名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libandroid.so ELF=unknown；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-014

**libbinder_ndk.so：当时缺口** · NDK静态基线

- 成员：AIBinder_Class_define, AIBinder_Class_disableInterfaceTokenHeader, AIBinder_Class_getDescriptor, AIBinder_Class_setOnDump, AIBinder_DeathRecipient_delete, AIBinder_DeathRecipient_new, AIBinder_DeathRecipient_setOnUnlinked, AIBinder_Weak_clone, AIBinder_Weak_delete, AIBinder_Weak_lt, AIBinder_Weak_new, AIBinder_Weak_promote
- 实现：仅对API33 stub核dynsym；本组107名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有104名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libbinder_ndk.so ELF=unknown；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-015

**libc.so：当时缺口** · NDK静态基线

- 成员：__FD_CLR_chk, __FD_ISSET_chk, __FD_SET_chk, __assert, __b64_ntop, __b64_pton, __cmsg_nxthdr, __dn_comp, __dn_count_labels, __dn_skipname, __fp_nquery, __fp_query
- 实现：仅对API33 stub核dynsym；本组214名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有6名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libc.so ELF=unknown；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-016

**libc.so：当时导出，功能未知** · NDK静态基线

- 成员：_Exit, __ctype_get_mb_cur_max, __cxa_atexit, __cxa_finalize, __cxa_thread_atexit_impl, __fbufsize, __fgets_chk, __flbf, __fpclassify, __fpclassifyf, __fpclassifyl, __fpending
- 实现：仅对API33 stub核dynsym；本组1170名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=oh；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libc.so ELF=fd3c4701acf719738fbd14cf1d419e4dd222c06a6df41f53d973354d648af7e2；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-017

**libc.so：当时导出，功能未知** · NDK静态基线

- 成员：__assert2, __errno, __open_2, __strncpy_chk2, __system_property_get, __system_property_set, android_set_abort_message, strtoll_l, strtoull_l
- 实现：仅对API33 stub核dynsym；本组9名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=westlake；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libc.so ELF=unknown；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-018

**libcamera2ndk.so：当时缺口** · NDK静态基线

- 成员：ACameraCaptureSession_abortCaptures, ACameraCaptureSession_capture, ACameraCaptureSession_captureV2, ACameraCaptureSession_close, ACameraCaptureSession_getDevice, ACameraCaptureSession_logicalCamera_capture, ACameraCaptureSession_logicalCamera_captureV2, ACameraCaptureSession_logicalCamera_setRepeatingRequest, ACameraCaptureSession_logicalCamera_setRepeatingRequestV2, ACameraCaptureSession_setRepeatingRequest, ACameraCaptureSession_setRepeatingRequestV2, ACameraCaptureSession_stopRepeating
- 实现：仅对API33 stub核dynsym；本组69名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libcamera2ndk.so ELF=unknown；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-019

**libdl.so：当时缺口** · NDK静态基线

- 成员：__cfi_shadow_size, android_dlopen_ext, android_get_application_target_sdk_version
- 实现：仅对API33 stub核dynsym；本组3名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libdl.so ELF=unknown；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-020

**libdl.so：当时导出，功能未知** · NDK静态基线

- 成员：__cfi_slowpath, __cfi_slowpath_diag, dl_iterate_phdr, dladdr, dlclose, dlerror, dlopen, dlsym, dlvsym
- 实现：仅对API33 stub核dynsym；本组9名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=oh；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libdl.so ELF=unknown；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-021

**libicu.so：当时缺口** · NDK静态基线

- 成员：u_charAge, u_charDigitValue, u_charDirection, u_charFromName, u_charMirror, u_charName, u_charType, u_countChar32, u_digit, u_enumCharNames, u_enumCharTypes, u_errorName
- 实现：仅对API33 stub核dynsym；本组306名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libicu.so ELF=unknown；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-022

**libjnigraphics.so：当时缺口** · NDK静态基线

- 成员：AImageDecoderFrameInfo_create, AImageDecoderFrameInfo_delete, AImageDecoderFrameInfo_getBlendOp, AImageDecoderFrameInfo_getDisposeOp, AImageDecoderFrameInfo_getDuration, AImageDecoderFrameInfo_getFrameRect, AImageDecoderFrameInfo_hasAlphaWithinBounds, AImageDecoderHeaderInfo_getAlphaFlags, AImageDecoderHeaderInfo_getAndroidBitmapFormat, AImageDecoderHeaderInfo_getDataSpace, AImageDecoderHeaderInfo_getHeight, AImageDecoderHeaderInfo_getMimeType
- 实现：仅对API33 stub核dynsym；本组36名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有36名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libjnigraphics.so ELF=unknown；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-023

**libjnigraphics.so：当时导出，功能未知** · NDK静态基线

- 成员：AndroidBitmap_getInfo, AndroidBitmap_lockPixels, AndroidBitmap_unlockPixels
- 实现：仅对API33 stub核dynsym；本组3名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=westlake；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libjnigraphics.so ELF=unknown；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-024

**liblog.so：当时导出，功能未知** · NDK静态基线

- 成员：__android_log_assert, __android_log_buf_print, __android_log_buf_write, __android_log_call_aborter, __android_log_default_aborter, __android_log_get_minimum_priority, __android_log_is_loggable, __android_log_is_loggable_len, __android_log_logd_logger, __android_log_print, __android_log_set_aborter, __android_log_set_default_tag
- 实现：仅对API33 stub核dynsym；本组18名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=westlake；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；liblog.so ELF=e8c113e62d2f9b53fac9ad99d61ff1d2f9a027f7d129f5ab8c47dbc64fa69214；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-025

**libm.so：当时缺口** · NDK静态基线

- 成员：__fe_dfl_env, fedisableexcept, feenableexcept, fegetexcept, gamma, gamma_r, gammaf, gammaf_r, significandl
- 实现：仅对API33 stub核dynsym；本组9名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libm.so ELF=unknown；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-026

**libm.so：当时导出，功能未知** · NDK静态基线

- 成员：__signbit, __signbitf, __signbitl, acos, acosf, acosh, acoshf, acoshl, acosl, asin, asinf, asinh
- 实现：仅对API33 stub核dynsym；本组277名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=oh；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libm.so ELF=unknown；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-027

**libmediandk.so：当时缺口** · NDK静态基线

- 成员：AImageReader_acquireLatestImageAsync, AImageReader_acquireNextImageAsync, AImageReader_getFormat, AImageReader_getHeight, AImageReader_getMaxImages, AImageReader_getWidth, AImageReader_setBufferRemovedListener, AImageReader_setImageListener, AImage_deleteAsync, AImage_getCropRect, AImage_getNumberOfPlanes, AImage_getPlanePixelStride
- 实现：仅对API33 stub核dynsym；本组287名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libmediandk.so ELF=unknown；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-028

**libmediandk.so：当时导出，功能未知** · NDK静态基线

- 成员：AImageReader_acquireLatestImage, AImageReader_acquireNextImage, AImageReader_delete, AImageReader_getWindow, AImageReader_new, AImageReader_newWithUsage, AImage_delete, AImage_getFormat, AImage_getHardwareBuffer, AImage_getHeight, AImage_getPlaneData, AImage_getPlaneRowStride
- 实现：仅对API33 stub核dynsym；本组13名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=westlake；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libmediandk.so ELF=unknown；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-029

**libnativehelper.so：当时导出，功能未知** · NDK静态基线

- 成员：AFileDescriptor_create, AFileDescriptor_getFd, AFileDescriptor_setFd, JNI_CreateJavaVM, JNI_GetCreatedJavaVMs, JNI_GetDefaultJavaVMInitArgs
- 实现：仅对API33 stub核dynsym；本组6名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=westlake；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libnativehelper.so ELF=7803616f7d962bad4c51a12198ecb0ce6e252877bb1f4ce6c15ed63b1db5334f；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-030

**libnativewindow.so：当时缺口** · NDK静态基线

- 成员：AHardwareBuffer_getId, AHardwareBuffer_isSupported, AHardwareBuffer_lockAndGetInfo, AHardwareBuffer_lockPlanes, ANativeWindow_setFrameRateWithChangeStrategy
- 实现：仅对API33 stub核dynsym；本组5名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libnativewindow.so ELF=unknown；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-031

**libnativewindow.so：当时导出，功能未知** · NDK静态基线

- 成员：AHardwareBuffer_acquire, AHardwareBuffer_allocate, AHardwareBuffer_describe, AHardwareBuffer_lock, AHardwareBuffer_recvHandleFromUnixSocket, AHardwareBuffer_release, AHardwareBuffer_sendHandleToUnixSocket, AHardwareBuffer_unlock, ANativeWindow_acquire, ANativeWindow_getBuffersDataSpace, ANativeWindow_getFormat, ANativeWindow_getHeight
- 实现：仅对API33 stub核dynsym；本组21名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=westlake；source-build另profile有4名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libnativewindow.so ELF=unknown；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-032

**libneuralnetworks.so：当时缺口** · NDK静态基线

- 成员：ANeuralNetworksBurst_create, ANeuralNetworksBurst_free, ANeuralNetworksCompilation_create, ANeuralNetworksCompilation_createForDevices, ANeuralNetworksCompilation_finish, ANeuralNetworksCompilation_free, ANeuralNetworksCompilation_getPreferredMemoryAlignmentForInput, ANeuralNetworksCompilation_getPreferredMemoryAlignmentForOutput, ANeuralNetworksCompilation_getPreferredMemoryPaddingForInput, ANeuralNetworksCompilation_getPreferredMemoryPaddingForOutput, ANeuralNetworksCompilation_setCaching, ANeuralNetworksCompilation_setPreference
- 实现：仅对API33 stub核dynsym；本组69名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libneuralnetworks.so ELF=unknown；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-033

**libstdc++.so：当时缺口** · NDK静态基线

- 成员：_ZSt7nothrow, _ZdaPv, _ZdaPvRKSt9nothrow_t, _ZdlPv, _ZdlPvRKSt9nothrow_t, _Znam, _ZnamRKSt9nothrow_t, _Znwm, _ZnwmRKSt9nothrow_t, __cxa_guard_acquire, __cxa_guard_release, __cxa_pure_virtual
- 实现：仅对API33 stub核dynsym；本组12名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有12名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libstdc++.so ELF=unknown；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-034

**libstdc++.so：当时导出，功能未知** · NDK静态基线

- 成员：__cxa_guard_abort
- 实现：仅对API33 stub核dynsym；本组1名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=westlake；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libstdc++.so ELF=unknown；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-035

**libsync.so：当时缺口** · NDK静态基线

- 成员：sync_file_info, sync_file_info_free, sync_merge
- 实现：仅对API33 stub核dynsym；本组3名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有3名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libsync.so ELF=unknown；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-036

**libvulkan.so：当时缺口** · NDK静态基线

- 成员：vkCreateAndroidSurfaceKHR, vkGetAndroidHardwareBufferPropertiesANDROID, vkGetMemoryAndroidHardwareBufferANDROID
- 实现：仅对API33 stub核dynsym；本组3名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=missing；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libvulkan.so ELF=unknown；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-037

**libvulkan.so：当时导出，功能未知** · NDK静态基线

- 成员：vkAcquireNextImage2KHR, vkAcquireNextImageKHR, vkAllocateCommandBuffers, vkAllocateDescriptorSets, vkAllocateMemory, vkBeginCommandBuffer, vkBindBufferMemory, vkBindBufferMemory2, vkBindImageMemory, vkBindImageMemory2, vkCmdBeginQuery, vkCmdBeginRenderPass
- 实现：仅对API33 stub核dynsym；本组229名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=oh；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libvulkan.so ELF=711d9723c47d816b7a72d96cd1d0a05533b76e891347fb830e5c8b6889a2f3dc；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-038

**libz.so：当时导出，功能未知** · NDK静态基线

- 成员：_dist_code, _length_code, _tr_align, _tr_flush_bits, _tr_flush_block, _tr_init, _tr_stored_block, _tr_tally, adler32, adler32_combine, adler32_combine64, adler32_z
- 实现：仅对API33 stub核dynsym；本组93名，成员给精确代表12名以内；全表在source，由外环附录列。legacy=oh；source-build另profile有0名改变供应，不合并为今日成功。
- 源码 / 产物：benchmark/2026-09-21-ndk-coverage/ndk-coverage.json providers记录；libz.so ELF=3c025525f68bc3afcd74fe3c14c2f7c55112e2b801a4d1046a335dd2f4c73240；该profile实现源码unknown
- Android 源码：NDK r25符号stub，不是方法体；API level：33（符号对照版本，非支持范围）；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-09-21 legacy / source-build两种profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；符号存在不证明转译、方法实现、注册winner、namespace可见或APK成功；后期修复分行记录，不能覆盖此历史profile。

- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/ndk-coverage.json>)：legacy NDK符号全集，仅导出供应；SHA256 `8273c3e58b5de5fc05f533b6602c6228a274b435929c98c4287068bbb84522a3`
- [ndk-coverage.json](<../../../../westlake-harness/benchmark/2026-09-21-ndk-coverage/source-build/ndk-coverage.json>)：不同source-build供应profile，不是U13或当前板态；SHA256 `bf301ff98c36d3c4c697a89879cde2c95a08abda14627e9a59532800685d1d99`

### NATIVE-039

**android.app.Activity：nullptr** · JNI历史有意桩

- 成员：android.app.Activity.getDlWarning()Ljava/lang/String;
- 实现：兼容降级/占位组=nullptr；原声明示例：android.app.Activity.getDlWarning ()Ljava/lang/String; | :30 | nullptr | "OH musl has no android_dlwarning; null = no warnings"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_app_Activity.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-040

**android.database.CursorWindow：unsupported** · JNI历史有意桩

- 成员：android.database.CursorWindow.nativeCreateFromParcel(Landroid/os/Parcel;)J, android.database.CursorWindow.nativeWriteToParcel(JLandroid/os/Parcel;)V
- 实现：兼容降级/占位组=unsupported；原声明示例：android.database.CursorWindow.nativeCreateFromParcel (Landroid/os/Parcel;)J | :118 | 0 (throws UnsupportedOperationException) | "Binder marshalling stubbed; path unused; throw if reached"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_database_CursorWindow.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-041

**android.graphics.BLASTBufferQueue：0** · JNI历史有意桩

- 成员：android.graphics.BLASTBufferQueue.nativeGetLastAcquiredFrameNum(J)J
- 实现：兼容降级/占位组=0；原声明示例：android.graphics.BLASTBufferQueue.nativeGetLastAcquiredFrameNum (J)J | BBQ_nativeGetLastAcquiredFrameNum | :653 | 0 | -。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_graphics_compat_shim.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-042

**android.graphics.BLASTBufferQueue：JNI_FALSE** · JNI历史有意桩

- 成员：android.graphics.BLASTBufferQueue.nativeSyncNextTransaction(JLjava/util/function/Consumer;Z)Z
- 实现：兼容降级/占位组=JNI_FALSE；原声明示例：android.graphics.BLASTBufferQueue.nativeSyncNextTransaction (JLjava/util/function/Consumer;Z)Z | BBQ_nativeSyncNextTransaction | :647 | JNI_FALSE | "OH queue has no SF transaction-acquisition callback; report none armed"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_graphics_compat_shim.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-043

**android.graphics.BLASTBufferQueue：void** · JNI历史有意桩

- 成员：android.graphics.BLASTBufferQueue.nativeApplyPendingTransactions(JJ)V, android.graphics.BLASTBufferQueue.nativeClearSyncTransaction(J)V, android.graphics.BLASTBufferQueue.nativeMergeWithNextTransaction(JJJ)V, android.graphics.BLASTBufferQueue.nativeSetTransactionHangCallback(JLandroid/graphics/BLASTBufferQueue$TransactionHangCallback;)V, android.graphics.BLASTBufferQueue.nativeStopContinuousSyncTransaction(J)V
- 实现：兼容降级/占位组=void；原声明示例：android.graphics.BLASTBufferQueue.nativeStopContinuousSyncTransaction (J)V | BBQ_nativeStopContinuousSyncTransaction | :650 | void | -。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_graphics_compat_shim.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-044

**android.graphics.BLASTBufferQueue：固定/占位/有损返回** · JNI历史有意桩

- 成员：android.graphics.BLASTBufferQueue.nativeGatherPendingTransactions(JJ)Landroid/view/SurfaceControl$Transaction;
- 实现：兼容降级/占位组=固定/占位/有损返回；原声明示例：android.graphics.BLASTBufferQueue.nativeGatherPendingTransactions (JJ)Landroid/view/SurfaceControl$Transaction; | BBQ_nativeGatherPendingTransactions | :655 | new empty Transaction | "return a live Transaction wrapper; no pending SF tx in OH"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_graphics_compat_shim.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-045

**android.graphics.HardwareRenderer：0** · JNI历史有意桩

- 成员：android.graphics.HardwareRenderer.nGetRenderThreadTid(J)I, android.graphics.HardwareRenderer.nSyncAndDrawFrame(J[JI)I
- 实现：兼容降级/占位组=0；原声明示例：android.graphics.HardwareRenderer.nGetRenderThreadTid (J)I | HRN_zero_j | :876 | 0 | "proxy-handle natives no-op"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_graphics_compat_shim.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。；NEUTER仅OHUB_VARIANT/OHUB_UNITY_LIBDIR门控，不能泛化到整个runtime的HWUI实现。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-046

**android.graphics.HardwareRenderer：JNI_FALSE** · JNI历史有意桩

- 成员：android.graphics.HardwareRenderer.nLoadSystemProperties(J)Z, android.graphics.HardwareRenderer.nPause(J)Z
- 实现：兼容降级/占位组=JNI_FALSE；原声明示例：android.graphics.HardwareRenderer.nLoadSystemProperties (J)Z | HRN_false_j | :873 | JNI_FALSE | "proxy-handle natives no-op"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_graphics_compat_shim.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。；NEUTER仅OHUB_VARIANT/OHUB_UNITY_LIBDIR门控，不能泛化到整个runtime的HWUI实现。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-047

**android.graphics.HardwareRenderer：JNI_TRUE** · JNI历史有意桩

- 成员：android.graphics.HardwareRenderer.nIsDrawingEnabled()Z
- 实现：兼容降级/占位组=JNI_TRUE；原声明示例：android.graphics.HardwareRenderer.nIsDrawingEnabled ()Z | HRN_true0 | :875 | JNI_TRUE | "proxy-handle no-op"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_graphics_compat_shim.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。；NEUTER仅OHUB_VARIANT/OHUB_UNITY_LIBDIR门控，不能泛化到整个runtime的HWUI实现。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-048

**android.graphics.HardwareRenderer：void** · JNI历史有意桩

- 成员：android.graphics.HardwareRenderer.nAddObserver, android.graphics.HardwareRenderer.nAddRenderNode, android.graphics.HardwareRenderer.nAllocateBuffers, android.graphics.HardwareRenderer.nBuildLayer, android.graphics.HardwareRenderer.nCancelLayerUpdate, android.graphics.HardwareRenderer.nDeleteProxy(J)V, android.graphics.HardwareRenderer.nDestroy, android.graphics.HardwareRenderer.nDestroyHardwareResources, android.graphics.HardwareRenderer.nDetachSurfaceTexture, android.graphics.HardwareRenderer.nDrawRenderNode, android.graphics.HardwareRenderer.nFence, android.graphics.HardwareRenderer.nForceDrawNextFrame, android.graphics.HardwareRenderer.nNotifyFramePending, android.graphics.HardwareRenderer.nOverrideProperty(Ljava/lang/String;Ljava/lang/String;)V, android.graphics.HardwareRenderer.nPushLayerUpdate, android.graphics.HardwareRenderer.nRegisterAnimatingRenderNode, android.graphics.HardwareRenderer.nRegisterVectorDrawableAnimator, android.graphics.HardwareRenderer.nRemoveObserver, android.graphics.HardwareRenderer.nRemoveRenderNode, android.graphics.HardwareRenderer.nSetContentDrawBounds, android.graphics.HardwareRenderer.nSetForceDark, android.graphics.HardwareRenderer.nSetLightAlpha, android.graphics.HardwareRenderer.nSetLightGeometry, android.graphics.HardwareRenderer.nSetName, android.graphics.HardwareRenderer.nSetOpaque, android.graphics.HardwareRenderer.nSetSdrWhitePoint, android.graphics.HardwareRenderer.nSetStopped, android.graphics.HardwareRenderer.nSetSurface, android.graphics.HardwareRenderer.nSetSurfaceControl, android.graphics.HardwareRenderer.nSetTargetSdrHdrRatio, android.graphics.HardwareRenderer.nStopDrawing, android.graphics.HardwareRenderer.preload()V
- 实现：兼容降级/占位组=void；原声明示例：android.graphics.HardwareRenderer.nDeleteProxy (J)V | HRN_v1 | :868 | void | "RenderThread birth"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_graphics_compat_shim.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。；NEUTER仅OHUB_VARIANT/OHUB_UNITY_LIBDIR门控，不能泛化到整个runtime的HWUI实现。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-049

**android.graphics.HardwareRenderer：固定/占位/有损返回** · JNI历史有意桩

- 成员：android.graphics.HardwareRenderer.nCreateProxy(ZJ)J, android.graphics.HardwareRenderer.nCreateRootRenderNode()J, android.graphics.HardwareRenderer.nCreateTextureLayer(J)J, android.graphics.HardwareRenderer.nSetColorMode(JI)F
- 实现：兼容降级/占位组=固定/占位/有损返回；原声明示例：android.graphics.HardwareRenderer.nCreateRootRenderNode ()J | HRN_make | :870 | 1L | "RenderThread birth load-bearing entries: no proxy => no RenderThread"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_graphics_compat_shim.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。；NEUTER仅OHUB_VARIANT/OHUB_UNITY_LIBDIR门控，不能泛化到整个runtime的HWUI实现。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-050

**android.graphics.ImageDecoder：nullptr** · JNI历史有意桩

- 成员：android.graphics.ImageDecoder.nGetColorSpace(J)Landroid/graphics/ColorSpace;, android.graphics.ImageDecoder.nGetSampledSize(JI)Landroid/util/Size;
- 实现：兼容降级/占位组=nullptr；原声明示例：android.graphics.ImageDecoder.nGetColorSpace (J)Landroid/graphics/ColorSpace; | ID_nGetColorSpace | :79 | nullptr | "libhwui caches gColorSpace jfieldID; when it fails (framework.jar layout) fid stays null -> CheckJNI abort. Override: return null; sRGB assumed when null" [ASSUMPTION REFUTED by fd-musicplayer -- but mus。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_graphics_compat_shim.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-051

**android.graphics.ImageDecoder：void** · JNI历史有意桩

- 成员：android.graphics.ImageDecoder.nClose(J)V
- 实现：兼容降级/占位组=void；原声明示例：android.graphics.ImageDecoder.nClose (J)V | ID_nClose | :109 | void | "stub remaining ImageDecoder natives; HelloWorld doesn't decode images"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_graphics_compat_shim.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-052

**android.graphics.ImageDecoder：固定/占位/有损返回** · JNI历史有意桩

- 成员：android.graphics.ImageDecoder.nGetMimeType(J)Ljava/lang/String;, android.graphics.ImageDecoder.nGetPadding(JLandroid/graphics/Rect;)V
- 实现：兼容降级/占位组=固定/占位/有损返回；原声明示例：android.graphics.ImageDecoder.nGetPadding (JLandroid/graphics/Rect;)V | ID_nGetPadding | :87 | void (outRect unchanged) | "same fid/jclass cache problem; libhwui IsInstanceOf on null gNinePatchInsetsClass -> abort. leave outRect (0,0,0,0)"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_graphics_compat_shim.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-053

**android.graphics.Typeface：0** · JNI历史有意桩

- 成员：android.graphics.Typeface.nativeGetStyle(J)I, android.graphics.Typeface.nativeWriteTypefaces(Ljava/nio/ByteBuffer;I[J)I
- 实现：兼容降级/占位组=0；原声明示例：android.graphics.Typeface.nativeGetStyle (J)I | :73 | 0 | same。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_graphics_Typeface.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-054

**android.graphics.Typeface：nullptr** · JNI历史有意桩

- 成员：android.graphics.Typeface.nativeGetSupportedAxes(J)[I, android.graphics.Typeface.nativeReadTypefaces(Ljava/nio/ByteBuffer;I)[J
- 实现：兼容降级/占位组=nullptr；原声明示例：android.graphics.Typeface.nativeGetSupportedAxes (J)[I | :71 | nullptr | "safe defaults, non-functional but non-crashing at ctor time"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_graphics_Typeface.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-055

**android.graphics.Typeface：void** · JNI历史有意桩

- 成员：android.graphics.Typeface.nativeAddFontCollections(J)V, android.graphics.Typeface.nativeForceSetStaticFinalField(Ljava/lang/String;Landroid/graphics/Typeface;)V, android.graphics.Typeface.nativeRegisterGenericFamily(Ljava/lang/String;J)V, android.graphics.Typeface.nativeRegisterLocaleList(Ljava/lang/String;)V, android.graphics.Typeface.nativeSetDefault(J)V, android.graphics.Typeface.nativeWarmUpCache(Ljava/lang/String;)V
- 实现：兼容降级/占位组=void；原声明示例：android.graphics.Typeface.nativeSetDefault (J)V | :72 | void | same。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_graphics_Typeface.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-056

**android.graphics.Typeface：固定/占位/有损返回** · JNI历史有意桩

- 成员：android.graphics.Typeface.nativeCreateFromArray([JJII)J, android.graphics.Typeface.nativeCreateFromTypeface(JI)J, android.graphics.Typeface.nativeCreateFromTypefaceWithExactStyle(JIZ)J, android.graphics.Typeface.nativeCreateFromTypefaceWithVariation(JLjava/util/List;)J, android.graphics.Typeface.nativeCreateWeightAlias(JI)J, android.graphics.Typeface.nativeGetWeight(J)I
- 实现：兼容降级/占位组=固定/占位/有损返回；原声明示例：android.graphics.Typeface.nativeCreateFromTypeface (JI)J | :66 | 1L (kFakeTypefaceHandle) | "Return non-zero fake handle so Typeface ctor accepts (rejects 0 with RuntimeException); same handle reused -> non-functional rendering"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_graphics_Typeface.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-057

**android.hardware.SystemSensorManager：0** · JNI历史有意桩

- 成员：android.hardware.SystemSensorManager.nativeConfigDirectChannel(JIII)I, android.hardware.SystemSensorManager.nativeCreateDirectChannel, android.hardware.SystemSensorManager.nativeSetOperationParameter
- 实现：兼容降级/占位组=0；原声明示例：android.hardware.SystemSensorManager.nativeCreateDirectChannel (...)I | :93 | 0 | "no channel / unsupported"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_hardware_SensorManager.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-058

**android.hardware.SystemSensorManager：JNI_FALSE** · JNI历史有意桩

- 成员：android.hardware.SystemSensorManager.nativeGetSensorAtIndex(JLandroid/hardware/Sensor;I)Z, android.hardware.SystemSensorManager.nativeIsDataInjectionEnabled(J)Z
- 实现：兼容降级/占位组=JNI_FALSE；原声明示例：android.hardware.SystemSensorManager.nativeGetSensorAtIndex (JLandroid/hardware/Sensor;I)Z | :74 | JNI_FALSE | "false ends enumeration loop -> empty sensor list"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_hardware_SensorManager.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-059

**android.hardware.SystemSensorManager：void** · JNI历史有意桩

- 成员：android.hardware.SystemSensorManager.nativeClassInit()V, android.hardware.SystemSensorManager.nativeDestroyDirectChannel(JI)V, android.hardware.SystemSensorManager.nativeGetDynamicSensors(JLjava/util/List;)V, android.hardware.SystemSensorManager.nativeGetRuntimeSensors(JILjava/util/List;)V
- 实现：兼容降级/占位组=void；原声明示例：android.hardware.SystemSensorManager.nativeClassInit ()V | :64 | void | "no Sensor field-ID caching; never populate a Sensor"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_hardware_SensorManager.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-060

**android.hardware.SystemSensorManager：固定/占位/有损返回** · JNI历史有意桩

- 成员：android.hardware.SystemSensorManager.nativeCreate(Ljava/lang/String;)J
- 实现：兼容降级/占位组=固定/占位/有损返回；原声明示例：android.hardware.SystemSensorManager.nativeCreate (Ljava/lang/String;)J | :69 | 1 (sentinel) | "non-zero sentinel; never dereferenced"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_hardware_SensorManager.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-061

**android.hardware.SystemSensorManager$BaseEventQueue：0** · JNI历史有意桩

- 成员：android.hardware.SystemSensorManager$BaseEventQueue.nativeDisableSensor(JI)I, android.hardware.SystemSensorManager$BaseEventQueue.nativeEnableSensor(JIII)I, android.hardware.SystemSensorManager$BaseEventQueue.nativeFlushSensor(J)I, android.hardware.SystemSensorManager$BaseEventQueue.nativeInjectSensorData
- 实现：兼容降级/占位组=0；原声明示例：android.hardware.SystemSensorManager$BaseEventQueue.nativeEnableSensor (JIII)I | :124 | 0 | "never reached with zero sensors"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_hardware_SensorManager.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-062

**android.hardware.SystemSensorManager$BaseEventQueue：void** · JNI历史有意桩

- 成员：android.hardware.SystemSensorManager$BaseEventQueue.nativeDestroySensorEventQueue(J)V
- 实现：兼容降级/占位组=void；原声明示例：android.hardware.SystemSensorManager$BaseEventQueue.nativeDestroySensorEventQueue (J)V | :133 | void | -。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_hardware_SensorManager.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-063

**android.hardware.SystemSensorManager$BaseEventQueue：固定/占位/有损返回** · JNI历史有意桩

- 成员：android.hardware.SystemSensorManager$BaseEventQueue.nativeInitBaseEventQueue
- 实现：兼容降级/占位组=固定/占位/有损返回；原声明示例：android.hardware.SystemSensorManager$BaseEventQueue.nativeInitBaseEventQueue (...)J | :117 | 1 (sentinel) | -。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_hardware_SensorManager.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-064

**android.media.AudioSystem：0** · JNI历史有意桩

- 成员：android.media.AudioSystem.newAudioSessionId()I
- 实现：兼容降级/占位组=0；原声明示例：android.media.AudioSystem.newAudioSessionId ()I | :34 | 0 | "0 = AUDIO_UNIQUE_ID_ALLOCATE; no AudioFlinger"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_media_AudioSystemCapabilities.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-065

**android.media.AudioSystem：固定/占位/有损返回** · JNI历史有意桩

- 成员：android.media.AudioSystem.native_getMaxChannelCount()I, android.media.AudioSystem.native_getMaxSampleRate()I, android.media.AudioSystem.native_getMinSampleRate()I
- 实现：兼容降级/占位组=固定/占位/有损返回；原声明示例：android.media.AudioSystem.native_getMaxChannelCount ()I | :10 | 2 | "D600 route stereo; smallest truthful value for FMOD CHANNEL_OUT_STEREO"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_media_AudioSystemCapabilities.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-066

**android.media.AudioTrack：void** · JNI历史有意桩

- 成员：android.media.AudioTrack.native_disableDeviceCallback()V, android.media.AudioTrack.native_enableDeviceCallback()V, android.media.AudioTrack.native_setPlayerIId(I)V
- 实现：兼容降级/占位组=void；原声明示例：android.media.AudioTrack.native_setPlayerIId (I)V | :202 | void | -。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_media_AudioTrack.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-067

**android.media.AudioTrack：固定/占位/有损返回** · JNI历史有意桩

- 成员：android.media.AudioTrack.native_get_output_sample_rate(I)I
- 实现：兼容降级/占位组=固定/占位/有损返回；原声明示例：android.media.AudioTrack.native_get_output_sample_rate (I)I | :112 | 48000 | -。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_media_AudioTrack.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-068

**android.media.MediaPlayer：无codec/空值/假状态** · JNI历史有意桩

- 成员：android.media.MediaPlayer._getAudioStreamType, android.media.MediaPlayer._notifyAt, android.media.MediaPlayer._prepareDrm, android.media.MediaPlayer._releaseDrm, android.media.MediaPlayer._seekTo, android.media.MediaPlayer._setAudioStreamType, android.media.MediaPlayer._setAuxEffectSendLevel, android.media.MediaPlayer._setDataSource, android.media.MediaPlayer._setVolume, android.media.MediaPlayer.attachAuxEffect, android.media.MediaPlayer.getAudioSessionId, android.media.MediaPlayer.getCurrentPosition, android.media.MediaPlayer.getDuration, android.media.MediaPlayer.getPlaybackParams, android.media.MediaPlayer.getSyncParams, android.media.MediaPlayer.getVideoHeight, android.media.MediaPlayer.getVideoWidth, android.media.MediaPlayer.isLooping, android.media.MediaPlayer.nativeSetDataSource, android.media.MediaPlayer.native_applyVolumeShaper, android.media.MediaPlayer.native_enableDeviceCallback, android.media.MediaPlayer.native_finalize, android.media.MediaPlayer.native_getMetadata, android.media.MediaPlayer.native_getMetrics, android.media.MediaPlayer.native_getRoutedDeviceId, android.media.MediaPlayer.native_getVolumeShaperState, android.media.MediaPlayer.native_invoke, android.media.MediaPlayer.native_pullBatteryData, android.media.MediaPlayer.native_setAudioSessionId, android.media.MediaPlayer.native_setMetadataFilter, android.media.MediaPlayer.native_setOutputDevice, android.media.MediaPlayer.native_setRetransmitEndpoint, android.media.MediaPlayer.setLooping, android.media.MediaPlayer.setNextMediaPlayer, android.media.MediaPlayer.setParameter, android.media.MediaPlayer.setPlaybackParams, android.media.MediaPlayer.setSyncParams
- 实现：兼容降级/占位组=无codec/空值/假状态；原声明示例：#  getVideoWidth:312=0 getVideoHeight:313=0 getCurrentPosition:314=0 getDuration:315=0 getAudioSessionId:316=0 isLooping:317=FALSE。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_media_MediaPlayer.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-069

**android.media.audiopolicy.AudioProductStrategy：固定/占位/有损返回** · JNI历史有意桩

- 成员：android.media.audiopolicy.AudioProductStrategy.native_list_audio_product_strategies(Ljava/util/ArrayList;)I
- 实现：兼容降级/占位组=固定/占位/有损返回；原声明示例：android.media.audiopolicy.AudioProductStrategy.native_list_audio_product_strategies (Ljava/util/ArrayList;)I | :24 | 0 (empty) | "no audio-policy service; empty -> AudioAttributes DEFAULT fallback"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_media_AudioSystemCapabilities.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-070

**android.opengl.EGL14：unsupported** · JNI历史有意桩

- 成员：android.opengl.EGL14.eglCopyBuffers, android.opengl.EGL14.eglCreatePixmapSurface
- 实现：兼容降级/占位组=unsupported；原声明示例：android.opengl.EGL14.eglCreatePixmapSurface (...)Landroid/opengl/EGLSurface; | :738 | throws UnsupportedOperationException, nullptr | -。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_opengl_EGL14_adapter.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-071

**android.os.Binder：0** · JNI历史有意桩

- 成员：android.os.Binder.clearCallingIdentity()J, android.os.Binder.clearCallingWorkSource()J, android.os.Binder.getThreadStrictModePolicy()I, android.os.Binder.setCallingWorkSourceUid(I)J
- 实现：兼容降级/占位组=0；原声明示例：android.os.Binder.clearCallingIdentity ()J | :86 | 0。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_os_Binder.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-072

**android.os.Binder：JNI_FALSE** · JNI历史有意桩

- 成员：android.os.Binder.hasExplicitIdentity()Z, android.os.Binder.isDirectlyHandlingTransaction()Z
- 实现：兼容降级/占位组=JNI_FALSE；原声明示例：android.os.Binder.isDirectlyHandlingTransaction ()Z | :84 | JNI_FALSE。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_os_Binder.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-073

**android.os.Binder：void** · JNI历史有意桩

- 成员：android.os.Binder.blockUntilThreadAvailable()V, android.os.Binder.flushPendingCommands()V, android.os.Binder.forceDowngradeToSystemStability()V, android.os.Binder.markVintfStability()V, android.os.Binder.restoreCallingIdentity(J)V, android.os.Binder.restoreCallingWorkSource(J)V, android.os.Binder.setThreadStrictModePolicy(I)V
- 实现：兼容降级/占位组=void；原声明示例：android.os.Binder.restoreCallingIdentity (J)V | :87 | void。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_os_Binder.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-074

**android.os.Binder：固定/占位/有损返回** · JNI历史有意桩

- 成员：android.os.Binder.getCallingWorkSourceUid()I
- 实现：兼容降级/占位组=固定/占位/有损返回；原声明示例：android.os.Binder.getCallingWorkSourceUid ()I | :91 | -1。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_os_Binder.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-075

**android.os.Debug：固定/占位/有损返回** · JNI历史有意桩

- 成员：android.os.Debug.getMemoryInfo(Landroid/os/Debug$MemoryInfo;)V
- 实现：兼容降级/占位组=固定/占位/有损返回；原声明示例：android.os.Debug.getMemoryInfo (Landroid/os/Debug$MemoryInfo;)V | :58 | void (MemoryInfo left zeroed) | "no PSS/smaps backing on OH"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_os_Debug.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-076

**android.os.GraphicsEnvironment：JNI_FALSE** · JNI历史有意桩

- 成员：android.os.GraphicsEnvironment.getShouldUseAngle(Ljava/lang/String;)Z, android.os.GraphicsEnvironment.isDebuggable()Z
- 实现：兼容降级/占位组=JNI_FALSE；原声明示例：android.os.GraphicsEnvironment.isDebuggable ()Z | :24 | JNI_FALSE | "non-debug build -> production path, no debug GLES layers"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_os_GraphicsEnvironment.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-077

**android.os.GraphicsEnvironment：JNI_TRUE** · JNI历史有意桩

- 成员：android.os.GraphicsEnvironment.setInjectLayersPrSetDumpable()Z
- 实现：兼容降级/占位组=JNI_TRUE；原声明示例：android.os.GraphicsEnvironment.setInjectLayersPrSetDumpable ()Z | :41 | JNI_TRUE | "caller treats failure as ok"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_os_GraphicsEnvironment.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-078

**android.os.GraphicsEnvironment：void** · JNI历史有意桩

- 成员：android.os.GraphicsEnvironment.hintActivityLaunch, android.os.GraphicsEnvironment.nativeToggleAngleAsSystemDriver, android.os.GraphicsEnvironment.setAngleInfo, android.os.GraphicsEnvironment.setDebugLayers, android.os.GraphicsEnvironment.setDebugLayersGLES, android.os.GraphicsEnvironment.setDriverPathAndSphalLibraries, android.os.GraphicsEnvironment.setGpuStats, android.os.GraphicsEnvironment.setLayerPaths
- 实现：兼容降级/占位组=void；原声明示例：android.os.GraphicsEnvironment.setLayerPaths/setDebugLayers/setDebugLayersGLES/setDriverPathAndSphalLibraries/setGpuStats/setAngleInfo/nativeToggleAngleAsSystemDriver/hintActivityLaunch (...)V | :27-45 | void | "no-op" [8 no-ops]。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_os_GraphicsEnvironment.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-079

**android.os.MessageQueue：void** · JNI历史有意桩

- 成员：android.os.MessageQueue.nativeSetFileDescriptorEvents(JII)V
- 实现：兼容降级/占位组=void；原声明示例：android.os.MessageQueue.nativeSetFileDescriptorEvents (JII)V | :128 | void | "HelloWorld doesn't install custom fd watchers"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_os_MessageQueue.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-080

**android.os.Parcel：0** · JNI历史有意桩

- 成员：android.os.Parcel.getGlobalAllocCount()J, android.os.Parcel.getGlobalAllocSize()J, android.os.Parcel.nativeGetOpenAshmemSize(J)J
- 实现：兼容降级/占位组=0；原声明示例：android.os.Parcel.getGlobalAllocSize ()J | :520 | 0 | "process-wide stats -> zeros"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_os_Parcel_aosp.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-081

**android.os.Parcel：JNI_FALSE** · JNI历史有意桩

- 成员：android.os.Parcel.nativeHasFileDescriptors(J)Z, android.os.Parcel.nativeHasFileDescriptorsInRange(JII)Z, android.os.Parcel.nativeReplaceCallingWorkSourceUid(JI)Z
- 实现：兼容降级/占位组=JNI_FALSE；原声明示例：android.os.Parcel.nativeHasFileDescriptors (J)Z | :560 | JNI_FALSE | -。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_os_Parcel_aosp.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-082

**android.os.Parcel：nullptr** · JNI历史有意桩

- 成员：android.os.Parcel.nativeReadFileDescriptor(J)Ljava/io/FileDescriptor;, android.os.Parcel.nativeReadStrongBinder(J)Landroid/os/IBinder;
- 实现：兼容降级/占位组=nullptr；原声明示例：android.os.Parcel.nativeReadStrongBinder (J)Landroid/os/IBinder; | :541 | nullptr | "consume placeholder"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_os_Parcel_aosp.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-083

**android.os.Parcel：void** · JNI历史有意桩

- 成员：android.os.Parcel.nativeEnforceInterface(JLjava/lang/String;)V
- 实现：兼容降级/占位组=void；原声明示例：android.os.Parcel.nativeEnforceInterface (JLjava/lang/String;)V | :574 | void | "silently accept; AIDL-stub not routed to OH IPC"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_os_Parcel_aosp.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-084

**android.os.Parcel：固定/占位/有损返回** · JNI历史有意桩

- 成员：android.os.Parcel.nativeMarkForBinder(JLandroid/os/IBinder;)V, android.os.Parcel.nativeReadCallingWorkSourceUid(J)I, android.os.Parcel.nativeWriteFileDescriptor(JLjava/io/FileDescriptor;)V, android.os.Parcel.nativeWriteInterfaceToken(JLjava/lang/String;)V, android.os.Parcel.nativeWriteStrongBinder(JLandroid/os/IBinder;)V
- 实现：兼容降级/占位组=固定/占位/有损返回；原声明示例：android.os.Parcel.nativeMarkForBinder (JLandroid/os/IBinder;)V | :529 | void (warn-only) | -。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_os_Parcel_aosp.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-085

**android.os.SystemProperties：0** · JNI历史有意桩

- 成员：android.os.SystemProperties.native_find(Ljava/lang/String;)J
- 实现：兼容降级/占位组=0；原声明示例：android.os.SystemProperties.native_find (Ljava/lang/String;)J | :192 | 0 | "find returns opaque handle, 0=not found"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_os_SystemProperties.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-086

**android.os.SystemProperties：defVal** · JNI历史有意桩

- 成员：android.os.SystemProperties.native_get_boolean(JZ)Z, android.os.SystemProperties.native_get_int(JI)I, android.os.SystemProperties.native_get_long(JJ)J
- 实现：兼容降级/占位组=defVal；原声明示例：android.os.SystemProperties.native_get_int (JI)I | :205 | defVal | same。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_os_SystemProperties.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-087

**android.os.SystemProperties：void** · JNI历史有意桩

- 成员：android.os.SystemProperties.native_add_change_callback()V, android.os.SystemProperties.native_report_sysprop_change()V, android.os.SystemProperties.native_set(Ljava/lang/String;Ljava/lang/String;)V
- 实现：兼容降级/占位组=void；原声明示例：android.os.SystemProperties.native_set (Ljava/lang/String;Ljava/lang/String;)V | :222 | void | "OH has no process-writable property store; writes dropped"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_os_SystemProperties.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-088

**android.os.SystemProperties：固定/占位/有损返回** · JNI历史有意桩

- 成员：android.os.SystemProperties.native_get(J)Ljava/lang/String;
- 实现：兼容降级/占位组=固定/占位/有损返回；原声明示例：android.os.SystemProperties.native_get (J)Ljava/lang/String; | :200 | empty string | "handle variants always get handle=0"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_os_SystemProperties.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-089

**android.util.EventLog：void** · JNI历史有意桩

- 成员：android.util.EventLog.readEventsOnWrapping([IJLjava/util/Collection;)V
- 实现：兼容降级/占位组=void；原声明示例：android.util.EventLog.readEventsOnWrapping ([IJLjava/util/Collection;)V | :244 | void | same。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_util_EventLog.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-090

**android.util.EventLog：固定/占位/有损返回** · JNI历史有意桩

- 成员：android.util.EventLog.readEvents([ILjava/util/Collection;)V
- 实现：兼容降级/占位组=固定/占位/有损返回；原声明示例：android.util.EventLog.readEvents ([ILjava/util/Collection;)V | :238 | void (Collection unchanged) | "no event channel on OH"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_util_EventLog.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-091

**android.view.DisplayEventReceiver：0** · JNI历史有意桩

- 成员：android.view.DisplayEventReceiver.nativeGetDisplayEventReceiverFinalizer()J
- 实现：兼容降级/占位组=0；原声明示例：android.view.DisplayEventReceiver.nativeGetDisplayEventReceiverFinalizer ()J | DER_nativeGetDisplayEventReceiverFinalizer | :523 | 0 | "previously returned 0 (feeds NAR(0) crash via ART intrinsic). Real DER_release caused regression; TODO P1 real release fn" [HAZARD: a 0 finalizer handed to NativeAllocationRegistry.app。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_view_DisplayEventReceiver.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-092

**android.view.InputChannel：nullptr** · JNI历史有意桩

- 成员：android.view.InputChannel.nativeGetToken(J)Landroid/os/IBinder;
- 实现：兼容降级/占位组=nullptr；原声明示例：android.view.InputChannel.nativeGetToken (J)Landroid/os/IBinder; | IC_nativeGetToken | :224 | nullptr | "no InputDispatcher; Java callers null-check (ViewRootImpl.setView)"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_view_InputChannel.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-093

**android.view.InputChannel：void** · JNI历史有意桩

- 成员：android.view.InputChannel.nativeWriteToParcel(Landroid/os/Parcel;J)V
- 实现：兼容降级/占位组=void；原声明示例：android.view.InputChannel.nativeWriteToParcel (Landroid/os/Parcel;J)V | IC_nativeWriteToParcel | :195 | void | "read side allocates fresh"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_view_InputChannel.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-094

**android.view.InputChannel：固定/占位/有损返回** · JNI历史有意桩

- 成员：android.view.InputChannel.nativeReadFromParcel(Landroid/os/Parcel;)J
- 实现：兼容降级/占位组=固定/占位/有损返回；原声明示例：android.view.InputChannel.nativeReadFromParcel (Landroid/os/Parcel;)J | IC_nativeReadFromParcel | :185 | placeholder OhInputChannel* | "channels not Parcel-transported in adapter; alloc fresh placeholder so nativeGetName/Dispose work"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_view_InputChannel.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-095

**android.view.InputEventReceiver：JNI_FALSE** · JNI历史有意桩

- 成员：android.view.InputEventReceiver.nativeConsumeBatchedInputEvents(JJ)Z
- 实现：兼容降级/占位组=JNI_FALSE；原声明示例：android.view.InputEventReceiver.nativeConsumeBatchedInputEvents (JJ)Z | IER_nativeConsumeBatchedInputEvents | :856 | JNI_FALSE | "no frame-time batching; one-per-MOVE; jank acceptable"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_view_InputChannel.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-096

**android.view.InputEventReceiver：void** · JNI历史有意桩

- 成员：android.view.InputEventReceiver.nativeFinishInputEvent(JIZ)V, android.view.InputEventReceiver.nativeReportTimeline(JIJJ)V
- 实现：兼容降级/占位组=void；原声明示例：android.view.InputEventReceiver.nativeReportTimeline (JIJJ)V | IER_nativeReportTimeline | android_view_InputEventReceiver.cpp:850 | void | "Choreographer FrameInfo timeline; not needed for input"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_view_InputChannel.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-097

**android.view.InputEventReceiver：固定/占位/有损返回** · JNI历史有意桩

- 成员：android.view.InputEventReceiver.nativeDump(JLjava/lang/String;)Ljava/lang/String;
- 实现：兼容降级/占位组=固定/占位/有损返回；原声明示例：android.view.InputEventReceiver.nativeDump (JLjava/lang/String;)Ljava/lang/String; | IER_nativeDump | :863 | empty string | -。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_view_InputChannel.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-098

**android.view.KeyCharacterMap：0** · JNI历史有意桩

- 成员：android.view.KeyCharacterMap.nativeGetCharacter(JII)C, android.view.KeyCharacterMap.nativeGetDisplayLabel(JI)C, android.view.KeyCharacterMap.nativeGetKeyboardType(J)I, android.view.KeyCharacterMap.nativeGetMatch(JI[CI)C, android.view.KeyCharacterMap.nativeGetNumber(JI)C
- 实现：兼容降级/占位组=0；原声明示例：android.view.KeyCharacterMap.nativeGetCharacter (JII)C | :163 | 0 | "mMap permanently nullptr"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_view_KeyCharacterMap_aosp.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-099

**android.view.KeyCharacterMap：false** · JNI历史有意桩

- 成员：android.view.KeyCharacterMap.nativeGetFallbackAction(JIILandroid/view/KeyCharacterMap$FallbackAction;)Z
- 实现：兼容降级/占位组=false；原声明示例：android.view.KeyCharacterMap.nativeGetFallbackAction (JIILandroid/view/KeyCharacterMap$FallbackAction;)Z | :174 | false | -。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_view_KeyCharacterMap_aosp.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-100

**android.view.KeyCharacterMap：void** · JNI历史有意桩

- 成员：android.view.KeyCharacterMap.nativeWriteToParcel(JLandroid/os/Parcel;)V
- 实现：兼容降级/占位组=void；原声明示例：android.view.KeyCharacterMap.nativeWriteToParcel (JLandroid/os/Parcel;)V | :151 | void | same。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_view_KeyCharacterMap_aosp.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-101

**android.view.KeyCharacterMap：固定/占位/有损返回** · JNI历史有意桩

- 成员：android.view.KeyCharacterMap.nativeGetEvents(J[C)[Landroid/view/KeyEvent;, android.view.KeyCharacterMap.nativeReadFromParcel(Landroid/os/Parcel;)J
- 实现：兼容降级/占位组=固定/占位/有损返回；原声明示例：android.view.KeyCharacterMap.nativeReadFromParcel (Landroid/os/Parcel;)J | :143 | placeholder NativeKeyCharacterMap* | "no cross-proc KCM Parcel; fresh empty so Dispose works"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_view_KeyCharacterMap_aosp.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-102

**android.view.MotionEvent：unsupported** · JNI历史有意桩

- 成员：android.view.MotionEvent.nativeReadFromParcel(JLandroid/os/Parcel;)J, android.view.MotionEvent.nativeWriteToParcel(JLandroid/os/Parcel;)V
- 实现：兼容降级/占位组=unsupported；原声明示例：android.view.MotionEvent.nativeReadFromParcel (JLandroid/os/Parcel;)J | :379 | throws UnsupportedOperationException, 0 | "MotionEvent Parcel I/O not implemented in Phase 1"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_view_MotionEvent_aosp.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-103

**android.view.Surface：0** · JNI历史有意桩

- 成员：android.view.Surface.nativeAttachAndQueueBufferWithColorSpace(JLandroid/hardware/HardwareBuffer;I)I, android.view.Surface.nativeCreateFromSurfaceTexture(Landroid/graphics/SurfaceTexture;)J, android.view.Surface.nativeForceScopedDisconnect(J)I, android.view.Surface.nativeGetNextFrameNumber(J)J, android.view.Surface.nativeLockCanvas(JLandroid/graphics/Canvas;Landroid/graphics/Rect;)J, android.view.Surface.nativeSetAutoRefreshEnabled(JZ)I, android.view.Surface.nativeSetFrameRate(JFII)I, android.view.Surface.nativeSetScalingMode(JI)I, android.view.Surface.nativeSetSharedBufferModeEnabled(JZ)I
- 实现：兼容降级/占位组=0；原声明示例：android.view.Surface.nativeCreateFromSurfaceTexture (Landroid/graphics/SurfaceTexture;)J | S_nativeCreateFromSurfaceTexture | :189 | 0 | "HelloWorld doesn't use SurfaceTexture; return 0"。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_graphics_compat_shim.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-104

**android.view.Surface：JNI_FALSE** · JNI历史有意桩

- 成员：android.view.Surface.nativeIsConsumerRunningBehind(J)Z
- 实现：兼容降级/占位组=JNI_FALSE；原声明示例：android.view.Surface.nativeIsConsumerRunningBehind (J)Z | S_nativeIsConsumerRunningBehind | :212 | JNI_FALSE | -。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_graphics_compat_shim.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-105

**android.view.Surface：void** · JNI历史有意桩

- 成员：android.view.Surface.nativeAllocateBuffers(J)V, android.view.Surface.nativeDestroy(J)V, android.view.Surface.nativeRelease(J)V, android.view.Surface.nativeUnlockCanvasAndPost(JLandroid/graphics/Canvas;)V, android.view.Surface.nativeWriteToParcel(JLandroid/os/Parcel;)V
- 实现：兼容降级/占位组=void；原声明示例：android.view.Surface.nativeRelease (J)V | S_nativeRelease | :208 | void | -。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_graphics_compat_shim.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-106

**android.view.Surface：固定/占位/有损返回** · JNI历史有意桩

- 成员：android.view.Surface.nativeGetHeight(J)I, android.view.Surface.nativeGetWidth(J)I, android.view.Surface.nativeReadFromParcel(JLandroid/os/Parcel;)J
- 实现：兼容降级/占位组=固定/占位/有损返回；原声明示例：android.view.Surface.nativeReadFromParcel (JLandroid/os/Parcel;)J | S_nativeReadFromParcel | :215 | nativeObject (parcel ignored) | -。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_graphics_compat_shim.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-107

**android.view.SurfaceControl：returns 0 / empty (3)** · JNI历史有意桩

- 成员：android.view.SurfaceControl.nativeCreateJankDataListenerWrapper, android.view.SurfaceControl.nativeGetCompositionDataspaces, android.view.SurfaceControl.nativeGetGPUContextPriority, android.view.SurfaceControl.nativeGetTransformHint
- 实现：兼容降级/占位组=returns 0 / empty (3)；原声明示例：# returns 0 / empty (3): nativeGetTransformHint:445(0=IDENTITY) nativeGetGPUContextPriority:634(0) nativeCreateJankDataListenerWrapper:630(0 null-token) nativeGetCompositionDataspaces:643(empty int[])。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_view_SurfaceControl.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-108

**android.view.SurfaceControl：returns JNI_FALSE (8)** · JNI历史有意桩

- 成员：android.view.SurfaceControl.nativeGetBootDisplayModeSupport, android.view.SurfaceControl.nativeGetDisplayBrightnessSupport, android.view.SurfaceControl.nativeGetProtectedContentSupport, android.view.SurfaceControl.nativeSetActiveColorMode, android.view.SurfaceControl.nativeSetDesiredDisplayModeSpecs, android.view.SurfaceControl.nativeSetDisplayBrightness, android.view.SurfaceControl.nativeSetDisplayedContentSamplingEnabled
- 实现：兼容降级/占位组=returns JNI_FALSE (8)；原声明示例：# returns JNI_FALSE (8): nativeGetBootDisplayModeSupport:592 nativeSetActiveColorMode:535 nativeSetDesiredDisplayModeSpecs:538 nativeSetDisplayBrightness:541 nativeGetDisplayBrightnessSupport:544 nativeSetDisplayedContentSamplingEnabled:547 nativeGetProtectedContentSupport:640。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_view_SurfaceControl.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-109

**android.view.SurfaceControl：returns JNI_TRUE (5, "always succeeded/booted")** · JNI历史有意桩

- 成员：android.view.SurfaceControl.nativeBootFinished, android.view.SurfaceControl.nativeClearAnimationFrameStats, android.view.SurfaceControl.nativeClearContentFrameStats, android.view.SurfaceControl.nativeGetAnimationFrameStats, android.view.SurfaceControl.nativeGetContentFrameStats
- 实现：兼容降级/占位组=returns JNI_TRUE (5, "always succeeded/booted")；原声明示例：# returns JNI_TRUE (5, "always succeeded/booted"): nativeClearContentFrameStats:385 nativeGetContentFrameStats:386 nativeClearAnimationFrameStats:387 nativeGetAnimationFrameStats:388 nativeBootFinished:622。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_view_SurfaceControl.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-110

**android.view.SurfaceControl：returns nullptr (7)** · JNI历史有意桩

- 成员：android.view.SurfaceControl.nativeGetDefaultApplyToken, android.view.SurfaceControl.nativeGetDisplayDecorationSupport, android.view.SurfaceControl.nativeGetDisplayNativePrimaries, android.view.SurfaceControl.nativeGetDisplayedContentSample, android.view.SurfaceControl.nativeGetDynamicDisplayInfo, android.view.SurfaceControl.nativeGetOverlaySupport, android.view.SurfaceControl.nativeGetStaticDisplayInfo
- 实现：兼容降级/占位组=returns nullptr (7)；原声明示例：# returns nullptr (7): nativeGetDisplayedContentSample:550 nativeGetDisplayDecorationSupport:553 nativeGetDisplayNativePrimaries:556 nativeGetDynamicDisplayInfo:559 nativeGetStaticDisplayInfo:562 nativeGetOverlaySupport:637 nativeGetDefaultApplyToken:647。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_view_SurfaceControl.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-111

**android.view.SurfaceControl：returns void log-only (22)** · JNI历史有意桩

- 成员：android.view.SurfaceControl.nativeAddWindowInfosReportedListener, android.view.SurfaceControl.nativeClearBootDisplayMode, android.view.SurfaceControl.nativeRemoveCurrentInputFocus, android.view.SurfaceControl.nativeSanitize, android.view.SurfaceControl.nativeSetAutoLowLatencyMode, android.view.SurfaceControl.nativeSetBootDisplayMode, android.view.SurfaceControl.nativeSetDefaultApplyToken, android.view.SurfaceControl.nativeSetDisplayFlags, android.view.SurfaceControl.nativeSetDisplayLayerStack, android.view.SurfaceControl.nativeSetDisplayPowerMode, android.view.SurfaceControl.nativeSetDisplayProjection, android.view.SurfaceControl.nativeSetDisplaySize, android.view.SurfaceControl.nativeSetDisplaySurface, android.view.SurfaceControl.nativeSetFixedTransformHint, android.view.SurfaceControl.nativeSetFocusedWindow, android.view.SurfaceControl.nativeSetGameContentType, android.view.SurfaceControl.nativeSetInputWindowInfo, android.view.SurfaceControl.nativeSetLayerStack, android.view.SurfaceControl.nativeSetMetadata, android.view.SurfaceControl.nativeSetTransformHint
- 实现：兼容降级/占位组=returns void log-only (22)；原声明示例：# returns void log-only (22): nativeSetLayerStack:472 nativeSetTransformHint:480 nativeSetMetadata:487 nativeAddWindowInfosReportedListener:510 nativeSetFixedTransformHint:526 nativeSanitize:615 nativeSetFocusedWindow:603 nativeSetInputWindowInfo:607 nativeSetGameContentType:596 nativeSetAutoLowLatencyMode:599 nativeSe。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_view_SurfaceControl.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-112

**android.view.SurfaceControl：returns void no-op (28)** · JNI历史有意桩

- 成员：android.view.SurfaceControl.nativeAddJankDataListener, android.view.SurfaceControl.nativeClearTrustedPresentationCallback, android.view.SurfaceControl.nativeRemoveJankDataListener, android.view.SurfaceControl.nativeSetBlurRegions, android.view.SurfaceControl.nativeSetBuffer, android.view.SurfaceControl.nativeSetBufferTransform, android.view.SurfaceControl.nativeSetCachingHint, android.view.SurfaceControl.nativeSetColorSpaceAgnostic, android.view.SurfaceControl.nativeSetColorTransform, android.view.SurfaceControl.nativeSetDamageRegion, android.view.SurfaceControl.nativeSetDataSpace, android.view.SurfaceControl.nativeSetDefaultFrameRateCompatibility, android.view.SurfaceControl.nativeSetDimmingEnabled, android.view.SurfaceControl.nativeSetDropInputMode, android.view.SurfaceControl.nativeSetExtendedRangeBrightness, android.view.SurfaceControl.nativeSetFrameRate, android.view.SurfaceControl.nativeSetFrameRateSelectionPriority, android.view.SurfaceControl.nativeSetFrameTimelineVsync, android.view.SurfaceControl.nativeSetGlobalShadowSettings, android.view.SurfaceControl.nativeSetRelativeLayer, android.view.SurfaceControl.nativeSetShadowRadius, android.view.SurfaceControl.nativeSetStretchEffect, android.view.SurfaceControl.nativeSetTransparentRegionHint, android.view.SurfaceControl.nativeSetTrustedOverlay, android.view.SurfaceControl.nativeSetTrustedPresentationCallback, android.view.SurfaceControl.nativeSurfaceFlushJankData, android.view.SurfaceControl.nativeUnsetBuffer, android.view.SurfaceControl.nativeWriteTransactionToParcel
- 实现：兼容降级/占位组=returns void no-op (28)；原声明示例：# returns void no-op (28): nativeSetShadowRadius:419 nativeSetFrameRate:425 nativeSetTrustedOverlay:371 nativeSurfaceFlushJankData:373 nativeSetRelativeLayer:278 nativeSetTransparentRegionHint:293 nativeSetColorTransform:304 nativeSetColorSpaceAgnostic:418 nativeSetBlurRegions:368 nativeSetStretchEffect:369 nativeSetFr。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_view_SurfaceControl.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-113

**com.android.internal.os.BinderInternal：nullptr** · JNI历史有意桩

- 成员：com.android.internal.os.BinderInternal.getContextObject()Landroid/os/IBinder;
- 实现：兼容降级/占位组=nullptr；原声明示例：com.android.internal.os.BinderInternal.getContextObject ()Landroid/os/IBinder; | :102 | nullptr。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_os_Binder.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-114

**com.android.internal.os.BinderInternal：void** · JNI历史有意桩

- 成员：com.android.internal.os.BinderInternal.handleGc()V
- 实现：兼容降级/占位组=void；原声明示例：com.android.internal.os.BinderInternal.handleGc ()V | :103 | void。回退不能冒充真实硬件/Android服务。
- 源码 / 产物：bms/src/adapter/framework/android-runtime/src/android_os_Binder.cpp；source4d5cac38ff，runtime ac59dec0，完整同源件SHA unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：2026-10-02 census / ac59历史profile；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：本条Android实际对照版本/APK targetSdk/OH实测版本没有直接钉值，保持unknown；不能由源版本或build名推成支持范围。；原表有压缩名称/不完整签名，签名unknown；reported325≠本行名称数；ART最后注册和libhwui覆盖未重新核，对source-build r86后续实现不可外推。

- [stubs-full.txt](<../../../../westlake-harness/benchmark/2026-10-02-runtime-stub-census/evidence/stubs-full.txt>)：reported325有意JNI桩；压缩名/签名按原表保留；SHA256 `a07f57d77fdf025765b6d2ed02f4e6c923f3814eab96762331cd11fb12891076`

### NATIVE-115

**SQLiteConnection 真实JNI→sqlite3** · JNI/数据库

- 成员：android.database.sqlite.SQLiteConnection.nativeOpen, android.database.sqlite.SQLiteConnection.nativePrepareStatement, android.database.sqlite.SQLiteConnection.nativeExecute
- 实现：U13编入android_database_SQLiteConnection.cpp真实TU，注册27方法并走sqlite3，不是Boat的弱return0 registrar；JNI注册完整不保证文件权限、CANTOPEN或所有SQL语义。
- 源码 / 产物：benchmark/2026-10-10-boat-runtime-jni-gap/README.md 中源码/产物谱系；U13 18763dd4；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：android-14.0.0_r1（源码证据，不是Android对照机）；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U13 18763dd4；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-10-boat-runtime-jni-gap/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `162d328abe01af2267b4462fc1191ed3a4c39c9a52ac46729678471a0e9293b1`
- [u13-tables.json](<../../../../westlake-harness/benchmark/2026-10-10-boat-runtime-jni-gap/u13-tables.json>)：精确18763dd4静态注册表、函数地址与方法签名；不证明本轮实际执行；SHA256 `938383bc50533e6824b64f5525363be4f8a09ddf9672dbb65e09e6bef1e012c8`

### NATIVE-116

**CursorWindow本进程缓存与SQLiteGlobal/Debug** · JNI/数据库

- 成员：android.database.CursorWindow.nativeCreate, android.database.CursorWindow.nativePutString, android.database.sqlite.SQLiteGlobal.nativeReleaseMemory, android.database.sqlite.SQLiteDebug.nativeGetPagerStats
- 实现：U13 21/1/1表包含本地窗口和SQLite操作；Parcel跨进程两方法仍另列stub，不把IPC无实现藏进真实窗口行。
- 源码 / 产物：benchmark/2026-10-10-boat-runtime-jni-gap/README.md 中源码/产物谱系；U13 18763dd4；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U13 18763dd4；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-10-boat-runtime-jni-gap/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `162d328abe01af2267b4462fc1191ed3a4c39c9a52ac46729678471a0e9293b1`
- [u13-tables.json](<../../../../westlake-harness/benchmark/2026-10-10-boat-runtime-jni-gap/u13-tables.json>)：真实CursorWindow/SQLiteGlobal/Debug表；Parcel桩另行保留；SHA256 `938383bc50533e6824b64f5525363be4f8a09ddf9672dbb65e09e6bef1e012c8`

### NATIVE-117

**Boat覆盖runtime导致SQLite真实注册缺失** · JNI/注册

- 成员：register_android_database_SQLiteConnection, register_android_database_CursorWindow, register_android_database_SQLiteGlobal, register_android_database_SQLiteDebug
- 实现：adc125f4是libandroid9ccf49字节改件被别名放到runtime；四registrar弱return0替代真实TU，无nativeOpen；349表差/520导出差不是APK挡住数。
- 源码 / 产物：benchmark/2026-10-10-boat-runtime-jni-gap/README.md 中源码/产物谱系；Boat adc125f4 vs U13 18763dd4；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：Boat adc125f4 vs U13 18763dd4；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-10-boat-runtime-jni-gap/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `162d328abe01af2267b4462fc1191ed3a4c39c9a52ac46729678471a0e9293b1`
- [missing-methods.json](<../../../../westlake-harness/benchmark/2026-10-10-boat-runtime-jni-gap/missing-methods.json>)：349个类/TU范围表差，不是349挡住app；SHA256 `023e0f0eeacc77630b5fe2f802992ba659103acf62f7e8374ae9404d8c6cf614`

### NATIVE-118

**NDK CPU lock/post真实队列与fence适配** · 图形/窗口

- 成员：ANativeWindow_lock, ANativeWindow_unlockAndPost
- 实现：8728134a小shim引用唯一runtime和libsurface.z；oh_anw_get_oh解包、usage3/dequeue、BufferHandle真实映射、fence等待/失败取消、mutex保护。报告行为夹具过，不等于21消费者全部亮。
- 源码 / 产物：benchmark/2026-10-01-u11-native/README.md 中源码/产物谱系；U11 candidate 8728134a；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U11 candidate 8728134a；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-01-u11-native/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `d6280df3d1be97fe4f9236628f93d93937a63bb730624e8493e6d14407b8dca3`
- [owner_wrappers.c](<../../../../westlake-harness/benchmark/2026-10-01-u11-native/window-lock/owner_wrappers.c>)：真实dequeue/fence/map/queue包装源码；SHA256 `1eb348fc11aba4f8afb0138a7293b3a563b173f51b2d0c45e3ec87e1ae8cfa27`

### NATIVE-119

**跨拷贝NativeWindow反查M1** · 图形/窗口

- 成员：ANativeWindow_fromSurface, m1_native_window_from_other_copies
- 实现：M1通过runtime导出/遍历已映射拷贝反查窗口；t4拆成m1_copy TU，PLT可抢占；1d42相对94c3仅既定变化，单owner和FZ-009复验必须按具体bundle。
- 源码 / 产物：benchmark/2026-10-03-u16-t4-m1-runtime/README.md 中源码/产物谱系；U16 candidate1d42dbfb / U15 94c31177；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U16 candidate1d42dbfb / U15 94c31177；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-03-u16-t4-m1-runtime/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `70371e04f35e067ee04e714a8b608a094a637fd2287121ad5dfe8fc3e14ffb40`

### NATIVE-120

**U14对话子窗口Z序与finish后后台** · 图形/窗口

- 成员：WindowSessionProperty::SetSubWindowZLevel, WindowSessionAdapter::relayout
- 实现：bridge7daa5435的M5/M6仅改对应窗口函数；ddmodel2是否移动依赖runtime M1，不用旧无M1预测替代U14结果。
- 源码 / 产物：benchmark/2026-10-03-u14-bridge-m5-m6/README.md 中源码/产物谱系；U14 bridge7daa5435 / runtime18763dd4；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U14 bridge7daa5435 / runtime18763dd4；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-03-u14-bridge-m5-m6/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `c5b3d7e0580191bc1cd177dc48dd29068b00c1fb8cee402c438afedf077f2037`

### NATIVE-121

**Flutter proc-address窗口解包钩子** · 图形/EGL

- 成员：eglGetProcAddress, eglCreateWindowSurface, eglDestroySurface, eglSwapBuffers, eglSwapBuffersWithDamageKHR
- 实现：eb90a640先返回自身4个EGL窗口/surface包装，再委托平台resolver；是ANW转接不是GPU实现；只westlake_flutter槽，不改westlake_native。
- 源码 / 产物：benchmark/2026-10-03-u16-flutter-egl-names/README.md 中源码/产物谱系；U16 A‴eb90a640 vs U15 9b824502；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U16 A‴eb90a640 vs U15 9b824502；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-03-u16-flutter-egl-names/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `1f1af0581c055dba025959d21d2e7f95018fecac3024f791221e6ca5fdf19364`
- [flutter_egl_getprocaddress.cpp](<../../../../westlake-harness/benchmark/2026-10-03-u16-flutter-egl-names/src/flutter_egl_getprocaddress.cpp>)：四EGL函数名返回自身包装后平台委托；SHA256 `fbc96152cddb826407bcd43eed5e3bd0c022e8b7a908528e33cbddedb025435b`

### NATIVE-122

**Bitmap JNI真实owner与空ColorSpace边界** · 图形/Bitmap

- 成员：android.graphics.Bitmap.nativeComputeColorSpace, android.graphics.Bitmap.nativeIsSRGB, android.graphics.Bitmap.nativeSetColorSpace
- 实现：真实JNI在libhwui be59260f，nativeComputeColorSpace注册与AOSP14对应但源bitmap的SkColorSpace可真实为null；不是runtime漏注册，后续Java sRGB隐式fallback归java分片。
- 源码 / 产物：benchmark/2026-10-03-bitmap-colorspace/README.md 中源码/产物谱系；U13/U12 libhwui be59260f；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：AOSP14 Bitmap.cpp 对照；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U13/U12 libhwui be59260f；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-03-bitmap-colorspace/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `906a3b04b3eb16e0e02606408bc48ba223c729c54158aed17699c846e7571777`

### NATIVE-123

**AMedia状态API合法unsupported边界** · 媒体/NDK

- 成员：AImageReader_acquireLatestImage, AImageReader_getWindow, AImageReader_newWithUsage, AImageReader_setBufferRemovedListener, AImageReader_setImageListener, AImage_getHardwareBuffer, AImage_getTimestamp, AImage_getWidth, AMediaCodec_configure, AMediaCodec_delete, AMediaCodec_flush, AMediaCodec_queueInputBuffer, AMediaCodec_releaseOutputBuffer, AMediaCodec_setOutputSurface, AMediaCodec_start, AMediaCodec_stop, AMediaExtractor_seekTo, AMediaExtractor_selectTrack, AMediaExtractor_setDataSource, AMediaExtractor_setDataSourceCustom, AMediaExtractor_setDataSourceFd
- 实现：50实际Unity导入拆成13行为组；本行仅21个status型unsupported接口，返回AOSP合法AMEDIA_ERROR_UNSUPPORTED=-10002且清输出；AMediaFormat/DataSource小容器的真实分配/读写/释放另行列，不将50个全称空桩。无Codec/Stagefright/OH解码引擎。
- 源码 / 产物：benchmark/2026-10-02-u12-mediandk/candidate.c + objects.c.inc，原型inputs/aosp14；build-receipt.json绑定 libmediandk 8fc0752dd561a62992268981164c5e75c87ceb802f93d6d0b958c23b54ddaa58
- Android 源码：android-14.0.0_r1 frameworks/av 402dbe885fd58af75e4c1d7e790fbf4bb22f29f9；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：AArch64 LP64：off_t=8、AMediaCodecBufferInfo=24，构建回执--target=aarch64-linux-ohos；其他ABI unknown；路由 / 代际：U12 candidate8fc0752d；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `b95908dd925d1103f08187b2089b0736a29c39d94936f6974eab88fbe3daef60`
- [api.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/api.json>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `1ba36522c5df5c3146a4ff55e300a1d5a3ac71a4ccd16d074623c7a81bfe051f`
- [candidate.c](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/candidate.c>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `666d51171718cb19a5922d744e2332edbbd6a45e0b578e94109b1ee8c581776b`
- [build-receipt.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/build-receipt.json>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `fe9b781dade79cd0e1de5e597ab42eb43e2ad187a571075422b885528a734739`

### NATIVE-124

**Android↔OH整数宽度与IID真实转接原语** · 音频/OpenSLES

- 成员：slCreateEngine, SL_IID_ANDROIDCONFIGURATION, SL_IID_ANDROIDSIMPLEBUFFERQUEUE
- 实现：移植四上游commit的结构/队列算法，Android32 vs OH64与16↔24字节IID字段换算、continuous queue有夹具；route-A真实backend注入/单owner准入尚未证。
- 源码 / 产物：benchmark/2026-10-02-u12-upstream-audio/README.md 中源码/产物谱系；U12 offline primitives / OH owner05d8ac90；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U12 offline primitives / OH owner05d8ac90；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-u12-upstream-audio/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `d1d71e9b848a9c8fd6d9a4f59a6fabaa72520d23d351c53415cfffd8bb81b6eb`

### NATIVE-125

**PLAY completion及回调尚无真实实现** · 音频/OpenSLES

- 成员：SLPlayItf::RegisterCallback, SLPlayItf::SetCallbackEventsMask
- 实现：现役OH05d8两方法返回12 FEATURE_UNSUPPORTED；上游c7d2992仍委托OH PLAY，原样抄不能解除墙；真实AudioRenderer completion未交，不把ledger成功当该route成功。
- 源码 / 产物：benchmark/2026-10-02-u12-upstream-audio/README.md 中源码/产物谱系；U10.1/U12 OH05d8 owner；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U10.1/U12 OH05d8 owner；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-u12-upstream-audio/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `d1d71e9b848a9c8fd6d9a4f59a6fabaa72520d23d351c53415cfffd8bb81b6eb`

### NATIVE-126

**Android _ctype_指针与257字节原表** · Bionic/ctype

- 成员：_ctype_
- 实现：AOSP原ctype_.c无改表；8字节GLOBAL指针指LOCAL257字节EOF+ASCII表，不导出裸数组。b8a87源/ELF表逐字等，符号存在不保证Realm relocation scope。
- 源码 / 产物：benchmark/2026-10-03-u13-compat-ctype/README.md 中源码/产物谱系；U13 compat-v2 b8a87f6f；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：android-14.0.0_r1 bionic e4df46f213d8d363017dce7ded5d1f2159614425；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U13 compat-v2 b8a87f6f；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-03-u13-compat-ctype/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `88e43bf4a9b95be2ee107b86d3c5846042e542fae85de2d5e22b63e763b5c823`
- [ctype_compat.c](<../../../../westlake-harness/benchmark/2026-10-03-u13-compat-ctype/ctype_compat.c>)：_ctype_指针/257字节大小断言与原表直接include；SHA256 `2908c8c0ba6e0e2dcec6d71cf9023a5731fd29e1d354919de54c548f514776a2`
- [ctype_.c](<../../../../westlake-harness/benchmark/2026-10-03-u13-compat-ctype/inputs/aosp/libc/upstream-openbsd/lib/libc/gen/ctype_.c>)：AOSP14r1原表不改；SHA256 `8fc63bd8bbfd6e17b2b55701a68a6e02dc6fb27f4d99eac277175863d7cf12f4`

### NATIVE-127

**strtoll_l/strtoull_l locale包装** · Bionic/locale

- 成员：strtoll_l, strtoull_l
- 实现：按AOSP stdlib_l委托strtoll/strtoull且忽略locale，保留endptr/base/ERANGE；不是改变全进程locale。候选b2be657c与resident scope分开。
- 源码 / 产物：benchmark/2026-10-02-u12-vlc-bionic-residue/README.md 中源码/产物谱系；U12 compat b2be657c；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：AOSP14r1 stdlib_l.cpp:49/57；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U12 compat b2be657c；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-u12-vlc-bionic-residue/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `aac7339c367c71b8d7a7021abe6e3a8e4325d45b0bdff8731a061a37558a553b`
- [vlc_bionic_residue.c](<../../../../westlake-harness/benchmark/2026-10-02-u12-vlc-bionic-residue/vlc_bionic_residue.c>)：locale委托与真实OH cleanup栈字段转换、线程退出回调；SHA256 `a600f0d5a8af4cb2ea8e9fc1bb603adf8c188b5ae0c992630227682f2e2c2474`

### NATIVE-128

**cleanup push/pop记录布局真实翻译** · Bionic/pthread

- 成员：__pthread_cleanup_push, __pthread_cleanup_pop
- 实现：Android/OH都24字节但字段序不同，转换后使用OH真实cleanup栈，覆盖pthread_exit；不以TLS-only no-op冒认。
- 源码 / 产物：benchmark/2026-10-02-u12-vlc-bionic-residue/README.md 中源码/产物谱系；U12 compat b2be657c；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：AOSP14r1 pthread_exit.cpp，NDK23仅布局参考；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U12 compat b2be657c；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-u12-vlc-bionic-residue/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `aac7339c367c71b8d7a7021abe6e3a8e4325d45b0bdff8731a061a37558a553b`
- [vlc_bionic_residue.c](<../../../../westlake-harness/benchmark/2026-10-02-u12-vlc-bionic-residue/vlc_bionic_residue.c>)：locale委托与真实OH cleanup栈字段转换、线程退出回调；SHA256 `a600f0d5a8af4cb2ea8e9fc1bb603adf8c188b5ae0c992630227682f2e2c2474`

### NATIVE-129

**errno及cmsg辅助函数新增候选** · Bionic/libc

- 成员：__errno, __cmsg_nxthdr
- 实现：4698c0a5加两导出；015aa基座__errno为LOCAL且cmsg缺失，不能由源map臆测动态导出。函数补齐不证明纳入app重定位scope。
- 源码 / 产物：benchmark/2026-10-02-toutiao-bionic-scope/README.md 中源码/产物谱系；U10.1 015aa3a6 -> candidate4698c0a5；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U10.1 015aa3a6 -> candidate4698c0a5；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-toutiao-bionic-scope/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `d05dfcb41dcdddf41ea44a45fd4e99da87fe3b15b0a2a002ad19ddfb9b5175b8`

### NATIVE-130

**dlext仅空flags可用，其他扩展拒绝** · Bionic/动态链接

- 成员：android_dlopen_ext
- 实现：weak __loader后端存在才真实转调；NULL extinfo/flags0走dlopen；非零flags缺后端时ENOTSUP+NULL。PPSSPP实际0x200/0x210非空，不能算修复。
- 源码 / 产物：benchmark/2026-10-03-u14-native-abi-gecko/README.md 中源码/产物谱系；U14 native_abi7605812c复制U10 015aa行为；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U14 native_abi7605812c复制U10 015aa行为；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-03-u14-native-abi-gecko/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `054587e99e0522c6f13954f75d2129740f69d403911fb78543b73e8a92a95efd`
- [android_dlopen_ext.c](<../../../../westlake-harness/benchmark/2026-10-03-u14-native-abi-gecko/src/android_dlopen_ext.c>)：弱后端转调、无后端非零扩展ENOTSUP；不是忽略extinfo；SHA256 `7337a3935c426801002ca56508189ea2e74d7d59a3cc4600b46c9e3b3f2e1649`

### NATIVE-131

**Gecko LIBC版本入口与fortify/strerror** · Bionic/版本与路由

- 成员：__gnu_strerror_r, __open_2, __strncpy_chk2, __assert2, __pthread_cleanup_push, __pthread_cleanup_pop
- 实现：native_abi加真实body和LIBC版本节点，通过consumer静态replay；LIBC_O callback另节点，弱dlext扩展仍拒。GNU strerror使用char* ABI，fortify非法参数可abort不是空桩成功。
- 源码 / 产物：benchmark/2026-10-03-u14-native-abi-gecko/README.md 中源码/产物谱系；U14 native_abi7605812c；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U14 native_abi7605812c；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-03-u14-native-abi-gecko/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `054587e99e0522c6f13954f75d2129740f69d403911fb78543b73e8a92a95efd`
- [gecko_abi.c](<../../../../westlake-harness/benchmark/2026-10-03-u14-native-abi-gecko/src/gecko_abi.c>)：GNU strerror、fortify、cmsg、locale和cleanup实际方法体；SHA256 `09aef138c904c2656925faf8d1326ddeb73734a22560d742a7930a1c5a01f61d`
- [native_abi_gecko.map](<../../../../westlake-harness/benchmark/2026-10-03-u14-native-abi-gecko/src/native_abi_gecko.map>)：LIBC/LIBC_O版本节点出口；不等于任意app可见；SHA256 `14bb2fbbb7254ac8591504f82bb4ce27819f0b6c6ad2063a5dcff1c7f3e3df5f`

### NATIVE-132

**Realm native域ctype补齐** · Bionic/版本与路由

- 成员：_ctype_
- 实现：f8619ad5=7605+原ctype一导出，44函数不变；RTLD_GLOBAL native_abi与NEEDED liblog/private libandroid组成实际provider集合。静态replay0missing不是McD/Element整app通过。
- 源码 / 产物：benchmark/2026-10-03-u14-native-abi-v2/README.md 中源码/产物谱系；U14 native_abi f8619ad5；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：AOSP14r1原ctype表；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U14 native_abi f8619ad5；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-03-u14-native-abi-v2/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `033e3beb034454d42e72611bc21b59b999ff9124e6cdec9af7827368440ca7b9`

### NATIVE-133

**私有zlib窄路由/别名** · NDK/加载路由

- 成员：dlopen_ns, inflate, deflate, zlibVersion
- 实现：N8仅删root libz壳、保留private alias和provider；N10 owner routing按域解析；不把库同名/SONAME同当scope完整或全局默认fallback。
- 源码 / 产物：benchmark/2026-10-01-n8-native/README.md 中源码/产物谱系；N8 manifest3dd48299；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：N8 manifest3dd48299；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-01-n8-native/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `37649a0fea6c30753a2f920c0c890944a89bf5907a57f74b3deeb6b0a1f1c78a`

### NATIVE-134

**media_jni映射现驻runtime而非mediandk** · JNI/媒体注册

- 成员：android.media.MediaPlayer.native_init, System.loadLibrary("media_jni")
- 实现：棋钟框架clinit先load media_jni再native_init；U12mediandk不能解此manifest墙，须system_libraries绑定常驻runtime并resident-only，真实后续播放未证。
- 源码 / 产物：benchmark/2026-10-02-u12-mediandk/README.md 中源码/产物谱系；U13 policy / resident owner路线；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U13 policy / resident owner路线；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `b95908dd925d1103f08187b2089b0736a29c39d94936f6974eab88fbe3daef60`

### NATIVE-135

**Jitsi native域双名单与runtime可见** · NDK/路由

- 成员：native_cluster_path, StockCreateConfiguredNamespaces, android_set_abort_message, __register_atfork
- 实现：host9e3a与ANLb96a同时加org.jitsi.meet，native_selected+host条件都成立才发布native_abi/runtime；不是另做compat假修，预计过LIBC墙，后续WebRTC未知。
- 源码 / 产物：benchmark/2026-10-03-u15-jitsi-native-domain/README.md 中源码/产物谱系；U15 host9e3ad72e + ANLb96a8991；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U15 host9e3ad72e + ANLb96a8991；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-03-u15-jitsi-native-domain/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `ce5b51a330fa8476c977247127954e7a65b39d831793fbc12d28aee30d0c80b7`

### NATIVE-136

**公共库继承与ICU74名→72转接** · NDK/ICU

- 成员：dlns_inherit, ubrk_open_74, ubrk_open_72
- 实现：341c扩host app共享白名单；9b36 libicuuc新增NEEDED4886shim，7个74后缀tail-branch到72；不能把两个ICU数据目录强换或宣称74全API实现。
- 源码 / 产物：benchmark/2026-10-03-u14-appns-build/README.md 中源码/产物谱系；U14 host341c1260 / ICU9b36b989+4886bc5c；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U14 host341c1260 / ICU9b36b989+4886bc5c；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-03-u14-appns-build/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `ac757f85e73a306a9272fd2f95e386be09bce3f59f6fa16808ea8fb915044c60`

### NATIVE-137

**Locale UErrorCode零初始化修复** · JNI/ICU

- 成员：com.android.icu.util.LocaleNative.getDisplayCountryNative, com.android.icu.util.CaseMapperNative.toUpperCase
- 实现：AOSP ScopedIcuLocale.h未初始化UErrorCode；零初始化编译参数在指令层新增err=0。此报告未完整重建libicu_jni（closure blocked）；后续1e206531候选须另绑产物回执，不能用本报告假称库已构建/部署。
- 源码 / 产物：benchmark/2026-10-02-u12-icu-zeroinit/README.md 中源码/产物谱系；U12 ICU修法/后续候选1e206531；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：AOSP14r1 ScopedIcuLocale.h；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：U12 ICU修法/后续候选1e206531；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-u12-icu-zeroinit/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `7b9515affdf3f4988bb88332103b6cc2ab4b0204fa6842d4d0a361afb20628c2`

### NATIVE-138

**Boat v2图形共享层与三私有库** · 图形/Boat

- 成员：ANativeWindow_setBuffersGeometry, ANativeWindow_fromSurface, JNI_OnLoad
- 实现：stock18763dd4 + adapter8ab/jar633 + Unity/il2cpp/signal_box，window9历史报告可渲染互动；并不证明共享adapter/jar对128无回退，runtime adc/947不进v2。
- 源码 / 产物：$WORKSPACES/westlake-harness-bms/benchmark/2026-10-12-boat-v2-handoff/README.md 中源码/产物谱系；Boat v2 ownership(a) / U13底座；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：Boat v2 ownership(a) / U13底座；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-12-boat-v2-handoff/README.md>)：离线接班摘要转引v2配置与历史观察；不是新上板证据；SHA256 `10ef7e4413793d7bdc76372d0dd180cda68ac7ed7b6cf86f8f45da2850f46a6d`

### NATIVE-139

**r84静态Bionic mutex类型翻译** · Bionic/互斥

- 成员：pthread_mutex_lock, pthread_mutex_trylock
- 实现：Bionic初始化字0x4000/0x8000与musl低位不同；未锁定时转换recursive/errorcheck类型再委托musl，避免sentry递归锁死。
- 源码 / 产物：benchmark/2026-10-04-r84-silent-answers/README.md 中源码/产物谱系；source-build/host r84 build80；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：source-build/host r84 build80；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-04-r84-silent-answers/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `068b14d4192fed36fa98a68079321606ec22bf39d20af1db9aa6ff11d0d799e1`

### NATIVE-140

**r84 UnixFileSystem空间查询真实statvfs** · JNI/文件系统

- 成员：java.io.UnixFileSystem.getSpace0
- 实现：missing-natives用libcore statvfs注册替换返回0的openjdk stub；不再使CNN cacheSize<=0。不是U13自动包含该override。
- 源码 / 产物：benchmark/2026-10-04-r84-silent-answers/README.md 中源码/产物谱系；source-build/host r84 build80；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：source-build/host r84 build80；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-04-r84-silent-answers/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `068b14d4192fed36fa98a68079321606ec22bf39d20af1db9aa6ff11d0d799e1`

### NATIVE-141

**r86 Android buffer geometry/CPU lock** · 图形/NDK

- 成员：ANativeWindow_setBuffersGeometry, ANativeWindow_lock, ANativeWindow_unlockAndPost
- 实现：source-build shim把SDL geometry按Android语义对适配器窗口实现，报告SDLGames过首帧；与U11 CPU lock和ac59JNI Canvas是不同profile。
- 源码 / 产物：benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md 中源码/产物谱系；source-build/host r86 builds86–90；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：source-build/host r86 builds86–90；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `8fead435a562ce14e905f13943493bfae84a0795db2c8dc16e11d67c67f81aa4`

### NATIVE-142

**r86 Surface.lockCanvas后期实现** · 图形/Canvas

- 成员：android.view.Surface.nativeLockCanvas, android.view.Surface.nativeUnlockCanvasAndPost
- 实现：r86 runtime override新增软件Canvas路径；历史ac59返回0的stub仍保留独立行；本报告未独立钉此build源码/ELF SHA，源码细节unknown。
- 源码 / 产物：benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md 中源码/产物谱系；source-build/host r86 builds86–90；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：source-build/host r86 builds86–90；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；r86摘要列出此能力实现，但未逐API提供单APK A/B；validations为空是未归因，不是能力未入表。；实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `8fead435a562ce14e905f13943493bfae84a0795db2c8dc16e11d67c67f81aa4`

### NATIVE-143

**r86 Process.readProcFile补全** · JNI/进程

- 成员：android.os.Process.readProcFile
- 实现：source-build缺失natives补proc文件解析，不把r86新注册回写为U13已有；具体format flags/错误边界需补方法体。
- 源码 / 产物：benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md 中源码/产物谱系；source-build/host r86 builds86–90；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：source-build/host r86 builds86–90；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；r86摘要列出此能力实现，但未逐API提供单APK A/B；validations为空是未归因，不是能力未入表。；实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `8fead435a562ce14e905f13943493bfae84a0795db2c8dc16e11d67c67f81aa4`

### NATIVE-144

**r86 legacy Camera注册/兼容边界** · JNI/相机

- 成员：android.hardware.Camera
- 实现：source-build legacyCamera JNI按无Camera设备给合法回答；注册缺口被补，不是OH有可用Camera HAL，更不保证完整拍摄。
- 源码 / 产物：benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md 中源码/产物谱系；source-build/host r86 builds86–90；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：source-build/host r86 builds86–90；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `8fead435a562ce14e905f13943493bfae84a0795db2c8dc16e11d67c67f81aa4`

### NATIVE-145

**r86 LocalSocketImpl后期native实现** · JNI/套接字

- 成员：android.net.LocalSocketImpl
- 实现：runtime补缺native实现；注册方法/Android reserved namespace和FD ancillary语义尚未逐个核，不从加载成功推完整LocalSocket兼容。
- 源码 / 产物：benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md 中源码/产物谱系；source-build/host r86 builds86–90；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：source-build/host r86 builds86–90；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；r86摘要列出此能力实现，但未逐API提供单APK A/B；validations为空是未归因，不是能力未入表。；实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `8fead435a562ce14e905f13943493bfae84a0795db2c8dc16e11d67c67f81aa4`

### NATIVE-146

**r86 SQLite collations补全** · JNI/数据库

- 成员：android.database.sqlite.SQLiteConnection.nativeRegisterLocalizedCollators
- 实现：后期source-build补SQLite本地化排序规则，与U13真实nativeOpen以及CursorWindow Parcel stub是独立能力；collation全集/locale版本unknown。
- 源码 / 产物：benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md 中源码/产物谱系；source-build/host r86 builds86–90；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：source-build/host r86 builds86–90；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；r86摘要列出此能力实现，但未逐API提供单APK A/B；validations为空是未归因，不是能力未入表。；实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `8fead435a562ce14e905f13943493bfae84a0795db2c8dc16e11d67c67f81aa4`

### NATIVE-147

**r86 font iterator真实供给** · NDK/字体

- 成员：ASystemFontIterator_open, ASystemFontIterator_next, ASystemFontIterator_close
- 实现：报告shim补NDK字体列表，使Fennec继续；未记录此组全部字体轴/matcher覆盖或文件格式，精确源码/产物仍unknown。
- 源码 / 产物：benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md 中源码/产物谱系；source-build/host r86 builds86–90；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：source-build/host r86 builds86–90；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `8fead435a562ce14e905f13943493bfae84a0795db2c8dc16e11d67c67f81aa4`

### NATIVE-148

**r86 PerformanceHint manager接口** · NDK/性能提示

- 成员：APerformanceHint_getManager, APerformanceHint_createSession, APerformanceHint_updateTargetWorkDuration, android.os.PerformanceHintManager
- 实现：报告shim+runtime hint-manager入口；尚无真实OH调度/功耗效果证据，不把非null manager当性能收益实现。
- 源码 / 产物：benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md 中源码/产物谱系；source-build/host r86 builds86–90；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：source-build/host r86 builds86–90；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；r86摘要列出此能力实现，但未逐API提供单APK A/B；validations为空是未归因，不是能力未入表。；实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `8fead435a562ce14e905f13943493bfae84a0795db2c8dc16e11d67c67f81aa4`

### NATIVE-149

**r86枚举已创建运行VM** · JNI/VM

- 成员：JNI_GetCreatedJavaVMs
- 实现：回答正在运行的JavaVM而非另建VM，报告ElementX移动；多VM/ABI/当前VM对象生命周期边界未知。
- 源码 / 产物：benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md 中源码/产物谱系；source-build/host r86 builds86–90；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：source-build/host r86 builds86–90；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `8fead435a562ce14e905f13943493bfae84a0795db2c8dc16e11d67c67f81aa4`

### NATIVE-150

**r86目录遍历fts移植** · Bionic/fts

- 成员：fts_open, fts_read, fts_children, fts_set, fts_close
- 实现：报告补Bionic fts使Emacs native库可载入，随后仍停首Activity；载入不等于整个编辑器可用。
- 源码 / 产物：benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md 中源码/产物谱系；source-build/host r86 builds86–90；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：source-build/host r86 builds86–90；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `8fead435a562ce14e905f13943493bfae84a0795db2c8dc16e11d67c67f81aa4`

### NATIVE-151

**r86线程创建参数顺序转接** · Bionic/pthread

- 成员：pthread_create
- 实现：报告按Bionic参数/attr顺序转到OH musl，TikTok过该线程墙；未外推pthread结构/全部同步API。
- 源码 / 产物：benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md 中源码/产物谱系；source-build/host r86 builds86–90；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：source-build/host r86 builds86–90；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `8fead435a562ce14e905f13943493bfae84a0795db2c8dc16e11d67c67f81aa4`

### NATIVE-152

**r86 mozglue allocator/operator版本选择** · Bionic/版本与隔离

- 成员：dlvsym, malloc, free, _Znwm, _ZdlPv
- 实现：按libmozglue版本提供C++operator/allocator，防runtime复制件错误interposition；精确版本节点应补本profile导出map，不能用U14 LIBC map代替。
- 源码 / 产物：benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md 中源码/产物谱系；source-build/host r86 builds86–90；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：source-build/host r86 builds86–90；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-06-r86-sdl-games-and-firefox/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `8fead435a562ce14e905f13943493bfae84a0795db2c8dc16e11d67c67f81aa4`

### NATIVE-153

**r87不会递交到app的queue shim** · 输入/NDK

- 成员：AInputQueue_getEvent, AInputQueue_finishEvent, AInputEvent_getDeviceId, AKeyEvent_getKeyCode, AMotionEvent_getX
- 实现：AInputQueue/Event/Key/Motion为空queue兼容shim，runtime无NativeActivity native，fromJava省略；aaaaxy库可加载不证明NDK事件递交。
- 源码 / 产物：benchmark/2026-10-06-r87-input-gles3-and-services/README.md 中源码/产物谱系；source-build/host r87 build95；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：source-build/host r87 build95；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-06-r87-input-gles3-and-services/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `59b7a9c9fd0651c84d247023ec62c5e8392b101bbcd17f00f991a4924fc5238f`

### NATIVE-154

**r87 GLESv2 dlopen转OH GLESv3及继承** · 图形/GL

- 成员：dlopen("libGLESv2.so"), glGenVertexArrays, glGetStringi
- 实现：在.z探测前将Android libGLESv2句柄映射OH GLESv3；Android namespace继承父GL栈。aaaaxy过GL加载/绘图为历史reported，不是输入shim突然真实现。
- 源码 / 产物：benchmark/2026-10-06-r87-input-gles3-and-services/README.md 中源码/产物谱系；source-build/host r87 build95；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：source-build/host r87 build95；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-06-r87-input-gles3-and-services/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `59b7a9c9fd0651c84d247023ec62c5e8392b101bbcd17f00f991a4924fc5238f`

### NATIVE-155

**r88默认native路由防runtime interposition** · NDK/隔离

- 成员：dlopen, png_set_longjmp_fn
- 实现：129apps按gap maps将consumer库路由Android ns避开runtime PNG/HWUI复制；PPSSPP/STK移动；Chaquopy written-module双libpython风险须排除，SONAME!=文件名规则后续补。
- 源码 / 产物：benchmark/2026-10-07-r88-routing-and-time-zone/README.md 中源码/产物谱系；source-build/host r88 build96；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：source-build/host r88 build96；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-07-r88-routing-and-time-zone/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `33823ac5b24f20203546dad3ca5934a92f52244840943c36ced1ca8eeaac77b8`

### NATIVE-156

**r88 per-thread passwd/group结果** · Bionic/身份库

- 成员：getpwnam, getpwuid, getgrnam, getgrgid
- 实现：shim保留每线程结果而非musl共享line buffer；MaterialFiles交替6+6报告带shim0崩/不带1崩，样本有限，不承诺全线程安全。
- 源码 / 产物：benchmark/2026-10-07-r88-routing-and-time-zone/README.md 中源码/产物谱系；source-build/host r88 build96；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：source-build/host r88 build96；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-07-r88-routing-and-time-zone/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `33823ac5b24f20203546dad3ca5934a92f52244840943c36ced1ca8eeaac77b8`

### NATIVE-157

**r89 if_name索引getifaddrs回退** · Bionic/网络接口

- 成员：if_nametoindex, if_indextoname, getifaddrs
- 实现：OH app域ioctl被拒时shim通过getifaddrs查名/索引；不是绕过用户授权/任意ioctl放行，yaacc/openhab报告移动。
- 源码 / 产物：benchmark/2026-10-08-r89-services-and-batches/README.md 中源码/产物谱系；source-build/host r89 build99；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：source-build/host r89 build99；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-08-r89-services-and-batches/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `b5c2a8438ce481743c34ef265b2413425edaf709cb4217bb166d81f3ac4d5ef3`

### NATIVE-158

**r89 UnixNativeDispatcher setters** · JNI/文件时间

- 成员：sun.nio.fs.UnixNativeDispatcher
- 实现：报告runtime override补文件时间setter，gitling下一墙移动；该摘要未给具体native方法名/ABI/源码件SHA，保持类级成员并记缺口，不臆造futimes签名。
- 源码 / 产物：benchmark/2026-10-08-r89-services-and-batches/README.md 中源码/产物谱系；source-build/host r89 build99；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：source-build/host r89 build99；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-08-r89-services-and-batches/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `b5c2a8438ce481743c34ef265b2413425edaf709cb4217bb166d81f3ac4d5ef3`

### NATIVE-159

**r89同窗口GL与HWUI surface竞争** · 图形/窗口缺口

- 成员：eglCreateWindowSurface, android.graphics.HardwareRenderer, android.view.SurfaceView
- 实现：usp小SurfaceView共用Activity OH window，GL先抢surface时HWUI abort；HWUI先抢时GL EGL_BAD_ALLOC且内容缺失；不是两条绘图路径完整可互换。
- 源码 / 产物：benchmark/2026-10-08-r89-services-and-batches/README.md 中源码/产物谱系；source-build/host r89 build99；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：source-build/host r89 build99；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-08-r89-services-and-batches/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `b5c2a8438ce481743c34ef265b2413425edaf709cb4217bb166d81f3ac4d5ef3`

### NATIVE-160

**r86/r87宿主麦克风请求后AudioRecord过墙** · 音频/输入权限

- 成员：android.media.AudioRecord.startRecording, ohos.permission.MICROPHONE
- 实现：host重装保持uid并请求麦克风，MuseKit报告调音器绘制/监听；未外推全部AudioRecord/AAudio或自动代用户授权。
- 源码 / 产物：benchmark/2026-10-06-r87-input-gles3-and-services/README.md 中源码/产物谱系；source-build/host r87 host4/build95；未逐项钉完整源码件和ELF SHA的字段unknown
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：unknown；路由 / 代际：source-build/host r87 host4/build95；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；实现方法与APK result据该rXX摘要；尚未逐件钉rXX TU、完整产物SHA及同源重建回执；不得用U13源码件填补此缺证。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-06-r87-input-gles3-and-services/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `59b7a9c9fd0651c84d247023ec62c5e8392b101bbcd17f00f991a4924fc5238f`

### NATIVE-161

**对象未产生时的void诊断** · 媒体/NDK

- 成员：AImageReader_delete, AImage_delete
- 实现：AImage/AImageReader不产对象，delete只记录unsupported；不能冒充图像生命周期实现。
- 源码 / 产物：benchmark/2026-10-02-u12-mediandk/candidate.c + objects.c.inc，原型inputs/aosp14；build-receipt.json绑定 libmediandk 8fc0752dd561a62992268981164c5e75c87ceb802f93d6d0b958c23b54ddaa58
- Android 源码：android-14.0.0_r1 frameworks/av 402dbe885fd58af75e4c1d7e790fbf4bb22f29f9；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：AArch64 LP64：off_t=8、AMediaCodecBufferInfo=24，构建回执--target=aarch64-linux-ohos；其他ABI unknown；路由 / 代际：U12 candidate8fc0752d；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；候选provider-only行为测试不等于Subwaysurfers APK解码/播放成功；没有本轮t20或功能签认。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `b95908dd925d1103f08187b2089b0736a29c39d94936f6974eab88fbe3daef60`
- [api.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/api.json>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `1ba36522c5df5c3146a4ff55e300a1d5a3ac71a4ccd16d074623c7a81bfe051f`
- [candidate.c](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/candidate.c>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `666d51171718cb19a5922d744e2332edbbd6a45e0b578e94109b1ee8c581776b`
- [build-receipt.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/build-receipt.json>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `fe9b781dade79cd0e1de5e597ab42eb43e2ad187a571075422b885528a734739`

### NATIVE-162

**异步删除只释放转移来的fence** · 媒体/NDK

- 成员：AImage_deleteAsync
- 实现：无image可删除，但AImage_deleteAsync关闭调用方转移的fence fd；保留所有权语义，不提供图像。
- 源码 / 产物：benchmark/2026-10-02-u12-mediandk/candidate.c + objects.c.inc，原型inputs/aosp14；build-receipt.json绑定 libmediandk 8fc0752dd561a62992268981164c5e75c87ceb802f93d6d0b958c23b54ddaa58
- Android 源码：android-14.0.0_r1 frameworks/av 402dbe885fd58af75e4c1d7e790fbf4bb22f29f9；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：AArch64 LP64：off_t=8、AMediaCodecBufferInfo=24，构建回执--target=aarch64-linux-ohos；其他ABI unknown；路由 / 代际：U12 candidate8fc0752d；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；候选provider-only行为测试不等于Subwaysurfers APK解码/播放成功；没有本轮t20或功能签认。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `b95908dd925d1103f08187b2089b0736a29c39d94936f6974eab88fbe3daef60`
- [api.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/api.json>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `1ba36522c5df5c3146a4ff55e300a1d5a3ac71a4ccd16d074623c7a81bfe051f`
- [candidate.c](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/candidate.c>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `666d51171718cb19a5922d744e2332edbbd6a45e0b578e94109b1ee8c581776b`
- [build-receipt.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/build-receipt.json>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `fe9b781dade79cd0e1de5e597ab42eb43e2ad187a571075422b885528a734739`

### NATIVE-163

**Codec/track指针型unsupported** · 媒体/NDK

- 成员：AMediaCodec_createDecoderByType, AMediaCodec_getInputBuffer, AMediaCodec_getOutputBuffer, AMediaCodec_getOutputFormat, AMediaExtractor_getTrackFormat
- 实现：构造/缓冲区/format/track返回NULL；缓冲区size置0，不造decoder或数据。
- 源码 / 产物：benchmark/2026-10-02-u12-mediandk/candidate.c + objects.c.inc，原型inputs/aosp14；build-receipt.json绑定 libmediandk 8fc0752dd561a62992268981164c5e75c87ceb802f93d6d0b958c23b54ddaa58
- Android 源码：android-14.0.0_r1 frameworks/av 402dbe885fd58af75e4c1d7e790fbf4bb22f29f9；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：AArch64 LP64：off_t=8、AMediaCodecBufferInfo=24，构建回执--target=aarch64-linux-ohos；其他ABI unknown；路由 / 代际：U12 candidate8fc0752d；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；候选provider-only行为测试不等于Subwaysurfers APK解码/播放成功；没有本轮t20或功能签认。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `b95908dd925d1103f08187b2089b0736a29c39d94936f6974eab88fbe3daef60`
- [api.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/api.json>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `1ba36522c5df5c3146a4ff55e300a1d5a3ac71a4ccd16d074623c7a81bfe051f`
- [candidate.c](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/candidate.c>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `666d51171718cb19a5922d744e2332edbbd6a45e0b578e94109b1ee8c581776b`
- [build-receipt.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/build-receipt.json>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `fe9b781dade79cd0e1de5e597ab42eb43e2ad187a571075422b885528a734739`

### NATIVE-164

**无decoder/样本的负数边界** · 媒体/NDK

- 成员：AMediaCodec_dequeueInputBuffer, AMediaCodec_dequeueOutputBuffer, AMediaExtractor_getSampleTime, AMediaExtractor_getSampleTrackIndex, AMediaExtractor_readSampleData
- 实现：Codec dequeue返回合法unsupported；Extractor样本索引/时间/read返回无样本负数，非解码成功。
- 源码 / 产物：benchmark/2026-10-02-u12-mediandk/candidate.c + objects.c.inc，原型inputs/aosp14；build-receipt.json绑定 libmediandk 8fc0752dd561a62992268981164c5e75c87ceb802f93d6d0b958c23b54ddaa58
- Android 源码：android-14.0.0_r1 frameworks/av 402dbe885fd58af75e4c1d7e790fbf4bb22f29f9；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：AArch64 LP64：off_t=8、AMediaCodecBufferInfo=24，构建回执--target=aarch64-linux-ohos；其他ABI unknown；路由 / 代际：U12 candidate8fc0752d；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；候选provider-only行为测试不等于Subwaysurfers APK解码/播放成功；没有本轮t20或功能签认。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `b95908dd925d1103f08187b2089b0736a29c39d94936f6974eab88fbe3daef60`
- [api.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/api.json>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `1ba36522c5df5c3146a4ff55e300a1d5a3ac71a4ccd16d074623c7a81bfe051f`
- [candidate.c](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/candidate.c>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `666d51171718cb19a5922d744e2332edbbd6a45e0b578e94109b1ee8c581776b`
- [build-receipt.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/build-receipt.json>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `fe9b781dade79cd0e1de5e597ab42eb43e2ad187a571075422b885528a734739`

### NATIVE-165

**DataSource/Extractor/Format真实释放** · 媒体/NDK

- 成员：AMediaDataSource_delete, AMediaExtractor_delete, AMediaFormat_delete
- 实现：释放本候选拥有的callback holder、unconfigured extractor与int32 property链表；DataSource_delete不自行调用close；不接收Stagefright/AMessage外来对象。
- 源码 / 产物：benchmark/2026-10-02-u12-mediandk/candidate.c + objects.c.inc，原型inputs/aosp14；build-receipt.json绑定 libmediandk 8fc0752dd561a62992268981164c5e75c87ceb802f93d6d0b958c23b54ddaa58
- Android 源码：android-14.0.0_r1 frameworks/av 402dbe885fd58af75e4c1d7e790fbf4bb22f29f9；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：AArch64 LP64：off_t=8、AMediaCodecBufferInfo=24，构建回执--target=aarch64-linux-ohos；其他ABI unknown；路由 / 代际：U12 candidate8fc0752d；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；候选provider-only行为测试不等于Subwaysurfers APK解码/播放成功；没有本轮t20或功能签认。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `b95908dd925d1103f08187b2089b0736a29c39d94936f6974eab88fbe3daef60`
- [api.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/api.json>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `1ba36522c5df5c3146a4ff55e300a1d5a3ac71a4ccd16d074623c7a81bfe051f`
- [candidate.c](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/candidate.c>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `666d51171718cb19a5922d744e2332edbbd6a45e0b578e94109b1ee8c581776b`
- [build-receipt.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/build-receipt.json>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `fe9b781dade79cd0e1de5e597ab42eb43e2ad187a571075422b885528a734739`

### NATIVE-166

**AMediaDataSource真实callback holder分配** · 媒体/NDK

- 成员：AMediaDataSource_new
- 实现：calloc自有opaque holder；非AOSP DataSource引擎对象，不把callback读取当实际媒体读取。
- 源码 / 产物：benchmark/2026-10-02-u12-mediandk/candidate.c + objects.c.inc，原型inputs/aosp14；build-receipt.json绑定 libmediandk 8fc0752dd561a62992268981164c5e75c87ceb802f93d6d0b958c23b54ddaa58
- Android 源码：android-14.0.0_r1 frameworks/av 402dbe885fd58af75e4c1d7e790fbf4bb22f29f9；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：AArch64 LP64：off_t=8、AMediaCodecBufferInfo=24，构建回执--target=aarch64-linux-ohos；其他ABI unknown；路由 / 代际：U12 candidate8fc0752d；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；候选provider-only行为测试不等于Subwaysurfers APK解码/播放成功；没有本轮t20或功能签认。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `b95908dd925d1103f08187b2089b0736a29c39d94936f6974eab88fbe3daef60`
- [api.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/api.json>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `1ba36522c5df5c3146a4ff55e300a1d5a3ac71a4ccd16d074623c7a81bfe051f`
- [candidate.c](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/candidate.c>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `666d51171718cb19a5922d744e2332edbbd6a45e0b578e94109b1ee8c581776b`
- [build-receipt.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/build-receipt.json>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `fe9b781dade79cd0e1de5e597ab42eb43e2ad187a571075422b885528a734739`

### NATIVE-167

**AMediaDataSource保留callback/userdata** · 媒体/NDK

- 成员：AMediaDataSource_setClose, AMediaDataSource_setGetSize, AMediaDataSource_setReadAt, AMediaDataSource_setUserdata
- 实现：真实写入read_at/get_size/close/userdata供后续持有；目前无解码器调用这些callback，不是流播放支持。
- 源码 / 产物：benchmark/2026-10-02-u12-mediandk/candidate.c + objects.c.inc，原型inputs/aosp14；build-receipt.json绑定 libmediandk 8fc0752dd561a62992268981164c5e75c87ceb802f93d6d0b958c23b54ddaa58
- Android 源码：android-14.0.0_r1 frameworks/av 402dbe885fd58af75e4c1d7e790fbf4bb22f29f9；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：AArch64 LP64：off_t=8、AMediaCodecBufferInfo=24，构建回执--target=aarch64-linux-ohos；其他ABI unknown；路由 / 代际：U12 candidate8fc0752d；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；候选provider-only行为测试不等于Subwaysurfers APK解码/播放成功；没有本轮t20或功能签认。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `b95908dd925d1103f08187b2089b0736a29c39d94936f6974eab88fbe3daef60`
- [api.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/api.json>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `1ba36522c5df5c3146a4ff55e300a1d5a3ac71a4ccd16d074623c7a81bfe051f`
- [candidate.c](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/candidate.c>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `666d51171718cb19a5922d744e2332edbbd6a45e0b578e94109b1ee8c581776b`
- [build-receipt.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/build-receipt.json>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `fe9b781dade79cd0e1de5e597ab42eb43e2ad187a571075422b885528a734739`

### NATIVE-168

**未支持property/轨道读取的false边界** · 媒体/NDK

- 成员：AMediaExtractor_advance, AMediaFormat_getFloat, AMediaFormat_getInt64, AMediaFormat_getString
- 实现：未实现float/int64/string property查询返回false且不改输出，Extractor_advance也false；与int32真实属性分行。
- 源码 / 产物：benchmark/2026-10-02-u12-mediandk/candidate.c + objects.c.inc，原型inputs/aosp14；build-receipt.json绑定 libmediandk 8fc0752dd561a62992268981164c5e75c87ceb802f93d6d0b958c23b54ddaa58
- Android 源码：android-14.0.0_r1 frameworks/av 402dbe885fd58af75e4c1d7e790fbf4bb22f29f9；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：AArch64 LP64：off_t=8、AMediaCodecBufferInfo=24，构建回执--target=aarch64-linux-ohos；其他ABI unknown；路由 / 代际：U12 candidate8fc0752d；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；候选provider-only行为测试不等于Subwaysurfers APK解码/播放成功；没有本轮t20或功能签认。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `b95908dd925d1103f08187b2089b0736a29c39d94936f6974eab88fbe3daef60`
- [api.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/api.json>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `1ba36522c5df5c3146a4ff55e300a1d5a3ac71a4ccd16d074623c7a81bfe051f`
- [candidate.c](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/candidate.c>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `666d51171718cb19a5922d744e2332edbbd6a45e0b578e94109b1ee8c581776b`
- [build-receipt.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/build-receipt.json>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `fe9b781dade79cd0e1de5e597ab42eb43e2ad187a571075422b885528a734739`

### NATIVE-169

**Extractor无配置时的零track** · 媒体/NDK

- 成员：AMediaExtractor_getTrackCount
- 实现：读取自有未配置容器返回0轨道；无媒体解析、track选择与sample读取，不返回假轨道。
- 源码 / 产物：benchmark/2026-10-02-u12-mediandk/candidate.c + objects.c.inc，原型inputs/aosp14；build-receipt.json绑定 libmediandk 8fc0752dd561a62992268981164c5e75c87ceb802f93d6d0b958c23b54ddaa58
- Android 源码：android-14.0.0_r1 frameworks/av 402dbe885fd58af75e4c1d7e790fbf4bb22f29f9；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：AArch64 LP64：off_t=8、AMediaCodecBufferInfo=24，构建回执--target=aarch64-linux-ohos；其他ABI unknown；路由 / 代际：U12 candidate8fc0752d；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；候选provider-only行为测试不等于Subwaysurfers APK解码/播放成功；没有本轮t20或功能签认。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `b95908dd925d1103f08187b2089b0736a29c39d94936f6974eab88fbe3daef60`
- [api.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/api.json>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `1ba36522c5df5c3146a4ff55e300a1d5a3ac71a4ccd16d074623c7a81bfe051f`
- [candidate.c](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/candidate.c>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `666d51171718cb19a5922d744e2332edbbd6a45e0b578e94109b1ee8c581776b`
- [build-receipt.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/build-receipt.json>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `fe9b781dade79cd0e1de5e597ab42eb43e2ad187a571075422b885528a734739`

### NATIVE-170

**AMediaExtractor未配置容器真实分配** · 媒体/NDK

- 成员：AMediaExtractor_new
- 实现：分配本候选自有未配置opaque对象；setDataSource仍unsupported；不是NuMediaExtractor真移植。
- 源码 / 产物：benchmark/2026-10-02-u12-mediandk/candidate.c + objects.c.inc，原型inputs/aosp14；build-receipt.json绑定 libmediandk 8fc0752dd561a62992268981164c5e75c87ceb802f93d6d0b958c23b54ddaa58
- Android 源码：android-14.0.0_r1 frameworks/av 402dbe885fd58af75e4c1d7e790fbf4bb22f29f9；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：AArch64 LP64：off_t=8、AMediaCodecBufferInfo=24，构建回执--target=aarch64-linux-ohos；其他ABI unknown；路由 / 代际：U12 candidate8fc0752d；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；候选provider-only行为测试不等于Subwaysurfers APK解码/播放成功；没有本轮t20或功能签认。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `b95908dd925d1103f08187b2089b0736a29c39d94936f6974eab88fbe3daef60`
- [api.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/api.json>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `1ba36522c5df5c3146a4ff55e300a1d5a3ac71a4ccd16d074623c7a81bfe051f`
- [candidate.c](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/candidate.c>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `666d51171718cb19a5922d744e2332edbbd6a45e0b578e94109b1ee8c581776b`
- [build-receipt.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/build-receipt.json>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `fe9b781dade79cd0e1de5e597ab42eb43e2ad187a571075422b885528a734739`

### NATIVE-171

**AMediaFormat真实int32属性读取** · 媒体/NDK

- 成员：AMediaFormat_getInt32
- 实现：遍历本候选property链表，存在键输出int32并返回true；缺键false且输出不变，不向AMessage传对象。
- 源码 / 产物：benchmark/2026-10-02-u12-mediandk/candidate.c + objects.c.inc，原型inputs/aosp14；build-receipt.json绑定 libmediandk 8fc0752dd561a62992268981164c5e75c87ceb802f93d6d0b958c23b54ddaa58
- Android 源码：android-14.0.0_r1 frameworks/av 402dbe885fd58af75e4c1d7e790fbf4bb22f29f9；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：AArch64 LP64：off_t=8、AMediaCodecBufferInfo=24，构建回执--target=aarch64-linux-ohos；其他ABI unknown；路由 / 代际：U12 candidate8fc0752d；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；候选provider-only行为测试不等于Subwaysurfers APK解码/播放成功；没有本轮t20或功能签认。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `b95908dd925d1103f08187b2089b0736a29c39d94936f6974eab88fbe3daef60`
- [api.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/api.json>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `1ba36522c5df5c3146a4ff55e300a1d5a3ac71a4ccd16d074623c7a81bfe051f`
- [candidate.c](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/candidate.c>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `666d51171718cb19a5922d744e2332edbbd6a45e0b578e94109b1ee8c581776b`
- [build-receipt.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/build-receipt.json>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `fe9b781dade79cd0e1de5e597ab42eb43e2ad187a571075422b885528a734739`

### NATIVE-172

**AMediaFormat真实创建/int32写入** · 媒体/NDK

- 成员：AMediaFormat_new, AMediaFormat_setInt32
- 实现：AMediaFormat_new分配自有property容器；setInt32新增strdup键或更新真实int32节点，delete释放；仅int32，不声称所有format字段类型。
- 源码 / 产物：benchmark/2026-10-02-u12-mediandk/candidate.c + objects.c.inc，原型inputs/aosp14；build-receipt.json绑定 libmediandk 8fc0752dd561a62992268981164c5e75c87ceb802f93d6d0b958c23b54ddaa58
- Android 源码：android-14.0.0_r1 frameworks/av 402dbe885fd58af75e4c1d7e790fbf4bb22f29f9；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：AArch64 LP64：off_t=8、AMediaCodecBufferInfo=24，构建回执--target=aarch64-linux-ohos；其他ABI unknown；路由 / 代际：U12 candidate8fc0752d；部署证据：candidate
- 冻结：未登记；关联：无
- 待补 / 限制：Android对照机版本、APK targetSdk、OH完整实测版本未由此来源逐项钉值，保持unknown。；本行只覆盖members列出的能力；报告实现或候选静态通过不证明当前部署与整个APK可用。；候选provider-only行为测试不等于Subwaysurfers APK解码/播放成功；没有本轮t20或功能签认。

- [README.md](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/README.md>)：该route的实现/限制与历史观察摘要，不是本轮上板或完整支持证明；SHA256 `b95908dd925d1103f08187b2089b0736a29c39d94936f6974eab88fbe3daef60`
- [api.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/api.json>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `1ba36522c5df5c3146a4ff55e300a1d5a3ac71a4ccd16d074623c7a81bfe051f`
- [candidate.c](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/candidate.c>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `666d51171718cb19a5922d744e2332edbbd6a45e0b578e94109b1ee8c581776b`
- [build-receipt.json](<../../../../westlake-harness/benchmark/2026-10-02-u12-mediandk/build-receipt.json>)：50实际Unity导入的类型/行为、候选源码和准确构建回执；SHA256 `fe9b781dade79cd0e1de5e597ab42eb43e2ad187a571075422b885528a734739`

### NATIVE-173

**R6 BLASTBufferQueue.nativeUpdate：成功SurfaceView专属child尺寸与主窗口兼容尺寸分流（未冻结）** · JNI/图形窗口尺寸候选

- 成员：android.graphics.BLASTBufferQueue.nativeUpdate(JJJJI)V
- 实现：仅BBQ_nativeUpdate：oh_rs_get_child_surface_window成功返回专属child才使用requested width/height；主ViewRoot/非SurfaceView和child失败fallback main均固定panel1200x1920；SurfaceView名字本身不能判成功。无session/无producer原失败返回保留；其余三几何/lazy/STAGE0/M1/SQLite行为不动。不是BLASTBufferQueue整族或SurfaceFlinger事务完整实现。
- 源码 / 产物：source c208788a90ee19ad891af5cbe6fb8d7b29f339467ece084255d168dab45d1aef，android_graphics_compat_shim.cpp:576-610；JNI注册:795-796；runtime f28bd1b3d44e2944f77911c2ad71376869f7f3ebc6dcd8434dfea869f4056db0
- Android 源码：unknown；source-only：候选JNI注册/源码注释指向AOSP调用约定，未建立Android版本支持区间；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：OpenHarmony 6.1.0.31，仅5ea实际；b711 Boat补充可操作，db429五popup另组原证据；其他OH版本unknown；ABI：aarch64/arm64-v8a；原787 exports及SQLite/三消费者静态ABI守卫通过，不外推所有Android ABI；路由 / 代际：5ea U13/R6 bounded candidate；7bind/337身份原完整集合；c208/f28；b711与db429证据组分别绑定；部署证据：candidate
- 冻结：未登记；关联：NATIVE-041, NATIVE-042, NATIVE-043, NATIVE-044, NATIVE-159
- 待补 / 限制：能力未冻结：frozen_ids为空；源码/产物归档或实验freeze不等于API frozen登记。；原全128八窗仍pending；十控/批量启动与337 PASS不能代替全128实际完成和用户解封。；Android运行版本、API支持范围与APK targetSdk均unknown/source-only，不能借AOSP注释或NDK对照推断。；五popup为db429原组BMS图审报告，原foreground_unconfirmed不改；不能借其oldboot身份为新boot授准入。；原首Boat五触组没有证明方向/LAP；成功为b711本轮补充独立组，非追认原首组。；主ViewRoot政策相对947的1920x1200有实际变化；仅列出已测组，不外推所有popup/native方法。；nativeGetLastAcquiredFrameNum/nativeSyncNextTransaction/事务相关历史stub和r89 usp混合surface缺口旧行不升格。

- [android_graphics_compat_shim.cpp](<../../../../westlake-harness/benchmark/2026-10-13-runtime-surfaceview-split/source/android_graphics_compat_shim.cpp>)：c208完整源码；仅BBQ nativeUpdate成功child尺寸分流，三几何/lazy逐字保留；SHA256 `c208788a90ee19ad891af5cbe6fb8d7b29f339467ece084255d168dab45d1aef`
- [results.json](<../../../../westlake-harness/benchmark/2026-10-13-runtime-surfaceview-split/evidence/offline/results.json>)：原实际函数六分支host测试，不冒板上功能成功；SHA256 `562ea6e4a9213e2d3d08228f1bf3136f3595606c6b1c4aada07b24359ae44414`
- [build-provenance.json](<../../../../westlake-harness/benchmark/2026-10-13-runtime-surfaceview-split/evidence/build-provenance.json>)：原实际rc0构建/输入闭包/源码及runtime关联；SHA256 `f8c0da42da2c4993658dfd84b889b1e46626f0b452f21f7a3625c7c13342fd86`
- [artifact-archive.json](<../../../../westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r6-source-review/artifact-archive.json>)：root稳定f28产物/source recipe/archive全SHA回执；SHA256 `de5fa08be7597cddf7104ee2fc1954a338e89fcd6a416ffa4162ab96fcde6ab8`
- [liboh_android_runtime.so](<../../../../westlake-inputs/generations/boat-v2-runtime-f28bd1b3-20261013/liboh_android_runtime.so>)：完整f28 runtime字节；SHA256 `f28bd1b3d44e2944f77911c2ad71376869f7f3ebc6dcd8434dfea869f4056db0`
- [binding.json](<../../../../westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r6-fresh-admission-main/replay/binding.json>)：b711独立实际fresh337/24calls与原Reader replay，OH6.1.0.31；不授full128信用；SHA256 `5c9acf631fc7a20145dbca6738837bb8d29d0c6ef4e91c12c43793a414201de1`
- [game-visual-review.json](<../../../../westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r6-interactive-main/game-visual-review.json>)：root本轮Boat GAME_PASS：方向/加速/reset/LAP0→1；不是完整赛道通关；SHA256 `bdc7baded3a115516b7160ec2ddd2008415d5da7578d6273486d5ba440fbd705`
- [record.json](<../../../../westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r6-interactive-main/run/boat/record.json>)：本轮同PID/birth/UID与七pin/五触和真实图；原CAPTURED_PENDING_HUMAN字段保留；SHA256 `94238e7334a6c26d187863f33ffc22cd934d3522b18ddbb14da2c1346c10ea3f`
- [r6-actual-observation-results.json](<../../../../westlake-harness-bms/benchmark/2026-10-09-demo-boatattack/v2-20261013/static/r6-actual-observation-results.json>)：BMS目读原R6五popup t20全部控件保留；Boat原首组并未证明方向/LAP；SHA256 `3a5861eb3a886dc39e438b562c6d267e4a10c132cd2b8817256af2f033305914`
- [r6-actual-observation.md](<../../../../westlake-harness-bms/benchmark/2026-10-09-demo-boatattack/v2-20261013/static/r6-actual-observation.md>)：popup/Boat分组边界，原foreground_unconfirmed不改；SHA256 `e4cd30ad51001c58d68cc03a4274fbc22df1bc2c68d967c5f144eccbdb8a3acf`
- [record.json](<../../../../westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r6-experiment-main/run/popup-after/20261013T185227-a1451577/5ea34a4500000000000000001123012c/cv2-com-edward-studytracker/record.json>)：原R6 cv2-com-edward-studytracker 的db429同组record，foreground_unconfirmed不改；SHA256 `91cf77d07b7a7a816863947a28e70fe583911506efe7a227fb6c494c86115306`
- [t20.jpeg](<../../../../westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r6-experiment-main/run/popup-after/20261013T185227-a1451577/5ea34a4500000000000000001123012c/cv2-com-edward-studytracker/t20.jpeg>)：原R6 cv2-com-edward-studytracker 真实t20图；BMS已目读必需控件保留；SHA256 `8f95fba55b08b8fe39233733f75afaf4f78864122e1d932cf8cc24ceceab890f`
- [record.json](<../../../../westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r6-experiment-main/run/popup-after/20261013T185227-a1451577/5ea34a4500000000000000001123012c/cv2-com-nicue-onetwo/record.json>)：原R6 cv2-com-nicue-onetwo 的db429同组record，foreground_unconfirmed不改；SHA256 `d1158b9a2aa8c0649c04037a89d30786cbd40bb209ae54280bfbde799d04958d`
- [t20.jpeg](<../../../../westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r6-experiment-main/run/popup-after/20261013T185227-a1451577/5ea34a4500000000000000001123012c/cv2-com-nicue-onetwo/t20.jpeg>)：原R6 cv2-com-nicue-onetwo 真实t20图；BMS已目读必需控件保留；SHA256 `107a796113374ab53e244f88e077033276f1c4ba73f71e5880368ccd313e0659`
- [record.json](<../../../../westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r6-experiment-main/run/popup-after/20261013T185227-a1451577/5ea34a4500000000000000001123012c/cv2-com-trianguloy-clipboardeditor/record.json>)：原R6 cv2-com-trianguloy-clipboardeditor 的db429同组record，foreground_unconfirmed不改；SHA256 `451b8411ecdb4172ef6a5372e897743a4d3c7d610b6bfcbb0f5d620684567de5`
- [t20.jpeg](<../../../../westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r6-experiment-main/run/popup-after/20261013T185227-a1451577/5ea34a4500000000000000001123012c/cv2-com-trianguloy-clipboardeditor/t20.jpeg>)：原R6 cv2-com-trianguloy-clipboardeditor 真实t20图；BMS已目读必需控件保留；SHA256 `071d11e56a323be341d3b534a04f441f4aadf8658c8dcce4ceab38d4f0471922`
- [record.json](<../../../../westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r6-experiment-main/run/popup-after/20261013T185227-a1451577/5ea34a4500000000000000001123012c/cv2-io-github-jdanders-dropcount/record.json>)：原R6 cv2-io-github-jdanders-dropcount 的db429同组record，foreground_unconfirmed不改；SHA256 `b95ad46361c2c5221381ae054dbce7fe75930518e45a2decb22f036f0192f340`
- [t20.jpeg](<../../../../westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r6-experiment-main/run/popup-after/20261013T185227-a1451577/5ea34a4500000000000000001123012c/cv2-io-github-jdanders-dropcount/t20.jpeg>)：原R6 cv2-io-github-jdanders-dropcount 真实t20图；BMS已目读必需控件保留；SHA256 `caac5d7820b258b86a35a5a7a89e43ba3a5e725a0b925b613559e3a2c62c7357`
- [record.json](<../../../../westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r6-experiment-main/run/popup-after/20261013T185227-a1451577/5ea34a4500000000000000001123012c/fd-seal/record.json>)：原R6 fd-seal 的db429同组record，foreground_unconfirmed不改；SHA256 `b321fe0c5f364e47b0772bd0688941b45e614373c6bdd48556406817373e9d24`
- [t20.jpeg](<../../../../westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r6-experiment-main/run/popup-after/20261013T185227-a1451577/5ea34a4500000000000000001123012c/fd-seal/t20.jpeg>)：原R6 fd-seal 真实t20图；BMS已目读必需控件保留；SHA256 `8b6eb00863529211f719ae9e11896e7d978ae60e0961a2ae22f45da5f025d618`

### REG-001

**BMS 安装的 Android 包后台拉起 ability(START_ABILITIES_FROM_BACKGROUND)** · 安装与授权

- 成员：libbms.z.so: canStartAbilityFromBackground 授权路径, libapk_installer.so: 安装时授 APL_NORMAL+ACL+preAuthorizationInfo, 优先应用自身 launcher 入口
- 实现：安装器在安装时刻授后台启动权限并登记 launcher 入口;libbms 查询路径返回可启动。只覆盖 BMS 安装路线
- 源码 / 产物：branch feat/bms-route-deploy commit b5a67c62, benchmark/2026-09-30-installer-background-launcher/{base_bundle_installer.patch,build-bms.sh,build-installer.sh,HANDOFF.md}
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：arm64；路由 / 代际：feat/bms-route-deploy b5a67c62 代；部署证据：historical
- 冻结：FZ-001；关联：无
- 待补 / 限制：APK 级验证为历史 reported,本轮未重看图；oh_tested 置 unknown:冻结登记为历史签认,未在本轮逐板核 OH 小版本;版本证据在 verified_apps 的 board 字段(61b/5cd/5ea)；deployment=historical:冻结登记不等于当前部署;当前部署代需 image-provenance/runtime 指纹另证

- [frozen.json](<../../../../westlake-harness/knowledge/frozen/frozen.json>)：冻结条目 FZ-001 的 mechanism/source_record/verified_apps；SHA256 `41971d779e43c08e18c2e82c98efc9832a43959e89aaf05636d53295fbfcdb46`

### REG-002

**Android 子进程 ActivityThread 运行在显式 8MiB pthread(大栈 provider)** · 运行时基础设施

- 成员：libwestlake_android_runtime_provider.so: [CM-BIGSTACK] ActivityThread 专用 pthread, stack=8390896B
- 实现：runtime provider 为每个 Android 子进程在独立 8MiB pthread 上跑 ActivityThread(深递归/大帧防溢出);双路径部署(/system/android/lib64 与 /system/lib64/westlake/route-a/)
- 源码 / 产物：westlake-harness-bms-deploy benchmark/2026-09-30-child-stack-default/{child_main_after_stock.cpp,build-provider.sh,source-link-inputs.json}; audit benchmark/2026-09-30-native-freeze-audit (cx-t0 2b3960ee)
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：arm64；路由 / 代际：Route A / provider 0509fe235a7883b5cd9b57477221cb868465de944c6f70ed0cf2835b0fe4a97c；登记实验 2026-09-30，U 代际 unknown；部署证据：historical
- 冻结：FZ-002；关联：无
- 待补 / 限制：APK 级验证为历史 reported,本轮未重看图；oh_tested 置 unknown:冻结登记为历史签认,未在本轮逐板核 OH 小版本;版本证据在 verified_apps 的 board 字段(61b/5cd/5ea)；deployment=historical:冻结登记不等于当前部署;当前部署代需 image-provenance/runtime 指纹另证

- [frozen.json](<../../../../westlake-harness/knowledge/frozen/frozen.json>)：冻结条目 FZ-002 的 mechanism/source_record/verified_apps；SHA256 `41971d779e43c08e18c2e82c98efc9832a43959e89aaf05636d53295fbfcdb46`

### REG-003

**AssetManager.nativeOpenAssetFd 返回真实 ParcelFileDescriptor(未压缩 asset)** · 资源

- 成员：runtime native: nativeOpenAssetFd 实现(替换 Implement-me 抛错)
- 实现：对未压缩 asset 返回真实 ParcelFileDescriptor;仅此对象变更,与 532633da ReturnParcelFileDescriptor 同源
- 源码 / 产物：westlake-harness-bms-deploy 8560fd68 benchmark/2026-09-30-asset-fd-runtime (copied from Westlake 532633da ReturnParcelFileDescriptor; only this object changed in liboh_android_runtime.so 9e14bf20 -> 53f00423)
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：arm64；路由 / 代际：unknown；部署证据：historical
- 冻结：FZ-003；关联：无
- 待补 / 限制：APK 级验证为历史 reported,本轮未重看图；oh_tested 置 unknown:冻结登记为历史签认,未在本轮逐板核 OH 小版本;版本证据在 verified_apps 的 board 字段(61b/5cd/5ea)；deployment=historical:冻结登记不等于当前部署;当前部署代需 image-provenance/runtime 指纹另证

- [frozen.json](<../../../../westlake-harness/knowledge/frozen/frozen.json>)：冻结条目 FZ-003 的 mechanism/source_record/verified_apps；SHA256 `41971d779e43c08e18c2e82c98efc9832a43959e89aaf05636d53295fbfcdb46`

### REG-004

**sun.security.jca.Providers.jarVerificationProviders[0] conscrypt→BouncyCastle 重写** · 安全/加密

- 成员：oh-adapter-runtime.jar: sun.security.jca.Providers JAR 层重写
- 实现：JAR 层把 jarVerificationProviders[0] 从 conscrypt 重写为 BouncyCastle,getSunProvider 路径恢复;随 J1-final/J2/J3 代际携带
- 源码 / 产物：feat/bms-walls commit cdb82fe5 (split out of B7BindFixes; carried unchanged through J1-final faf0782b, J2 0715c964, J3 75c2068c). build-result-{j1final,j2,j3}.json show the split as an added class; changed_existing stayed the 2 injection targets.; audited post-split on J3; full logs/SHAs and earlier failure excerpts in benchmark/2026-09-30-freeze-audit-u4/audit.json. Source root is westlake-harness-walls; default master path currently absent.
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：arm64；路由 / 代际：J1-final faf0782b / J2 0715c964 / J3 75c2068c (jar 链)；部署证据：historical
- 冻结：FZ-004；关联：无
- 待补 / 限制：APK 级验证为历史 reported,本轮未重看图；oh_tested 置 unknown:冻结登记为历史签认,未在本轮逐板核 OH 小版本;版本证据在 verified_apps 的 board 字段(61b/5cd/5ea)；deployment=historical:冻结登记不等于当前部署;当前部署代需 image-provenance/runtime 指纹另证

- [frozen.json](<../../../../westlake-harness/knowledge/frozen/frozen.json>)：冻结条目 FZ-004 的 mechanism/source_record/verified_apps；SHA256 `41971d779e43c08e18c2e82c98efc9832a43959e89aaf05636d53295fbfcdb46`

### REG-005

**dex2oat-once 工具链: host dex2oat64(r1 树+22 补丁)离线重生成 27 件 boot image** · ART 工具链

- 成员：dex2oat64(host, r1+22-patch, suspend-check 显式/implicit_suspend_checks_=false), t5_gen_image.sh, boot.oat(T5c/T6c/T7c 产物)
- 实现：自有工具链离线重生成 27 件 boot image;板上 R155 libart 接受 image-only(T6c)与 image+jar 包(T7c)无 CheckSystemClass abort;常驻 libart 不变
- 源码 / 产物：branch master; recipe knowledge/toolchains/art-r155/{patches (22), series, BUILD.md, recipe/}; build env BUILD.md §T3c (ART_USE_READ_BARRIER=false, ART_DEFAULT_GC_TYPE=CMS, ART_USE_GENERATIONAL_CC=false, ART_HEAP_POISONING=false, ART_TEST_DEBUG_GC=false, ALLOW_MISSING_DEPENDENCIES=true; m -j32 dex2oat); reproducible per scripts/lab/reproduce_dex2oat_toolchain.sh (dex2oat64 byte-for-byte ae865ddd, image vdex 9/9 == T5c, only boot.art/boot.oat differ by embedded cmdline path string). Board R155 device libart 59e1bb45 is a GATE REFERENCE only (not deployed by this toolchain).
- Android 源码：AOSP android-14.0.0_r1；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：arm64；路由 / 代际：master(art-r155 T3c/T5c/T6c/T7c)；部署证据：historical
- 冻结：FZ-005；关联：无
- 待补 / 限制：APK 级验证为历史 reported,本轮未重看图；oh_tested 置 unknown:冻结登记为历史签认,未在本轮逐板核 OH 小版本;版本证据在 verified_apps 的 board 字段(61b/5cd/5ea)；deployment=historical:冻结登记不等于当前部署;当前部署代需 image-provenance/runtime 指纹另证

- [frozen.json](<../../../../westlake-harness/knowledge/frozen/frozen.json>)：冻结条目 FZ-005 的 mechanism/source_record/verified_apps；SHA256 `41971d779e43c08e18c2e82c98efc9832a43959e89aaf05636d53295fbfcdb46`

### REG-006

**android.os.VibratorManager.getVibratorIds() → int[0](route-A stub)** · 系统服务

- 成员：adapter.activity.VibratorFetcher.install(): SYSTEM_SERVICE_FETCHERS[vibrator_manager] 替换, allocateInstance(SystemVibratorManager)(跳过会 NPE 的构造器), IVibratorManagerService.getVibratorIds() stub 返回 int[0]
- 实现：adapter 替换 vibrator_manager fetcher,无服务端实现按空设备集返回;mLock 保护(J7)。语义=无振动器设备而非真实振动 API
- 源码 / 产物：J7 a6a2537f9 (mLock added) on top of the J04 vibrator_manager split; U6 unified state ACK(95) 2026-10-01 04:36. | carried in oh-adapter-runtime.jar J7b 381110a6 (the jar also carries other fixes, so the freeze is on the source blob, like FZ-004).
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：arm64；路由 / 代际：J7 a6a2537f9 / J7b jar 381110a6 / U6 统一态；部署证据：historical
- 冻结：FZ-006；关联：无
- 待补 / 限制：APK 级验证为历史 reported,本轮未重看图；oh_tested 置 unknown:冻结登记为历史签认,未在本轮逐板核 OH 小版本;版本证据在 verified_apps 的 board 字段(61b/5cd/5ea)；deployment=historical:冻结登记不等于当前部署;当前部署代需 image-provenance/runtime 指纹另证

- [frozen.json](<../../../../westlake-harness/knowledge/frozen/frozen.json>)：冻结条目 FZ-006 的 mechanism/source_record/verified_apps；SHA256 `41971d779e43c08e18c2e82c98efc9832a43959e89aaf05636d53295fbfcdb46`

### REG-007

**完整 AOSP android-14.0.0_r1 external/tagsoup 进 BCP adapter-mainline-stubs jar** · XML/解析

- 成员：org.ccil.cowan.tagsoup.Parser(extends DefaultHandler implements ScanHandler/XMLReader), 15 个源文件整族
- 实现：BCP 顺序(stubs 在 framework 前)使 stubs-jar 内完整 tagsoup 成为生效类,解除 IncompatibleClassChangeError;源=AOSP r1 外部 tagsoup
- 源码 / 产物：AOSP android-14.0.0_r1 external/tagsoup src/**/*.java (15 files; Parser.java sha aa68cc4d04869aee...; byte-identical on hw248 aosp-14.0.0_r1-art and a2hlab android-source/external-tagsoup). Compiled into adapter-mainline-stubs.jar via dockbuild (a2hlab-b5-java:24.04, 4 compile-only jars) -> T7d jar d8b2406e. The other 6 android stub additions are unchanged from the T7c base. | carried in adapter-mainline-stubs.jar T7d d8b2406e (hw248 $HW248_ROOT/cc-wiki-t7d-stubs.jar); frozen on the source blobs because the stubs jar carries other stubs (outer 2026-10-01, same rule as FZ-006).
- Android 源码：AOSP android-14.0.0_r1；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：arm64；路由 / 代际：BCP adapter-mainline-stubs.jar T7d d8b2406e / AOSP android-14.0.0_r1；部署证据：historical
- 冻结：FZ-007；关联：JAVA-001
- 待补 / 限制：APK 级验证为历史 reported,本轮未重看图；oh_tested 置 unknown:冻结登记为历史签认,未在本轮逐板核 OH 小版本;版本证据在 verified_apps 的 board 字段(61b/5cd/5ea)；deployment=historical:冻结登记不等于当前部署;当前部署代需 image-provenance/runtime 指纹另证

- [frozen.json](<../../../../westlake-harness/knowledge/frozen/frozen.json>)：冻结条目 FZ-007 的 mechanism/source_record/verified_apps；SHA256 `41971d779e43c08e18c2e82c98efc9832a43959e89aaf05636d53295fbfcdb46`

### REG-008

**android.net.ssl.SSLSockets stub 进 BCP adapter-mainline-stubs jar** · 网络/TLS

- 成员：android.net.ssl.SSLSockets: isSupportedSocket(SSLSocket)->false, setUseSessionTickets/setHostname 等静态方法 no-op
- 实现：新建类(BCP 无他处定义→G3 安全不遮蔽);类可解析使 OkHttp AndroidPlatform.buildIfSupported 走 fallback 而非 Dispatcher 崩溃
- 源码 / 产物：benchmark/2026-10-01-image-predeploy-gate/t7d-stub-spec/sources/android/net/ssl/SSLSockets.java (new class, not in any other BCP jar -> G3-safe). Compiled into adapter-mainline-stubs.jar via dockbuild -> T7d jar d8b2406e. | carried in adapter-mainline-stubs.jar T7d d8b2406e (hw248 $HW248_ROOT/cc-wiki-t7d-stubs.jar); frozen on the source blobs because the stubs jar carries other stubs (outer 2026-10-01, same rule as FZ-006).
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：arm64；路由 / 代际：BCP adapter-mainline-stubs.jar T7d d8b2406e；部署证据：historical
- 冻结：FZ-008；关联：无
- 待补 / 限制：APK 级验证为历史 reported,本轮未重看图；oh_tested 置 unknown:冻结登记为历史签认,未在本轮逐板核 OH 小版本;版本证据在 verified_apps 的 board 字段(61b/5cd/5ea)；deployment=historical:冻结登记不等于当前部署;当前部署代需 image-provenance/runtime 指纹另证

- [frozen.json](<../../../../westlake-harness/knowledge/frozen/frozen.json>)：冻结条目 FZ-008 的 mechanism/source_record/verified_apps；SHA256 `41971d779e43c08e18c2e82c98efc9832a43959e89aaf05636d53295fbfcdb46`

### REG-101

**板上 libart 代际判定(oat230/image108, R155 无布局差)** · ART 工具链

- 成员：libart.so ComputeAndSetHashCode 反汇编指纹, oat.h kOatVersion=230, image.cc kImageVersion=108
- 实现：板上 libart(59e1bb45)与官方 aosp-14.0.0_r16 产物逐指令同形(count@8/tbnz bit0/hash@12/data@16)+源码级 230/108 常量;R155 风险排除
- 源码 / 产物：master knowledge/toolchains/dex2oat-a14.md(官方 r16 复现节)
- Android 源码：AOSP android-14.0.0_r16(对照) 与 android-14.0.0_r1(源)；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：arm64；路由 / 代际：unknown；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：板上 libart 精确源 commit 未知(d600 树未取得)

- [dex2oat-a14.md](<../../../../westlake-harness/knowledge/toolchains/dex2oat-a14.md>)：R155 对照+版本判定的全过程；SHA256 `afd946b461a9ad9933e14daff1998cce66b6aa15258fe815d979c95673c82bcd`
- [boot-image-inputs.sha256](<../../../../westlake-harness/knowledge/toolchains/boot-image-inputs.sha256>)：板上 27 件 image 权威 SHA；SHA256 `801a003cde5ffe293bf965e51c3428186782ff1b83cf0a7d765d30cf377ec202`

### REG-102

**官方 r16 dex2oat 9-jar 复现(7s 工具链 vs c-route 570s 挂起)** · ART 工具链

- 成员：官方树 host dex2oat64(sha16 1a2f5a22), 9 jar 输入(payload v3a-r8b)
- 实现：官方 aosp-14.0.0_r16 树构建,板上 boot.oat 内 cmdline 逐字复刻;7.086s 出 27 文件(vdex 9/9 逐位同,art/oat 因 cmdline 路径串+53KB 残差)
- 源码 / 产物：master knowledge/toolchains/dex2oat-a14.md;aosp-14.0.0_r16-pinned-manifest.xml
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：arm64；路由 / 代际：unknown；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：art/oat 18 件未逐字节复现(checksum+53KB 残差,归因 d600 构建侧差异)；d600 树源未取得

- [dex2oat-a14.md](<../../../../westlake-harness/knowledge/toolchains/dex2oat-a14.md>)：复现命令/L1 9/27/L2 头字段判定；SHA256 `afd946b461a9ad9933e14daff1998cce66b6aa15258fe815d979c95673c82bcd`

### REG-103

**arm64 asm 常量对齐(asm_defines 上游生成器重生成)** · ART 工具链

- 成员：stubs108/asm_defines.h(188 defines), quick/jni_entrypoints_arm64.o, thread_arm64.o
- 实现：A15 手写 asm_defines.h(THREAD_CARD_TABLE_OFFSET 0x90)毒化 asm 对象;用 108 树自带 cpp-define-generator 重生成真值(0x98/0xa0/0xe0/0x24)并强制重汇三件,修掉 thread_arm64 Check failed
- 源码 / 产物：t4 树 c-route 工作(hw248);记录于 master knowledge/toolchains/dex2oat-a14.md
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：arm64；路由 / 代际：unknown；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：产物未持久到 master 树(hw248 $HW248_ROOT)

- [dex2oat-a14.md](<../../../../westlake-harness/knowledge/toolchains/dex2oat-a14.md>)：r12 重生成记录；SHA256 `afd946b461a9ad9933e14daff1998cce66b6aa15258fe815d979c95673c82bcd`

### REG-104

**CheckSystemClass 豁免(A15 patch 语义移植)** · ART 工具链

- 成员：runtime/class_linker.cc: CheckSystemClass FATAL→WARNING
- 实现：A15 host 线从来是放行(非通过)String mismatch;把该豁免打到 108 原生基上,r16 host 链 InitWithoutImage 通过;板上 libart 无豁免(纯 r16 镜像必 abort,已由 5cd L2 失败实证)
- 源码 / 产物：t4 树 bms commit 1c9c640a(r16 waiver 版)
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：arm64；路由 / 代际：unknown；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：豁免仅存在于 host 工具链,板上 libart 未打(设计如此)

- [dex2oat-a14.md](<../../../../westlake-harness/knowledge/toolchains/dex2oat-a14.md>)：cppcrash-9465 取证；SHA256 `afd946b461a9ad9933e14daff1998cce66b6aa15258fe815d979c95673c82bcd`

### REG-105

**部署标签配方(12 规则, inode 标签非策略)** · SELinux/标签

- 成员：appspawn-x→appspawn_exec, /system/android/lib64+route-a+boot*.{art,oat,vdex}+*.so→system_lib_file, *.jar→system_file, *.json→system_etc_file, fonts.xml→system_fonts_file, /system/lib64/seccomp→原厂(窄例外已删)
- 实现：cx-bms 单一配方;seccomp-stock 规则因证伪删除(61b/5ea 原厂即 system_lib_file);每条经 sepolicy 门 sesearch 证明
- 源码 / 产物：master knowledge/gates/selinux-label-recipe.json
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：arm64；路由 / 代际：unknown；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：app-private(/data/app)域归属未证(安装域关注,范围外)

- [selinux-label-recipe.json](<../../../../westlake-harness/knowledge/gates/selinux-label-recipe.json>)：12 规则全集；SHA256 `7835707990d4fa2019fdf2665fd89a9a86e86a6d673bb105dd793fd2189a0f83`
- [sepolicy-evidence.json](<../../../../westlake-harness/knowledge/gates/sepolicy-evidence.json>)：35 条 allow 证明；SHA256 `55f488a4e48d0121405c65dace42e5671ab406653d483a904848b42458c72b01`

### REG-106

**离线 sepolicy 门(sesearch 证明+fail-closed)** · SELinux/标签

- 成员：scripts/lab/sepolicy_gate.py, QUERIES 映射(rule id→class+perms), policy SHA 7d23015f 钉死
- 实现：读 cx-bms 配方原位(rules[]+match/context),a2hlab VM setools 4.4.4 sesearch;漂移/缺失/工具不可达均 fail-closed;拒复用过期 evidence
- 源码 / 产物：$WORKSPACES/westlake-harness-t4/scripts/lab/sepolicy_gate.py(commit 7bdecae0f4 链)
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：arm64；路由 / 代际：unknown；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：live 板上策略 vs 拉取件一致性依赖 SHA 钉(未每板重拉)

- [sepolicy-evidence.json](<../../../../westlake-harness/knowledge/gates/sepolicy-evidence.json>)：门输出快照；SHA256 `55f488a4e48d0121405c65dace42e5671ab406653d483a904848b42458c72b01`

### REG-107

**U13 recover-v3 冷启动恢复链(post-fs-data→ready 参数→boat overlay)** · 冷启动/自启

- 成员：init cfg: post-fs-data start westlake-u13-recover, param:westlake-u13-boat-overlay-start condition sys.westlake.demo.u13.ready=true, westlake-u13-recover-v3.sh: 56 mounts 重放+labels+READY
- 实现：post-fs-data 期(先于 foundation/AMS)重放 56 基线 mount 不 umount(stat 连续防 init INVALID 闩锁);设 ready 参数触发 boat overlay;幂等(同 boot 已 READY 即退出);v3 增默认 OFF 的 permissive opt-in
- 源码 / 产物：master benchmark/2026-10-10-u13-autostart/payload/{init/00_westlake_u13_recover-v3.cfg,scripts/westlake-u13-recover-v3.sh}
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：arm64；路由 / 代际：unknown；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：v2/v3 双 cfg 并存,staged 目录需按 RECOVER_VARIANT 选择；permissive 14s 窗依赖 receipt-ready barrier

- [00_westlake_u13_recover-v3.cfg](<../../../../westlake-harness/benchmark/2026-10-10-u13-autostart/payload/init/00_westlake_u13_recover-v3.cfg>)：触发链与 bootstage 语义；SHA256 `7a954d8918b767f1ec54311a359172d9f83d1b1e5fc3881d29a82a792a2a91f1`

### REG-108

**封存 driver receipt-ready barrier(竞态修复)** · 冷启动/自启

- 成员：demo_seal_61b.py wait_receipt_ready(name) — polls ROOT/receipt.env until state=READY and boot_id==current boot (L477-479, after wait_boot, before post-enforcing), demo_seal_61b.py wait_boot(name, previous) — bounded poll: /proc/sys/kernel/random/boot_id differs + bootevent.boot.completed=true (L240-258), affected checks moved behind the barrier: post-enforcing getenforce / post-receipt-selinux / post-dmesg invalid count / ready-socket stat 0660 (L483-498)
- 实现：oc-t4 只读审计定位:wait_boot 以 boot.completed 为准而 recover 收尾晚 14s;setenforce/dmesg/socket 检查曾撞窗口;cc-wiki 落 barrier 轮询 receipt.env state=READY+boot_id 匹配
- 源码 / 产物：$WORKSPACES/westlake-harness-wiki/scripts/lab/demo_seal_61b.py L477-479(注释引 oc-t4 审表)
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：arm64；路由 / 代际：unknown；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：新版 driver 尚未在真实封存跑过一次(barrier 未实测)

- [demo_seal_61b.py](<../../../../westlake-harness-wiki/scripts/lab/demo_seal_61b.py>)：receipt-ready barrier implementation + the four checks now behind it (race fix credited to oc-t4 audit)；SHA256 `a7add5519e9f3cf932c620a7e8e71246cb350caa3c7681f42f41c04017e9b446`

### REG-109

**BoatAttack 三私有件(C7/C4/signal-box)与 9 共享路径部署判定** · BoatAttack 私有件

- 成员：C7 libunity.so(关 Swappy+电话监听+resolver→eglGetProcAddress), C4 libil2cpp.so(改名+pthread-edge), signal-box(westlake_bionic_signal_box: bionic/musl 信号垫片)
- 实现：12 件输入(3 私有+9 共享候选)全部对钉值逐字节核验(0 缺 0 漂移);9 共享路径里 pthread_bridge 两代字节同(db31d6d8),libandroid 差 49B=CLASSNAME_FIX 非 ABI;路线①=统一态+私有件不碰共享路径
- 源码 / 产物：00.Workspace-games-ad1ab0a7(games/boatattack-repro 43ec24af9)src/tools/devices/boat-attack-apk-lightup.sh L22-55
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：arm64；路由 / 代际：unknown；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：可玩判据(1920×1200/HUD/KPH)待上板；49B CLASSNAME_FIX 移植决策未落

- [README.md](<../evidence/old-boat-readme.md>)：9 共享路径对照+路线判定；SHA256 `6467f9fcc09155e9a581308d436cb16ea9ed0d6d696b7329c72f394f760f22df`

### REG-110

**NDK libandroid 缺口(ANativeWindow 簇等 16 符号)** · NDK/原生

- 成员：MISSING in OH 6.1 sysroot (16): AConfiguration_new/_delete/_fromAssetManager/_getDensity/_getCountry (5); ASensorManager_getInstance/_getSensorList/_getDefaultSensor/_forget / ASensorEventQueue_getEvents/_disable/_enable/_setEventRate / ASensor_getName/_getVendor/_getHandle (11), BRIDGED (android_graphics_compat_shim.cpp, 00.Workspace 72a2f0a52): ANativeWindow_fromSurface / _acquire / _release / _getWidth / _getHeight -> OH_NativeWindow_*
- 实现：OH 6.1 sysroot 符号核算:16 缺失;ANativeWindow 簇经 android_graphics_compat_shim.cpp 桥到 OH_NativeWindow_*(00.Workspace 72a2f0a52);传感器/配置簇未实现
- 源码 / 产物：$WORKSPACES/00.Workspace/src/adapter/framework/android-runtime/src/android_graphics_compat_shim.cpp
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：arm64；路由 / 代际：unknown；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：16 缺失符号中仅 ANativeWindow 簇有桥;ASensor/AConfiguration 无实现；桥接层未入主仓

- [android_graphics_compat_shim.cpp](<../../../../00.Workspace/src/adapter/framework/android-runtime/src/android_graphics_compat_shim.cpp>)：ANativeWindow cluster bridged onto OH_NativeWindow_* exports (shim source)；SHA256 `7e4b38a0dbf3191245ef85df52e49e627895e2982f6acc72193bf066667e8cac`

### REG-111

**可重编产物清单(adapter846/Boat8ab/U13 runtime187 等)** · 可重编产物

- 成员：rebuildable-artifacts.json scope 全集
- 实现：按两次干净构建+receipt 审计判定可重编/锁定;adapter846/Boat8ab/U13 runtime187 初批;无行证据或无双干净构建=locked
- 源码 / 产物：master knowledge/gates/rebuildable-artifacts.json
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：arm64；路由 / 代际：unknown；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：清单为诊断性,不修改部署/准入/冻结；U13 其余成员待审计 receipt

- [rebuildable-artifacts.json](<../../../../westlake-harness/knowledge/gates/rebuildable-artifacts.json>)：清单 scope 与 policy；SHA256 `2da82ec24fadf28c5fa87156a7a2acea2fa65954024d3c8c0fcf0bbd395f5275`

### REG-112

**新 native 准入与 BCP 替换例外** · 镜像治理

- 成员：libmediandk.so 准入(8fc07525), U15-FRAMEWORK-BITMAP-001(framework jar 位图替换,approved)
- 实现：新 native 库走 new-native-admissions(SHA 钉);BCP jar 只许 adapter-mainline-stubs 例外+显式登记(U15 framework 位图经外环批)
- 源码 / 产物：master knowledge/gates/{new-native-admissions.json,bcp-swap-exceptions.json}
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：arm64；路由 / 代际：unknown；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：例外清单封闭集合,新例外需走同流程

- [new-native-admissions.json](<../../../../westlake-harness/knowledge/gates/new-native-admissions.json>)：libmediandk 准入；SHA256 `585202ed6798073ab6557aa8499e2e4d5c74f7d2b45581d54308f31439ff5fba`
- [bcp-swap-exceptions.json](<../../../../westlake-harness/knowledge/gates/bcp-swap-exceptions.json>)：U15 例外；SHA256 `45266e367eab748385486b174bafa52b7dd4a4fa3044dd55122a86b5f0a65f6e`

### REG-113

**验证辅助清单(flaky/benign/未落地 ack)** · 验证可靠性

- 成员：flaky-keys, benign-log-signatures(112KB 签名库), unlanded-ack(SHA 锚定)
- 实现：flaky key 单列防误判回归;fatal 判定先滤 benign 签名;未落地 lane 以 listing SHA 锚定 ack,改动即失效
- 源码 / 产物：master knowledge/gates/{flaky-keys.json,benign-log-signatures.json,unlanded-ack.json}
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：arm64；路由 / 代际：unknown；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：benign 库只覆盖已见签名,新噪声需增量

- [flaky-keys.json](<../../../../westlake-harness/knowledge/gates/flaky-keys.json>)：flaky 机制；SHA256 `1333549039c413f9f23b5557afd983ca9e9d748ee69bd31f29d367ba37c80aa9`
- [benign-log-signatures.json](<../../../../westlake-harness/knowledge/gates/benign-log-signatures.json>)：签名库；SHA256 `550c368a6e3b13259381380a6abff51a009298997e15d8d1a0f4eef4b6221a91`
- [unlanded-ack.json](<../../../../westlake-harness/knowledge/gates/unlanded-ack.json>)：ack 机制；SHA256 `52ad369b277b0b79c23f8fe1faa9d096e2344246f57edba8e5d110498bd5a3fa`

### REG-114

**镜像来源例外与统一态归属判定** · 部署代际

- 成员：image-provenance-exceptions.json(27KB)
- 实现：按 boot-image-inputs SHA 与 runtime 指纹判定当前部署代归属;例外显式登记防误归
- 源码 / 产物：master knowledge/gates/image-provenance-exceptions.json
- Android 源码：unknown；API level：unknown；APK targetSdk：unknown；Android 实测：unknown
- OH 实测：unknown；ABI：arm64；路由 / 代际：unknown；部署证据：historical
- 冻结：未登记；关联：无
- 待补 / 限制：三板代际混杂历史(U13/U15/boat 候选),例外表需随封存收敛

- [image-provenance-exceptions.json](<../../../../westlake-harness/knowledge/gates/image-provenance-exceptions.json>)：例外机制；SHA256 `0b27c3faee1bd7583e96e48e3509156c29d0afec80daa581a6075b02597d0ce3`

## 下一步最该补的知识

| 优先项 | 需要补什么 | 为什么 |
|---|---|---|
| 现态映射 | 每条 API 对应的当前部署 SHA、Route A/B、namespace、JNI 最终绑定者 | 历史修好不等于当前进程正在使用该实现 |
| 版本矩阵 | 实测运行的 OH 完整版本/Release/ABI、APK SHA/版本/targetSdk；Android 源码和对照机另列 | 当前材料不足以声明跨 Android/OH 版本通用支持 |
| 功能深度 | 图形、音频、媒体、输入、WebView 等按具体操作留证，而非只看首屏 | API 过墙、界面出现、功能有效是三个不同结论 |
| 冻结候选 | 将多 APK 过墙与至少一张 t20 亮图关联到同一实现版本，再按既有规则复核 | 只有 8 条冻结登记，其他实现不能自动视为冻结 |
| 复现来源 | 源码快照、补丁、工具链 SHA、原始 rc=0 构建日志与产物 SHA 成套绑定 | 报告里写了修复，仍可能缺少可重建的完整链条 |
| 覆盖空白 | 从 benchmark-source-index.json 的未直接引用包继续检查，与新首个致命点簇关联 | 本表是知识地图，不能把未记录能力当成已经支持或永远不需要 |

新增修复应更新对应分片并运行 `python3 benchmark/2026-10-12-api-progress/atlas.py build` 和校验。修墙优先级仍按最近统一态运行的首个致命点挡住的 key 数排序，历史静态缺口数只是上界。
