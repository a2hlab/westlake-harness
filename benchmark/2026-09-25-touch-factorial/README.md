# #25 头条启动期触摸延迟：数据 × UID 网络隔离

仅使用 `5ea34a4500000000000000001123012c`，内环 codex-2；独立 harness worktree / 分支 `analysis/touch-factorial-25`，只 commit、不 push。使用 #21 的 `out-touch21/wake` 诊断构建、`WL_TOUCH_TRACE=1`，未修改 APK 或运行时行为。

**结果：#25 调查完成，R2=partially。** 八轮 trace、原始证据、主线程锁链及静态产物核对已验证；方法耗时是采样估计，native 栈未取到，修复收益未验证。

## 测量口径

- 四格各两次独立进程；表内没有点击期间主动 SIGQUIT。以底部“头条”导航出现为共同触发条件，前台化宿主后，以 `i 309 213` 注入 DOWN/UP，按同一 action + event 配对 `[TOUCH21] post/run`。这是排队延迟，**不是信息流换内容耗时**；离线全新数据没有下载到频道配置。
- 全新：停止本部署的 child 和 parent，确认无进程 mount 引用，再清空隔离的 `app-data`、`data`（ART cache）、`webview-t-data`，重新启动 parent/child。APK、framework、native 库保持相同；系统页缓存未清空。
- 复用：每轮都恢复同一份离线启动后快照，避免联网种子与离线种子不同。快照含 236 个普通文件，逐文件哈希已与原目录核对；UID、权限由 tar 保留，应用目录重新应用原 SELinux label。socket 不进入持久快照。快照原始 SHA256：`00e756c615e4dd17928f528a036cb985c636a6c7ef810b709cd8ada00282ca2f`。
- 离线：仅 `iptables` / `ip6tables` OUTPUT owner UID `20010053` 丢包；这是本板专用 Westlake host/头条 child 的 UID。Wi-Fi 和系统联网状态不改；这与 #21 的整板失联不是同一种 ConnectivityManager 状态。联网轮撤销本任务规则。起止规则、丢包计数与 wlan0 地址均存档。
- 运行顺序交错，记录在 `evidence/matrix.log.gz`。每格 n=2 只支撑这些样本，不是统计总体结论。全新数据与复用数据的启动路径不同；另记录启动到点击时间，不能将其误称为固定启动秒数的实验。

## 四格结果

单位毫秒，单元格为 DOWN / UP；原始解压行号由 `evidence/summary.json` 给出。

| 网络 | 数据 | 第一次 | 第二次 | run 名 |
|---|---|---:|---:|---|
| UID 离线 | 全新 | 21499 / 21406 | 21374 / 21491 | offline-fresh-3 / 4 |
| UID 离线 | 固定快照复用 | 10656 / 10658 | 8331 / 8227 | offline-seeded-1 / 2 |
| 联网 | 全新 | 11451 / 11364 | 13217 / 13191 | online-fresh-1 / 2 |
| 联网 | 固定快照复用 | 11662 / 11586 | 13186 / 13244 | online-seeded-1 / 2 |

**全新数据离线也慢；复用数据联网与离线也都可能慢。** 联网两种数据条件接近，离线全新数据明显慢于离线复用。这些结果排除了“联网是长延迟的必要条件”，也不能支持“复用数据一定 1ms”。

额外对照 `offline-fresh-diag1`：同一进程早期 22611 / 22634ms，启动工作结束后的第二次点击 1 / 0ms。前者含采样扰动，不进正式表；后者说明这个 UID 离线条件下投递路径能够及时消费。#21 warm1 的 1ms 不能仅归功于离线或旧数据，启动阶段也必须对齐。

## UI 线程在做什么

采用 `offline-fresh-diag2` 的 **32 份**主线程样本（sysTid=11021，最大样本间隔 1.368s），在 post(DOWN) 至 run(UP) 的 21.709s 窗口内以相邻采样时间中点划分权重。以下是互斥工作分类的前五项；同一条栈只归一类，避免父子方法重复计时。**耗时为抽样占用估计，不是方法入口/出口实测或 exclusive CPU 时间**；1.3–1.5s 的近邻排名不具备精细区分能力。完整分类规则、全部样本和其余工作在 `scripts/work_groups25.py` / `evidence/work-groups.json`。

| 工作（方法） | 估计占用 | 命中 | `offline-fresh-diag2/child.stderr.gz` 解压行号 |
|---|---:|---:|---|
| `VanGoghServiceImpl.init` → Downloader / `TTDownloader.<init>` / Mannor 初始化 | 3.663s | 5 | 40623, 44516, 48343, 52230, 56207 |
| `LuckyDogSDKApiManager.initWithCallBack` → task settings、`initSettings`、timer 类初始化、容器回调 | 3.350s | 5 | 76612, 80770, 84857, 88993, 93044 |
| `ResourcesManager.applyConfigurationToResources` → `DisplayManagerAdapter.nativeGetDefaultDisplayHeight/Dpi` | 1.517s | 2 | 7119, 127525 |
| `ViewRootImpl.performTraversals` → `HardwareRenderer.nPause/nSyncAndDrawFrame` | 1.353s | 2 | 3406, 114313 |
| `SourcePackageRegistry.contains` 等待签名校验所持全局类锁 | 1.342s | 2 | 29152, 32993 |

这些工作总计只覆盖窗口的一部分，其余包括 Npth/Splash 初始化、LuckyDog plugin-ready、Emoji、前后台回调等，不能把前五项合计当成全部延迟。栈中直接见到 `<clinit>` 和 `Class.forName`，但没有把所有 SDK 时间都归因于 ART 类校验；没有观察到证据足够的数据库迁移主因。

联网密集轮 `online-fresh-diag1`（sysTid=7692，12 份样本，最大间隔 1.873s）前五项：LuckyDog 初始化约 1.994s（L37309/42485），PackageRegistry 锁等待约 1.726s（L24056/28189），`TranscodeConfigUtil.checkScriptConfig` 的 Kotlin lazy 锁约 1.357s（L47685），`String.fillBytesLatin1` 所在 JSON 序列化链约 1.320s（L53190），Splash 初始化中的 `Alog.nativeWrite` 约 1.150s（L32739，线程状态 D）。后两项仍需要更细 native/IO 计时才能把函数本体与采样间隔内其他工作分开。

### 已闭合的锁等待因果链

在联网轮 L24056 与 L28189，UI 正等待 `SourcePackageRegistry` 类锁，持有者均为 ART thread **207**；两样本相隔 **0.692s**，UI schedstat CPU 与 runnable-wait 计数均相同。相同 dump 的持锁线程见 L24488 与 L28674：`bd_tracker_n:13` / sysTid=9450 正在 `SourcePackageRegistry.packageInfo → PackageParser.collectCertificates → ApkSignatureSchemeV3Verifier → ApkSigningBlockUtils.computeContentDigestsPer1MbChunk`，叶子分别为 SHA256 的 `EVP_DigestUpdateDirect` 和 mmap chunk 的 `munmap`。锁对象 ID 完全一致。

离线密集轮也复现同一机制：L29152/32993 的 UI 等 ART thread 168；该持有者是 sysTid=12502 的 `bd_tracker_n:13`，同样在整包签名摘要路径。

源码快照 `evidence/SourcePackageRegistry.java.txt`（L48, L120–127）：`contains` 与 `packageInfo` 都是 static synchronized；`packageInfo` 在该锁内同步 `collectCertificates(parsed, false)`，非签名查询也必须先经过 `contains` 的同一锁。因此普通包查询会被后台签名校验挡住。证据支撑此机制，**不支撑“这一把锁解释整个 21 秒”**。

另一条有持有者证据的锁是联网轮 L47685 的 `SynchronizedLazyImpl.getValue`：UI 等 ART thread 220；L48217 的 `platform-io-thread-13` 持相同 lazy 对象锁，正在 Gson / 反射构造 XBrowser 配置。这是应用配置初始化与主线程的依赖，不能靠改变触摸 Handler 类型消除。

### 修复方向与工作量估计

本条不修改运行时，以下估计按单工程师、现有构建和本板可用计，需后续实测验收：

1. **优先拆分 SourcePackageRegistry 的读路径与证书校验锁：1–2 个工作日。** 已验证元数据以不可变快照发布；`contains`、不要求签名的读请求不等待整包摘要。签名校验使用独立的一次性任务/状态，成功后原子发布结果，要求签名的请求仍等待真实校验，失败仍报错。增加“证书计算阻塞时普通查询可完成”、并发首次查询、APK 变更/校验失败的回归，再重跑本四格。不要跳过校验或伪造证书。本次抽样提示约 1–2s 的等待机会，不承诺整个启动降到亚秒。
2. **给 Looper 分发、SDK 入口、类加载与锁等待加低扰动起止计时：0.5–1 个工作日。** 用上述明确的方法和锁做定向记录，再决定优化类加载、配置解析或重复平台查询；补取 native/IO 栈需使用获准的诊断通道。本轮 SIGQUIT 已能定位调用链，但不够确定每个小方法的独占成本。
3. **按精确 profile 处理后续热点：每个热点约 1–3 个工作日，当前低置信度。** 候选为重复 display/config 查询、Alog 同步写路径、SDK 初始化中的反射/类加载与配置序列化。保持原 APK、回调次序和真实平台结果；不能把整个 SDK 初始化任意挪线程、丢日志、跳回调或用触摸线程直接执行 UI 工作来制造快结果。全部消除 8–21s 启动积压尚无可靠总工期。

当前证据无需用 nativeWake 丢失解释：UI 忙于上述工作，同进程稳定期 0–1ms 投递已出现；这不等于证明所有条件下都不存在 wake 问题。

## 证据与复核

已通过本地 `verify25.py`：214 份对象哈希与 gzip 往返、八轮 16 对 trace、相同 runtime/seed、UID 规则及“基线取栈晚于消费”断言。脚本语法检查与 `git diff --check` 通过。

所有 `.stderr.gz` 为原始日志逐字节 gzip，行号指解压后的文件。`files.json` 同时记录原始与压缩对象哈希；`summary.json` 从原始 trace 重算，不使用截图代替事件配对。SIGQUIT 主线程以栈底 `ActivityThread.main` 判定，不能按 `Thread-2` / `CrBrowserMain` 名字猜。

```sh
python3 benchmark/2026-09-25-touch-factorial/scripts/summarize.py benchmark/2026-09-25-touch-factorial/evidence
python3 benchmark/2026-09-25-touch-factorial/scripts/profile25.py benchmark/2026-09-25-touch-factorial/evidence
python3 benchmark/2026-09-25-touch-factorial/scripts/work_groups25.py benchmark/2026-09-25-touch-factorial/evidence
python3 benchmark/2026-09-25-touch-factorial/scripts/verify25.py
```

板操作脚本只绑定本板，原始命令保留在 `evidence/operations.jsonl.gz`。它们是有状态实验的审计记录；不要整批盲目重放 cleanup/stage，需使用新 run 名并检查在途 namespace。VM 入口一律为 `orb -m a2hlab bash -lc "<cmd>"`。

## 测前清理

旧日志归档为 VM 的 `~/a2hlab/board/5ea34a4500000000000000001123012c/touch25/old-logs.tar`：581538816 bytes，SHA256 `db417e707886ca4453a0dead2d2fee232274fda630c362c764d488f2f4a1e27e`，板端与 VM 相同；成员清单见 `evidence/old-archive.json`。归档后清理 77 个旧部署目录。初次引用匹配因 mountinfo 缺 `/data` 前缀漏掉旧 parent 2394，之后按已确认 socket / PID 补杀，并在正式测量前核对；脚本已改按部署 basename 匹配，不把这次中间失误省略为“全程无遗漏”。本任务保留诊断部署及新证据供复验。

## 排除与限制

- `offline-fresh-1` 等待离线不存在的频道配置超时，没有有效触摸；`offline-fresh-2` 在触摸消费前做过一次 SIGQUIT；`offline-reuse-2` 是形成固定种子的探索轮。三者均不进入正式四格。
- 在线复用两轮出现 work_thread SIGABRT 日志，触摸仍完成；独立记录 fatal 与 UI 返回，不把二者直接当成同一因果链。本条没有修复 #23 的联网生命周期问题，也未验证五分钟存活。
- `dumpcatcher -p ... -t <UI tid>` 失败返回访问 `/proc` 的 errno=13，并声称 target killed；同窗口 SIGQUIT 和触摸仍继续，因此该失败不是退出证据。未修改系统安全策略。失败等待会使 `offline-fresh-diag1` 的采样间距较大，不能把其单点权重当成函数实测耗时。

收尾核对：306 个部署运行时文件 SHA256 与 framework/source_files 完全相同；本任务网络规则均撤销，无本任务部署的存活 mount 引用，Wi-Fi 地址仍为 192.168.0.109。见 `evidence/final-runtime-verification.json` 和 `evidence/final-board-state.txt`。
