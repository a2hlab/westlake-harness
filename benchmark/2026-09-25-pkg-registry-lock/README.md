# #28：包证书验签移出 registry 类锁；点击门槛未达标

**结论：锁拆分、每包一次性缓存与真实验签已实现；`<2s` 验收失败，ACK(blocked)，R2=partially。** 四个正式新进程均完成点击、无致命信号/UI 返回。拆掉这个等待点没有消除启动队列中的其他工作，不能把实现完成写成整体性能验收通过。

仅板 `5ea34a4500000000000000001123012c`。VM source worktree `~/a2hlab/ws/westlake-pkg28`，harness worktree `/Users/zhaoyue/orca/workspaces/westlake-harness-pkg28`，两库均用独立分支 `fix/pkg-registry-lock-28`，只 commit、不 push。源码提交 **`b80aebbf36f8eda0c28a9ce079026ac5a65fe5f3`**。源码基线 `b3dae7aed16f10ba492e2bd6c7a02bc17b2bbf58`，已确认包含 `2478a7f`（#11/PM）；harness 基线 `bc20d1c` 保留完整 #25 对照。

## 实现和验证边界

选择 #28 方向①：volatile 发布完整 Entry，包名/UID 查询无锁；注册使用独立锁；按包名查到唯一 Entry 的 FutureTask，实现一次计算、并发请求等待同一结果、成功和失败都缓存。原有“一进程一个 source package”的注册限制保持，所以缓存是按包名查找的单条目，无需引入多包注册或失效协议。

昂贵的 `PackageParser.collectCertificates(input, false)` 在注册锁和元数据锁外执行。验签会修改 Package 的签名字段，因此使用私有输入对象，复制原 APK baseCodePath、splitCodePaths 和完整 ApplicationInfo；保持 target SDK、static shared library 标志和各 split 一致性验证。成功后在 Entry 的短锁内用 `setSigningDetails` 发布，PackageInfo 生成与 Parcel 深复制仍串行。失败保留 SecurityException 和原始原因；等待中断保留 interrupt 状态。

GET_META_DATA **原来就不会主动发起验签**；原缺陷是其他线程的验签持有全局类锁，挡住了这个查询。本次保留原有签名 flags 判断、processName 修正、Direct Boot 默认位、权限与返回值隔离。真实验证仍走 `ApkSignatureVerifier.verify`，未改 APK、未关闭校验。

生产源码直接参与的并发测试通过：12 个并发签名请求 + 10 次后续请求，成功/失败两种情况都只调用 parser 一次；故意挂起验签时，100 次普通查询在 2s 超时内完成，调用者修改返回值不污染后续查询。该测试用 Android doubles 控制线程时序，**不是密码学验证**。真实 APK 验签证据来自下列板上日志。

## 可比性能结果

复用 #25 的触发与注入协议：fresh 删除 app-data、ART data、webview-t-data，重启 parent/child；首次部署使用新随机根目录。底部“头条”导航出现后前台化宿主，等待 1s，再 `i 309 213`。离线只对 UID 20010053 的 IPv4/IPv6 OUTPUT 丢包，未关闭 Wi-Fi。每个正式进程仅在点击消费后 SIGQUIT。独立诊断进程不混入此表。

原 APK SHA256：`a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395`。沿用 `out-touch21/wake` native / appspawn 与 WL_TOUCH_TRACE=1；仅 Java 与 boot 构建到独立 `out-pkg28`。

| 条件 | #25 两次 DOWN/UP (ms) | #28 两次 DOWN/UP (ms) | 点击中位数：前 → 后 |
|---|---|---|---|
| offline-fresh | 21499/21406；21374/21491 | 20590/20648；20897/20989 | 21495 → **20818.5 ms** |
| online-fresh | 11451/11364；13217/13191 | 13838/13834；11028/10979 | 12334 → **12433 ms** |

每次点击取 max(DOWN,UP)，再对两个独立进程取中位数；[results.json](results.json) 同时提供各 action 的中位数、精确 trace 行号和触发时间。两种口径均远大于 2s。这是 post→run 队列延迟，**不是信息流切换内容耗时**；小样本不支持对约 0.7s 差值作显著收益推断。对照来自已采认 #25 同日实验，并非交错随机 A/B。

## 真实验签与剩余工作

每个下列进程的原始日志均为 **1 次 start、1 次 pass、0 次 fail**。次数通过实际 start 标记条数统计，不仅依赖日志中的 count=1 注释。

| 进程 | child PID | start/pass 行号 | 校验耗时 |
|---|---:|---:|---:|
| offline-fresh-1 | 30981 | 3638 / 3768 | 2233 ms |
| offline-fresh-2 | 1303 | 955 / 1098 | 1772 ms |
| online-fresh-1 | 3999 | 12813 / 12998 | 2423 ms |
| online-fresh-2 | 6454 | 1268 / 1523 | 1945 ms |
| offline-fresh-diag1 | 10031 | 25022 / 32715 | 2323 ms |
| online-fresh-diag1 | 12312 | 1359 / 1531 | 1949 ms |

日志位于 `evidence/<进程>/child.stderr.gz`，解压后行号。例如第一轮 L3638 为 `start ... skipVerify=false`，L3768 为 `pass ... scheme=3 signers=1 elapsedMs=2233`。第二轮离线 **验签通过发生在点击 post 之前**，后续仍排队约 21s，足以否定“只移出这次验签即可消除全部点击延迟”。

独立 SIGQUIT 采样按 `ActivityThread.main` 栈底识别 UI，共离线 32、联网 16 份；48 份均无 SourcePackageRegistry 栈帧，原等待链未再采到。并发测试补充证明验签期间普通查询可完成。有限采样不等于证明任何短等待都不存在。

剩余 UI 工作示例（诊断日志原始行号）：

| 工作 | offline-fresh-diag1 | online-fresh-diag1 |
|---|---|---|
| HardwareRenderer.nPause | 2886、6656、10344 | 13324、17068 |
| AppLog / 启动初始化 | AppLogInstance.init：17731 | OldAppInitLoader.prepareDelayInit：32712 |
| VanGogh / Downloader | VanGoghServiceImpl.init：44452；TTDownloader.init：52297；initDownloader：60151 | — |
| LuckyDog | updateSettings：80377；initWithCallBack：88639 | LuckyNewTimerManager.tryInit：41524；onDogPluginReady：46230 |
| display / 绘制 | GradientDrawable.draw：114263；getDisplayInfo：123136 | getDisplayInfo：56813、68681、74804、85953 |

此处只列采样命中，不伪称精确方法耗时。后续需单独归因剩余主线程启动任务及 display 查询成本；本条没有改 SDK、迁移其初始化线程或更改点击触发时点来满足数字。

## Noice / Wikipedia 对照

| 应用 | child / UI tid | 真实输入结果 | 点击后额外存活观察 |
|---|---|---|---:|
| Noice | 16293 / 16310 | i 1119 1841：Welcome → Design your ideal environment；标题 x=36，旧页 x=-1164 | 66.600s（DOWN/UP 1/53ms） |
| Wikipedia | 21993 / 22013 | i 1150 1870：All the world's knowledge → Data & Privacy；截图目视核验 | 66.768s（DOWN/UP 1/17ms） |

两个窗口内均无 Fatal signal、INITCHILD-FAIL 或该 PID 的 faultlog，符合既有启动/翻页烟测表现；未做全功能回归。Noice 原有两条 `<get-mainActivityPi>(...) must not be null` NPE 仍在 child.stderr L716/L742，明确保留，不宣称零异常。Wikipedia 的 Compose 页面不提供普通 TextView 文本，采用[点击前截图](evidence/control-wikipedia/wikipedia-before.jpeg)与[点击后截图](evidence/control-wikipedia/after.jpeg)核验；截图 SHA256 和人工目视声明在 visual-verification.json。重跑 `finish_control28.py ... --visual` 时需独立查看新截图并记录核验，不能复用旧声明。

## 构建与证据复核

Java、runtime packaging、boot image、板上 framework preload 均通过。73 个 adapter 源文件与构建清单哈希相符。相对 #25 的 306 个部署静态文件，只变更 `fw/adapter-runtime-bcp.jar` 与 8 个 boot 产物，其余 297 项（包括 APK 和 native）完全相同；见 [build-provenance.json](evidence/build-provenance.json)。完整 build manifest 和日志归档在 `evidence/build/`。135 份归档的原始/存储 SHA256 与 gzip 往返均已核验；最终 306 个板上静态文件全匹配，任务 namespace、进程、触摸转发器和 UID 丢包规则已清除，Wi-Fi 保留。收尾状态见 evidence 内 final-*。

复算（宿主，只读实验数据，summary/results 会原样重新生成）：

```sh
cd /Users/zhaoyue/orca/workspaces/westlake-harness-pkg28
python3 benchmark/2026-09-25-touch-factorial/scripts/summarize.py benchmark/2026-09-25-pkg-registry-lock/evidence
python3 benchmark/2026-09-25-pkg-registry-lock/scripts/metrics28.py benchmark/2026-09-25-pkg-registry-lock/evidence
python3 benchmark/2026-09-25-pkg-registry-lock/scripts/verify28.py --git
```

板上重跑入口在 scripts：build.sh → stage.py → matrix28.py → post_matrix28.py；控制应用由 controls28.py / finish_control28.py 执行。所有 VM 入口均须 `orb -m a2hlab bash -lc "<cmd>"`。scripts 使用固定板 5ea34a45；已有实验目录不覆写。并发测试位于 runtime commit 的 `tests/pkg-registry-lock/test_registry.py`，复现命令见该库 `PACKAGE-REGISTRY-LOCK-28.md`。
