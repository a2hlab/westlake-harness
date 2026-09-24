# 100 APK 静态复核与通用缺口优先级（2026-09-24，v2 / 黑板 #5）

交付分支 `analysis/static-100`；基线 harness `e3100e1`，Westlake 源码 `22b945321929987c86b35cd99f9f2d2f4283e82e`。负责：内环(codex)，黑板 #2 分析改派及 #5 修订。**R2：partially-verified（静态全量验证；启动结果未验证）**。没有连接或写入板子，没有 push，也没有修改主树或本分支的 harness 实现。

100 个输入均完成 scan → oh-resolve → gap-map，并按输入哈希、包名、版本、runtime lock 与输出哈希逐个核对。最终 ABI 为 **92 个 target-abi-available，8 个 no-packaged-native-libraries**。按 #5 恢复主对照头条：保留原 APK，排除 ARM32 `libcvt.so` 的 AArch64 provider 资格，不再排除 app；移出同源 K-9/Thunderbird 对中的 `fd-k9`，保留微博与 Thunderbird，总数仍为 100。

**最值得先验证的共性问题是 PackageManager、UserManager、JobScheduler、Notification 和 native 装载/入口契约。当前没有任何 app 的首阻塞或启动阶段跃迁观测，不能把静态引用数量称为“已阻塞 app 数”。** 前 N 项的条件化预估见后文：可计算覆盖与剩余静态约束，不能据此许诺点亮数量。

## v2 相对已采认 v1 的差异

基线为外环已采认的 `1cd16b3`；本次追加提交，不改写该提交。恢复 `toutiao`、移出 `fd-k9`，保留微博。pipeline 的指纹失效和 aggregator 的 corpus 过滤已作为正式工具提交，源码位于根目录 `tools/`。

| 指标 | v1 | v2 | 差值 |
|---|---:|---:|---:|
| app | 100 | 100 | +0 |
| 开放分组 | 170 | 170 | +0 |
| 含硬 verdict 的分组 | 101 | 101 | +0 |
| 缺失 Java 签名/类型候选 | 897 | 899 | +2 |

以下每格依次为 **覆盖 / 静态硬行清零 / 乐观启动候选**，模型和权重不变；是语料变化及全量重算差异，不是观测到的启动收益。

| 前 N 项 | v1 | v2 |
|---:|---|---|
| 1 | 79 / 0 / 0 | 79 / 0 / 0 |
| 2 | 98 / 0 / 0 | 98 / 0 / 0 |
| 3 | 98 / 0 / 0 | 98 / 0 / 0 |
| 4 | 98 / 0 / 0 | 98 / 0 / 0 |
| 5 | 100 / 0 / 1 | 100 / 0 / 1 |
| 6 | 100 / 0 / 1 | 100 / 0 / 1 |
| 7 | 100 / 1 / 2 | 100 / 1 / 2 |
| 8 | 100 / 1 / 26 | 100 / 1 / 26 |
| 9 | 100 / 1 / 100 | 100 / 1 / 100 |
| 10 | 100 / 1 / 100 | 100 / 1 / 100 |

最终明确忽略的 corpus 外 maps：`fd-k9`。所有 app 清单、统计差分和前 N 表保存于 [revision-diff.json](revision-diff.json)。


## 1. 语料与技术栈复核

原语料的 36 个 `commercial`/`commercial (CN)` 标签是来源，不是技术栈；其余标签混合了语言、业务与引擎。本次统一为互斥的**打包实现层**，并保留 `original_stack`、独立 source、ABI 状态、完整 SHA-256、DEX 类定义与 ELF 证据。`android-jvm` 表示 Android Java/Kotlin framework 为基础的类别，**不表示没有 native 库**；纯 JVM 资格由 `no-packaged-native-libraries` 单独判断。

| 技术栈层 | app | arm64 / 无打包 native | 示例 |
|---|---|---|---|
| android-jvm | 68 | 60 / 8 | mcdonalds, wikipedia, termux, ooniprobe, anki, antennapod, newpipe, aegis, markor, opencamera, fd-tusky, fd-cl |
| flutter | 8 | 8 / 0 | co-weibo, localsend, fd-fluffychat, fd-libre, fd-saber, fd-immich, fd-kitchenowl, co-mm |
| native-engine | 8 | 8 / 0 | vlc, ppsspp, fd-organicmaps, fd-stk, fd-minetest, fd-mpv, co-client, co-candycrushsaga |
| react-native | 7 | 7 / 0 | burgerking, fd-meet, fd-im-vector-app, co-barcelona, co-teams, co-shopping, co-discord |
| libgdx/arc | 3 | 3 / 0 | mindustry, fd-app, fd-shatteredpixeldungeon |
| unity-il2cpp | 2 | 2 / 0 | subwaysurfers, co-duolingo |
| gecko | 2 | 2 / 0 | firefox, fd-fennec_fdroid |
| webview-hybrid | 2 | 2 / 0 | fd-tutanota, fd-mobile |

分类规则可在 [审计脚本快照](evidence/audit_static100.py.txt) 复算：优先识别 `libflutter.so`、`libreactnative.so`/React 合并库加 DEX 定义、`libunity.so`、`libxul.so`、libGDX/Arc；WebView hybrid 结合原标签与包内 JS 资源（Tutanota `assets/tutanota/app-env/*.js`、Jellyfin `assets/native/nativeshell.js`）保留；明确 native 主引擎按专用库划分；其余归 Android JVM。Compose/Kotlin 仅作辅助标签（58/100 含 Compose 类定义，不能推断全部首屏使用 Compose）。**引擎被打包不等于它是首屏或主 UI**，例如微信/微博含 Flutter、Duolingo 含 Unity、Element 含 React Native 子模块，必须在动态采样时再分主路径。

McDonald’s 的旧 React Native 标签没有得到包内引擎/类定义支持，改为 Android JVM；原来的 libGDX、Flutter、Gecko、native-engine 样本分开保留。所有逐 app 分类与证据见 [CORPUS.md](CORPUS.md)、[corpus100.json](corpus100.json) 和 [audit.json](audit.json)。这是一组 F-Droid、既有控制/原生引擎及商业热门 app 的目的抽样，不代表市场占比；移出 K-9 后，同源 SDK 与 Firefox/Fennec 的相关性仍使 100 个 app 不等于 100 个独立实现。

语料修订记录：

- `toutiao` 已恢复。输入 SHA-256 逐字节匹配 VM manifest 锁中的 `applications.toutiao.sha256`；保留原包及所有文件，`lib/arm64-v8a/libcvt.so` 的 ELF machine 为 ARM32，只从 AArch64 符号提供者集合排除。依据是 manifest `SOURCE_STACK.md:22–26` 与 `tools/prepare_app.py:98–105`，快照及锁项见 evidence。scan 的 `target-abi-available` 有效，OH/map 沿用同一 target ABI + machine 过滤。
- v1 将单个错标库扩大为整个 app 不合格，现按外环 #5 纠正。`exclusions.json` 保留原结论和证据，同时明确当前状态为 retained，避免将历史排除当现行规则。
- 移出 `fd-k9`，保留 `fd-android`（Thunderbird）以减轻同源偏重；不删除原 APK、锁项或残留 scan/oh/map。最终聚合器必须把 corpus 外的 `fd-k9` map 列入 ignored，不能让它污染分母。
- `co-weibo` 仍保留：v1 已校验富余候选来源、SHA-256 和 81 个 arm64 ELF。`fd-tutanota` 的 `armeabi` alias mismatch 仍不进入 arm64 提供者集合。
- 本任务没有改包、重签名或改 manifest 历史。`fd-noice` 使用 F-Droid 下载目录输入，不沿用历史板上 patch 产物；历史板上 P4 结果不能转移到本次哈希。

## 2. 流水线失败、修复与冻结证据

v1 首轮由 kimi 启动，以下失败已在 #2 定位并重跑；本次 v2 保留这些修补，以新指纹机制从零重建所有 corpus app 的三阶段产物：

| app/范围 | 根因 | 处置与复验 |
|---|---|---|
| `fd-plus`（OsmAnd） | GNU readelf 输出含非 UTF-8 字节；`subprocess.run(text=True)` 解码失败 | 隔离工具副本加 `errors="backslashreplace"`；ELF 动态符号仍由原始字节/pyelftools 提取；原包不动，scan 重跑成功 |
| `co-p2pmobile`（PayPal） | Androguard XML 部分 Android 属性无命名空间，严格 `_attr` 读出 22 个 null provider 名称，gap-map `.split()` 崩溃 | `_attr` 优先读取 Android namespace，缺失时读取同名裸属性；22/22 provider 名称恢复；gap-map 重跑成功，未用空字符串掩盖问题 |
| 多 ABI app 的 OH / map | scan 选了 arm64，但两个后续消费者仍遍历所有 ELF；既会引入 ARM32 依赖，也可能借错误 ABI 的 export 满足 ARM64 import | 消费者使用同一 `target_abi` + `abi_matches_machine` 过滤；全量 OH 与 maps 归档后重建；合成例确认 ARM32 export 不再满足 ARM64 import |

上表所涉四处底层 scanner/consumer 修补仍只在 `westlake-inputs/static100-tooling/` 操作副本，补丁存于 [operational-tooling.patch.txt](evidence/operational-tooling.patch.txt)。这不是已合入 harness 的修复；外环可另立 detector 条目采纳。若不用这份补丁直接拿原脚本从零复跑，会重现前两处失败和 ABI 污染。

本次新增的正式工具位于 [tools/static_pipeline.py](../../tools/static_pipeline.py) 与 [tools/aggregate_gaps.py](../../tools/aggregate_gaps.py)，内容同步到实际运行的 `westlake-inputs/tools/`。指纹机制为每个 app 在 `maps/<key>/pipeline-state.json` 记录：实际输入路径/SHA-256、runtime-index 路径/SHA-256/runtime_lock_id、工具包版本与源码/数据模型哈希、pipeline/CLI 入口哈希、Python 版本和配置。任何身份变化均归档旧三阶段结果并重跑该 app；没有 receipt 的旧输出也不信任。每阶段成功后原子记录输出 SHA-256，损坏的中间产物会使自身及下游失效；失败输出不会成为缓存。全局 runtime-index 改变影响所有使用它的 app，单 app 可用 `runtime_index` 指定独立快照。输出目录使用进程锁防止两个 writer 交错。

聚合器现在必须传 corpus；只读取其 app keys 对应的 map，外部 map 即使 JSON 损坏也不解析，在 JSON 的 `ignored_apps` 和 Markdown 的 Ignored maps 小节列出。corpus 内缺 map 则非零退出，避免悄悄发布少于 100 个的榜单。

验证证据：

- 100 个有效 JSON 三元组；每个 scan/map 哈希与容器实际 SHA-256 一致，包名/版本/runtime-lock 一致；split/XAPK 保留整个容器，内 APK 与 DEX 的组件哈希另记在 audit；不存在只拿 base APK 代替 XAPK 的情况。
- `static-100-v2.log` 的 `ok (` 行为 100，失败和 ABI 排除均为 0；[LEADERBOARD.md](LEADERBOARD.md) 首行含 `— 100 apps`。
- [逐 app 校验](audit.json) 的全部布尔 checks 为真；OH 解析按目标 ABI 与 provider export 集重新计算，100/100 与落盘结果一致；见 [verification.json](verification.json)。
- 本分支的宿主已知答案测试：`source .../env-mac.sh && PYTHONPATH=harness:tests python -m unittest discover -s tests -v`，79 tests，77 pass、2 skip（原 69 + 10 个新工具回归测试）。专项覆盖输入变更、单 app runtime 变更、同 lock ID 下内容变更、工具实现变更、旧输出无 receipt、输出损坏与失败续跑，以及 100 个 corpus maps + 一个非法外部 map 的过滤。没有把 skip 算 pass。
- runtime lock 的 9 个 boot jar + 1 个 bridge 逐项哈希匹配当前文件；OH 解析输入的 261 个 `.so` 文件哈希单独冻结（其中 197 个非变体且有 exports 的库进入 resolver 索引）。源码 HEAD 和工作区 clean 已核对，[provenance.json](provenance.json) 记录完整值。

相对 #2 原始未过滤 ABI 的历史基线，当前 21 个 corpus app 的 OH 缺失符号集合不同；差分包含语料变化，并非本次新增的兼容性修复。v1 → v2 数量变化另见 `revision-diff.json`。

真实 VM 缓存复验：仅将 `markor` receipt 的 runtime_lock_id 改为明确的测试值，然后对完整 corpus 续跑，结果 1 rebuilt（markor）+ 99 cached；规范的 runtime-index 与 APK 未改。独立运行时文件实际变更的单-app 隔离行为另由已知答案测试验证。原 receipt、扰动记录、输出和逐 app receipt 快照均归档。

原始扫描全量仍在 VM `~/a2hlab/static/scans`，单文件哈希与大小均入 audit；完整最终 gap-map（含 supplied 行和成员签名）压缩冻结在 [gap-maps.json.gz](gap-maps.json.gz)。逐步原始日志、原工具及修补差异在 [evidence](evidence/)；最终 corpus 同步到用户指定的 `westlake-inputs/corpus100.json`。

**证据边界**：这是 VM 源码构建 + OH SDK 公共库 + firmware link-only stubs 的静态供给集合，不是部署中的 DAYU600 完整运行时。runtime lock 只含 1 个 bridge、0 个 system library；另附 provider 输入哈希补充追溯，不能凭此声称已完成规范 §6 的设备快照。flat export union 不证明 DT_NEEDED、namespace、symbol version、可见性、ABI 或真实实现可调用；link-only stub 的符号存在也不证明语义。

## 3. 哪些共性缺口涉及最多 app

以下 `静态/硬` 均按唯一 app 去重，硬计数沿用聚合器的 `missing/null/strict/denied/stub/hollow/unresolved/absent` 集合，**是报告 verdict，不是运行阻塞判据**。同一 Java 分组可混合 missing、hollow-candidate 与 probe-only，因此不得用组首行的 C 类/effort 概括全组。

| 静态/硬 | 分组 | verdict 分布 | 解释 |
|---|---|---|---|
| 100/59 | `java:App framework` | hollow-candidate×41, missing×59 | apk-dependency-candidate |
| 100/51 | `java:Java library` | hollow-candidate×49, missing×51 | apk-dependency-candidate |
| 100/100 | `load:runtime-silent-success` | unresolved×100 | integrity |
| 99/41 | `java:Other` | probe-only×55, missing×41, hollow-candidate×3 | apk-dependency-candidate |
| 99/72 | `java:Views & windows` | hollow-candidate×27, missing×72 | apk-dependency-candidate |
| 97/1 | `java:Content & intents` | hollow-candidate×96, missing×1 | apk-dependency-candidate |
| 97/17 | `java:Graphics` | hollow-candidate×80, missing×17 | apk-dependency-candidate |
| 97/52 | `java:Other Android` | hollow-candidate×45, missing×52 | apk-dependency-candidate |
| 97/97 | `pm:call:resolveContentProvider` | stub×97 | apk-dependency-candidate |
| 97/0 | `pm:providers` | unverified×97 | candidate |
| 97/0 | `svc:accessibility` | inert×97 | candidate |
| 96/0 | `java:Widgets` | hollow-candidate×96 | candidate |
| 96/96 | `svc:notification` | hollow×96 | apk-dependency-candidate |
| 93/93 | `svc:audio` | hollow×93 | apk-dependency-candidate |
| 92/92 | `pm:call:getPackagesForUid` | stub×92 | apk-dependency-candidate |
| 92/92 | `pm:call:queryIntentActivityOptions` | stub×92 | apk-dependency-candidate |
| 91/91 | `pm:call:setComponentEnabledSetting` | stub×91 | apk-dependency-candidate |
| 89/89 | `pm:call:getComponentEnabledSetting` | stub×89 | apk-dependency-candidate |
| 88/88 | `pm:call:queryIntentContentProviders` | stub×88 | apk-dependency-candidate |
| 86/86 | `svc:textclassification` | unresolved×86 | candidate |
| 81/40 | `java:OS services` | hollow-candidate×40, missing×40, probe-only×1 | apk-dependency-candidate |
| 81/81 | `pm:call:queryIntentServices` | stub×81 | apk-dependency-candidate |
| 80/80 | `svc:jobscheduler` | hollow×80 | apk-dependency-candidate |
| 79/79 | `svc:user` | strict×79 | apk-dependency-candidate |
| 68/68 | `wv:renderer-process` | missing×68 | apk-dependency-candidate |
| 51/51 | `sym:bionic-private (not in the NDK)` | missing×51 | apk-dependency-candidate |
| 31/31 | `load:shadowed-by-board` | missing×31 | apk-dependency-candidate |
| 58/58 | `policy:lnk_file` | denied×58 | apk-dependency-candidate |
| 42/42 | `dep:google-play-services` | absent×42 | apk-dependency-candidate |

本次聚合得到 170 个开放分组，其中 101 组至少有一个硬 verdict；独立成员表含 899 个缺失 Java 签名/类型候选。

所有组的修复路径与工时见 [GAP-DISPOSITION.md](GAP-DISPOSITION.md)；所有组 × 所有栈的分布、which 清单、class/verdict 分布见 [gap-analysis.json](gap-analysis.json)。按高频共性路径看，PM 查询/组件状态、通知、音频、调度和 user 查询比“把所有 Java hollow 补成有代码”更值得做启动契约验证。

| 栈（分母） | PM provider | 通知 | 音频 | Job | User | native符号 | WebView |
|---|---|---|---|---|---|---|---|
| android-jvm (68) | 68 | 67 | 65 | 55 | 57 | 30 | 46 |
| flutter (8) | 8 | 8 | 6 | 6 | 5 | 4 | 8 |
| native-engine (8) | 7 | 7 | 7 | 6 | 5 | 6 | 3 |
| react-native (7) | 7 | 7 | 7 | 6 | 6 | 6 | 7 |
| libgdx/arc (3) | 1 | 1 | 2 | 1 | 1 | 1 | 0 |
| unity-il2cpp (2) | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| gecko (2) | 2 | 2 | 2 | 2 | 2 | 2 | 0 |
| webview-hybrid (2) | 2 | 2 | 2 | 2 | 1 | 0 | 2 |

**必须从产品缺口榜拆出的三类数据：**

1. `load:runtime-silent-success` 在 100 app 出现，因为生成器无条件对每 app 复制运行时属性；它属于独立 runtime integrity/注册表审计队列，不是 100 个已证明的 APK 依赖缺口。
2. `java:Content & intents`、`java:Widgets` 等许多高频项是 hollow 候选。所用 AOSP 的 `Application.java:264–265` 的 `onCreate()` 与 `Activity.java:7469–7470` 的 `onActivityResult(...)` 就是合法空体；不能自动判 C9 或添加副作用。C8 同样只能在静态、动态 DEX、反射和调用证据齐全后成立。
3. `not-a-platform-service` 包括格式串、日志文字、vendor 名等常量传播噪声；`unresolved`、provider `unverified` 和 SDK `environment-sensitive` 不能按“不支持”处置。它们进入 detector/取证队列。

规范 §12 需要稳定的 contract layer + owner/member/signature 身份。现有 `java:Views & windows`、`sym:bionic-private...` 只是工作包，不是 canonical gap。我们在分析附件为缺失 Java 成员保留了完整 signature，修复优先级要在这些签名与首阻塞间建立映射。

| app | 缺失成员（签名保留） | 状态 |
|---|---|---|
| 50 | `Landroid/view/accessibility/AccessibilityNodeInfo;->getChecked()I` | 静态缺失；动态到达未测 |
| 50 | `Landroid/view/accessibility/AccessibilityNodeInfo;->getExpandedState()I` | 静态缺失；动态到达未测 |
| 50 | `Landroid/view/accessibility/AccessibilityNodeInfo;->getSupplementalDescription()Ljava/lang/CharSequence;` | 静态缺失；动态到达未测 |
| 50 | `Landroid/view/accessibility/AccessibilityNodeInfo;->isFieldRequired()Z` | 静态缺失；动态到达未测 |
| 48 | `Landroid/view/RenderNode;` | 静态缺失；动态到达未测 |
| 47 | `Landroid/view/DisplayListCanvas;` | 静态缺失；动态到达未测 |
| 46 | `Landroid/app/Notification$Builder;->setShortCriticalText(Ljava/lang/String;)Landroid/app/Notification$Builder;` | 静态缺失；动态到达未测 |
| 36 | `Landroid/os/Build$VERSION;->SDK_INT_FULL:I` | 静态缺失；动态到达未测 |
| 34 | `Landroid/window/BackEvent;->getFrameTimeMillis()J` | 静态缺失；动态到达未测 |
| 30 | `Landroid/app/ActivityOptions;->setAllowPassThroughOnTouchOutside(Z)V` | 静态缺失；动态到达未测 |
| 29 | `Landroid/view/accessibility/AccessibilityNodeInfo$AccessibilityAction;->ACTION_SET_EXTENDED_SELECTION:Landroid/view/accessibility/AccessibilityNodeInfo$AccessibilityAction;` | 静态缺失；动态到达未测 |
| 22 | `Ljava/lang/Thread;->threadId()J` | 静态缺失；动态到达未测 |
| 22 | `Ldalvik/annotation/SourceDebugExtension;` | 静态缺失；动态到达未测 |
| 19 | `Ljava/lang/instrument/ClassFileTransformer;` | 静态缺失；动态到达未测 |
| 18 | `Ljavax/naming/NamingException;` | 静态缺失；动态到达未测 |

聚合脚本的 `top_missing_members` 当前错误地只匹配 `absent_*` / `missing_member`，而扫描输出是 `missing_class/method/field`，因此原 leaderboard 的此字段会空白；且原脚本按 owner/name 合并会丢 overload signature。本次保留该成员统计行为（#5 仅修 corpus 过滤），在 gap-analysis 中独立纠正。**未传 `--api-levels`，上述“缺失”还没有剔除非 Android API、较新 API 或 SDK_INT 保护分支**；因此这些高频 Android 新 API 先校准版本与可达性，再决定移植。

Native 方面，`oh-resolve` 未传 `--ndk-api-dir`，其 fallback 把所有未命名依赖写成 `bionic-private (not in the NDK)`。ANativeWindow、AMedia、AAsset 等不能因此被判为私有 Bionic；必须使用匹配 Android NDK 的声明库重新细分，不能拿 OH SDK 路径当 Android NDK。以下来自完整 OH missing 列表，扣除了 gap-map 识别的 shim symbol 覆盖，未受 `open_symbols[:20]` 截断影响。原始 OH-only 计数另存 gap-analysis 的 `oh_missing_symbols`：

| app | OH + 源码 shim 后仍开口的符号 | 候选修复路径 |
|---|---|---|
| 24 | `__libc_init` | 先核 AOSP/Bionic 已有实现/ABI；NDK 图形、媒体、传感器项再接 OH |
| 20 | `__system_property_read` | 先核 AOSP/Bionic 已有实现/ABI；NDK 图形、媒体、传感器项再接 OH |
| 15 | `SL_IID_ANDROIDSIMPLEBUFFERQUEUE` | 先核 AOSP/Bionic 已有实现/ABI；NDK 图形、媒体、传感器项再接 OH |
| 15 | `SL_IID_ANDROIDCONFIGURATION` | 先核 AOSP/Bionic 已有实现/ABI；NDK 图形、媒体、传感器项再接 OH |
| 13 | `AMediaCodec_configure` | 先核 AOSP/Bionic 已有实现/ABI；NDK 图形、媒体、传感器项再接 OH |
| 13 | `AMediaCodec_delete` | 先核 AOSP/Bionic 已有实现/ABI；NDK 图形、媒体、传感器项再接 OH |
| 13 | `AMediaCodec_dequeueInputBuffer` | 先核 AOSP/Bionic 已有实现/ABI；NDK 图形、媒体、传感器项再接 OH |
| 13 | `AMediaCodec_dequeueOutputBuffer` | 先核 AOSP/Bionic 已有实现/ABI；NDK 图形、媒体、传感器项再接 OH |
| 13 | `AMediaCodec_getInputBuffer` | 先核 AOSP/Bionic 已有实现/ABI；NDK 图形、媒体、传感器项再接 OH |
| 13 | `AMediaCodec_queueInputBuffer` | 先核 AOSP/Bionic 已有实现/ABI；NDK 图形、媒体、传感器项再接 OH |
| 13 | `AMediaCodec_releaseOutputBuffer` | 先核 AOSP/Bionic 已有实现/ABI；NDK 图形、媒体、传感器项再接 OH |
| 13 | `AMediaCodec_start` | 先核 AOSP/Bionic 已有实现/ABI；NDK 图形、媒体、传感器项再接 OH |
| 13 | `AMediaCodec_stop` | 先核 AOSP/Bionic 已有实现/ABI；NDK 图形、媒体、传感器项再接 OH |
| 13 | `AMediaFormat_delete` | 先核 AOSP/Bionic 已有实现/ABI；NDK 图形、媒体、传感器项再接 OH |
| 13 | `AMediaCodec_getOutputBuffer` | 先核 AOSP/Bionic 已有实现/ABI；NDK 图形、媒体、传感器项再接 OH |

此外 pipeline 没有提供 native-upcalls 的 platform-member 库，也没有动态下载 DEX、反射计算、JNI 运行注册、实际服务端行为的覆盖；零检测不等于没有缺口。

## 4. 按规范 §13 排序与修复路径

本语料已有分层且超过 25，但还没有 25 个可复现的动态阶段结果。**不发布复合 portfolio score**。每项的 dynamic-reached、first-confirmed-blocker、observed-stage-transition 均为 `null`（未测），不是 0。重要性暂按每 app 权重 1；没有暗中给商业 app 加权。以下是“先验证/再修”的执行顺序，不能冒充按已点亮收益排序。

| 顺序 | 工作包与规范队列 | 实现路径 | 启动关联、风险与验证出口 | 初步工作量 |
|---|---|---|---|---|
| P0 | detector 校准、启动 `<clinit>`；§13.1(1) | 本次四处操作修补正式化；增加 API level/分支过滤、NDK 声明索引、native-upcalls 输入、成员 signature 榜；逐合同排除合法空体 | `<clinit>` 中反射探测仍可能被捕获，不能只按方法名判启动致命；先做已知答案与 Android 对照。风险低，错误收益高 | 2–4 工日，不计为新增点亮 |
| 1 | `svc:user`；C9/C6 确认后进入(3)/(5) | 复用 AOSP UserManager 契约，对本机用户、解锁、限制状态作真实答复；不再由 strict 代理无条件抛异常 | 先录初始化调用/首异常；逐方法异常、权限与无用户场景，风险低 | 1–3 工日 |
| 2 | PM 查询、UID、组件状态；(3)/(5) | AOSP PackageManager/IntentResolver 语义 + SourcePackageRegistry，按 APK manifest/flags/权限答复；跨包时接 OH bundle 身份映射 | 初始化库查询 provider/service 和禁用组件可能早达；共享状态、authority、enabled 持久化、签名不能硬编码。风险中 | 工作包 5–10 工日，不能把每行相加 |
| 3 | `svc:jobscheduler`；(3)/(5) | AOSP JobInfo/JobScheduler 状态机，接 OH work_scheduler/后台任务能力 | WorkManager 启动登记、取消、持久化、约束和失败回调；返回默认成功不足。风险中 | 3–7 工日 |
| 4 | `svc:notification`；(3)/(5) | AOSP NotificationManager/channel/权限语义，接 OH notification 服务 | 初始化创建 channel、查询权限、服务通知关联；真无能力按契约返回。风险中 | 3–7 工日 |
| 5 | native 入口；确认 N-C1/J-C1 后(2)，C4(3)，C2(8)另拆 | 已存在实现只导出/注册；AOSP NDK 框架层复用；ANativeWindow → OH surface/buffer，AMedia → AVCodec，资产 → Android resources/包内资产；Bionic 布局/常量显式翻译 | lib JNI_OnLoad/dlopen 可能 P1–P2 首阻塞；需区分 ABI、状态/所有权和异步回调。高风险，不能统一“加同名 stub” | 转发小片 1–3；首批综合 5–20 工日 |
| 6 | loader/SONAME/namespace；(4)，runtime integrity 独立 | 复用 AOSP 的 namespace 和 app library 所有权规则；显式解析依赖次序，核对 Java natives 注册表；修 silent success | RN/Flutter/Gecko/native app 的潜在共享路径；不能全局优先某个 libc++。ABI 回归风险高 | 2–5 工日，注册表审计另 2–5 |
| 7 | 真缺失/真 hollow 的 Java/AOSP 成员；(3)，图形子项(6) | API epoch 与可达性校准后按签名移植 AOSP；只有落到设备边界才换 OH backend。RenderNode/Canvas 不得凭名字补空类 | 静态数量大，但新版本分支/合法 no-op 比例未知；RenderNode/HWUI 合同必须测 P4a 与 P4b。风险中至高 | 小簇 3–10 工日；覆盖全部 Java 分组需多迭代、约 20–60 工日，低置信度 |
| 8 | `svc:audio`；(5)/(6) | AOSP AudioManager 焦点、路由、音量语义，接 OH audio framework | 对媒体 app 比一般 app 更重要；即使过首屏仍须验证回调顺序、设备变化与播放。风险中 | 5–15 工日 |
| 9 | WebView renderer / 多进程；(5)/(6) | 保留 Android WebView/进程/IPC/ContentProvider 生命周期，用 OH appspawn/IPC/surface 承载；独立确认 Chromium 或 ArkWeb 接入边界 | WebView hybrid 可能是首屏依赖，其余 app 可能是广告/登录后路径；通用多进程不是局部 shim。风险高 | 10–25 工日以上 |
| 10 | WiFi/Keyguard/生物识别/设备 manager；(5)/(6)或经证实 C5 | 有能力时 AOSP facade → 对应 OH 子系统；无硬件/权限时暴露真实 feature/unavailable，manager 返回约定而非随意 null | 首屏普遍性低于前三包；每个设备能力单独确认，不能由源代码名推断 DAYU600 已提供。风险中 | 每类 3–10 工日 |
| 分队列 | GMS/完整性、策略、可选 SDK；(7)/(8)/(9)/(10) | GMS 专有服务与服务端校验诚实不支持；OH 可替代功能另立契约；fifo/link 由实际 OH policy 决定；C10 与 R-C7 必须独立证据 | 不绕过认证/完整性，不把 kernel policy 变成 Java stub，不拿截图黑屏证明渲染失败 | 缺能力声明/降级 1–3 工日；OH 政策/后端 5–15+；R-C7 未定位不报精确工时 |

工作量是单名熟悉 Android/OH 的工程师的**容量占位区间**，包含实现、契约测试和一次设备回归，不是已批准的 Task Contract 估算，也不是 agent 分钟承诺；API 校准结果、硬件权限、AOSP 可复用程度会改变区间。当前调用频次、首路径、severity 深度和 causality confidence 未知，不代入 §13 公式制造精确分数。

路径依据以本次固定的本地 AOSP 与 Westlake 源码为主；namespace 设计可核对 [AOSP linker namespace 文档](https://source.android.com/docs/core/architecture/vndk/linker-namespace)，阶段验证应遵循 [Android Activity 生命周期](https://developer.android.com/guide/components/activities/activity-lifecycle)。两者支持契约/验证方向，不证明 OH 当前实现可用。

## 5. 修复前 N 项能让多少 app 越过启动路径

本报告把“越过启动路径”操作化为后续实测 **P2 Application attach/create + 进程存活 → P3 首 Activity create/resume → P4a ViewRoot/有几何或文本的 view tree → P4b 独立的 surface/buffer/present 证据**，每个判据独立；进程存活、截图、静态无缺口均不能单独充当成功。当前所有 app 的这些状态未测，**已验证新增越过数为 0；实际可新增数未知**。

为给排期一个可复算的量化范围，使用三种不同口径；不把相交 app 重复相加：

- 覆盖：有至少一条硬 verdict 落在前 N 工作包中的 app 并集；表示值得做回归的候选规模。
- 硬行清零：移除前 N 包后，该 app 原来的硬 verdict 集合为空；排除全体复制的 runtime integrity 行。只是静态集合指标，既不是运行成功的充分条件，也不是首屏必要条件。
- 乐观启动候选：额外假设所有 sandbox policy、GMS/其他外部依赖、非 user/job/notification/audio 的 service 都不在启动路径或能正常降级，且所有候选/未验证行不是启动阻塞。其余硬行需全被修复包覆盖。**这些假设尚未被证实**，尤其商业 app 的风控、Google 登录和 JNI 最可能使上界失效。

| 前 N 项 | 新增工作包 | 覆盖 app 并集 | 全部静态硬行清零 | 乐观启动候选 | 实际越过启动 |
|---|---|---|---|---|---|
| 1 | user | 79 | 0 | 0 | 未测 |
| 2 | package-manager | 98 | 0 | 0 | 未测 |
| 3 | jobscheduler | 98 | 0 | 0 | 未测 |
| 4 | notification | 98 | 0 | 0 | 未测 |
| 5 | native-entrypoints | 100 | 0 | 1 | 未测 |
| 6 | loader | 100 | 0 | 1 | 未测 |
| 7 | java-members | 100 | 1 | 2 | 未测 |
| 8 | audio | 100 | 1 | 26 | 未测 |
| 9 | webview-process | 100 | 1 | 100 | 未测 |
| 10 | device-managers | 100 | 1 | 100 | 未测 |

因此，前 1/3/5 项的“触及很多 app”不能解释为点亮很多 app；前 7 项开始移除 Java 分组后、前 8 项补音频后、前 9 项补进程体系后，乐观候选集合才显著变化。第 7/9 项是大工作包，不与单方法修复等成本。乐观列给出的只能是 **0–该列值的条件化规划区间**，不是置信区间或真实收益上限；由于静态误报/漏报，现实结果也不受这个模型严格约束。未引入没有依据的“成功概率 30%”一类常数。

完整前 N 列表、精确 app 名单、覆盖的 gap IDs、乐观豁免 IDs 在 gap-analysis 的 `scenarios` / `model_assumptions`。后续上板采集首因后，替换为每 app 的必要启动阻塞集合，按交集清空计数，然后才按 §13 用真实 reachability、severity、confidence、effort 与 risk 计算分数。最有信息量的第一轮应在每栈选控制 + 失败样本并覆盖纯 JVM、小 native、跨语言引擎、WebView、商业初始化路径；不是先挑最容易成功的 25 个。

## 6. 复验命令与交付状态

所有 VM 命令均经 `orb -m a2hlab bash -lc "<cmd>"`；以下 Python 工具快照和完整补丁随 evidence 保存，不依赖聊天记忆。v1 的按文件存在跳过机制已由指纹 + 阶段输出哈希替代：换包、换 runtime、换工具时自动失效。v2 聚合器允许保留 corpus 外的 maps；它们明确列为 ignored。

```bash
# 宿主：操作副本在 westlake-inputs/static100-tooling；无需设备
source ~/orca/workspaces/westlake-inputs/env-mac.sh
PYTHONPATH=harness:tests python -m unittest discover -s tests -v

# VM：最终 100 个均可续跑；现存结果仍须 audit 验证身份
orb -m a2hlab bash -lc "PYTHONPATH=/Users/zhaoyue/orca/workspaces/westlake-inputs/static100-tooling ~/a2hlab/harness-venv/bin/python /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/static_pipeline.py /Users/zhaoyue/orca/workspaces/westlake-inputs/corpus100.json ~/a2hlab/static --jobs 4"
orb -m a2hlab bash -lc "python3 /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/aggregate_gaps.py ~/a2hlab/static /Users/zhaoyue/orca/workspaces/westlake-inputs/corpus100.json"
orb -m a2hlab bash -lc "python3 /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/audit_static100.py /Users/zhaoyue/orca/workspaces/westlake-inputs/audit-review"
```

证据快照重算分析：把 `evidence/analyze_static100.py.txt` 复制为临时 `.py`，执行 `python3 <该脚本> <本目录>`。逐文件完整性用 `shasum -a 256 -c SHA256SUMS`。两个流水线工具修复已入本分支；底层 scanner 操作补丁仍未合入 harness library。设备上的 R2 verified、动态首阻塞确认、任何推送均未在本任务中声称完成。
