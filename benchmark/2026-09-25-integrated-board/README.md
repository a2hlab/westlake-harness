# #32 总集成上板验证

结论：**部署/框架preload及两个对照烟测通过，头条端到端被既有启动故障阻断，无法签“合并后无回归”。** 两次头条均在7秒、bind完成前a-4 SIGSEGV，尚未进入同意/信息流。与#23同版属性shim且不加metasec target的既有6/7/6秒记录同签名；未发现足以归因总集成新增回归的证据，也没有证明后续路径无回归。没有实施修复。

## 构建与部署

- westlake `integrate/all-20260925` HEAD `e5666e4a90d9da2e1527270eb4974f1638f2bb93`，运行时代码构建源 `d835639`；ART `1a190e8b7b08f13ef4349153136534f6c8296fc8`。运行时源码树clean。
- VM `/home/dspfac/a2hlab/source-closure/verify/out-all0925`：appspawn、native-runtime（同时作core-runtime）、framework-runtime、framework-boot、webview-candidate均来自该构建；其它core Java/resources/data输入沿用#27所列共享只读产物。
- 仅板 `5cd1e3dd00000000000000000923012c`。`probe_framework_vm.py` 部署，preload exit=0，`SOURCE_FRAMEWORK_PRELOAD_PASS`；未要求的专门contracts不是本轮通过项。
- 板上framework 306项SHA256逐项匹配部署报告；另核本地out-all0925顶层可匹配的appspawn/native产物58项均一致（不冒称这个额外子集覆盖全部boot嵌套文件）。四轮app目录中WebView六文件各自实核全部匹配。见 `evidence/framework/hash-verification.json`、`evidence/provenance.json`、`evidence/webview-hash-verification.json`。
- 头条参数严格为三个native targets：libvision_core.so、libc++_shared.so、libsscronet.so；net target libsscronet.so；**没有metasec target**，没有#30扩展图片库targets。仅沿用观测用 `WL_TOUCH_TRACE=1`，不传GPU环境覆盖。

测量夹具 `scripts/start.py toutiao-N toutiao --p2-wait 120` 复用boardloop `40748f0` 的 `has_p2_marker`，轮询上限120秒；进程已消失则提前终止，而非等待满120秒再取空日志。这里是交互验收夹具，不直接运行会在测量后清进程的boardloop批量runner，也未把不受支持的参数传给probe_source_app。`launch.py` 使用已有out-touch21/probe-local launcher，仅把runtime源码与产物参数切到总集成；脚本原文归档。两次等待实际4.816/4.919秒、状态exited-before-bind；这是probe返回后的等待时长，**不是进程寿命**。

## 头条逐项验收

|项目|toutiao-1 child26793|toutiao-2 child29260|证据/解释|
|---|---|---|---|
|过同意|fail：未到达|fail：未到达|两轮sBindAppDone=true均0，退出前未获得同意UI|
|Unable to load function ASurface=0|字面计数pass：0|字面计数pass：0|WebView未到达，不能据此判“WebView不崩”通过|
|WebView不崩/可进入|未覆盖|未覆盖|早期崩溃阻断，没有有效WebView截图|
|Cronet bootSucceed=1|fail：0|fail：0|完整child日志计数|
|信息流≥3真实标题|fail：无可验标题|fail：无可验标题|没有有效信息流VT或截图，不用死亡后的host屏代替|
|i点条目→B47-SLA/新Activity|fail：未执行|fail：未执行|无条目可点，B47-SLA计数0，不伪造点击通过|
|联网存活|7s|7s|各cppcrash Process life time|

两轮原始child.stderr致命信号在 **L370 / L368**，a-4线程；faultlog均 `pc=0x4000, lr=0, sp=x29=0x7b`。原始stderr以gzip保存，行号按解压后的原文。首轮L352另有libkeva的__ndk1缺符号，参数未加入该库，按要求保留。两轮启动前ping均5/5、0%丢包，不代表应用全程联网质量。没有work_thread SIGABRT样本，观察窗只有7秒，不能宣称该问题解决。

看板预期约82秒TLS崩溃对应#23**加入metasec target**的配置；本任务明确不加，实际重现的是默认namespace的早期a-4签名。不能把7秒故障写成82秒预期，也不能由当前故障说明TLS问题已解决。这里阻断的是端到端验收，不宣告它是新合并回归。

## 与分散构建比较

|参照|第一屏行为|本轮可得结论|
|---|---|---|
|历史#26/#28的sp20候选流程|有同意/信息流、能记录触摸；历史细节见看板及相应报告|总集成这两轮达不到该水平；但runtime/shim版本和时序非受控同一变量，本轮未回滚做新A/B，不能直接归因某个合并|
|#23 property-bounds，分散runtime＋sp20派生v4 shim，无metasec target|6/7/6秒a-4 pc0x4000，同样未到同意|与本轮7/7秒同签名，说明当前首阻塞在总集成前已存在|
|#23增加metasec target|82/79/84秒、同意后直接Bionic TLS访问崩溃|不属本轮参数，不拿它冒充可比首屏基线|

同签名基线原始stderr/faultlog/run.sh/device-report已归档 `evidence/prior-bounds/`，来源westlake提交`1dd1ff5`。本轮没有复跑旧构建，因此结论限于历史证据对照；要证明总集成后续路径无回归，需要先有能越过当前前置故障的受控配置或平台修复，再执行本条剩余步骤。

## 对照应用

|应用|真实注入|结果|UI/进程额外观察|
|---|---|---|---:|
|Noice child30897|`i 1119 1840`|Welcome→Design your ideal environment|65.1308s|
|Wikipedia child2188|`i 1149 1867`|All the world's knowledge→Data & Privacy|65.1293s|

前后截图、view tree、actions.jsonl、UI tid、/proc采样均留档；截图已目视核验。两者无Fatal signal、UI返回及本PID cppcrash。Noice既有mainActivityPi NPE两条仍在L591/L617；最终可见页VT在L2202。Wikipedia标题用截图证据，不伪造VT文本行号。这只是启动/翻页烟测，非全功能测试或头条五分钟验收。

## 清理、证据和复验边界

stage前先处理旧测试进程及旧部署：首次shell cat大日志超时，随后改为文件接收/复用本地原始日志，40条关联记录与SHA在cleanup/archives.json（大日志仍保存在VM，不塞入本报告仓库）。只删18个已在#23归档的bounds部署路径，未归档旧目录保留。第一次按exe路径识别未覆盖namespace中的/appspawn-x，补充核对旧PID、exe、启动时间后清理；旧parent的comm为main，不能用comm含appspawn作为唯一判据，验收夹具清理已按exe核对。残留清理有一部分延续到stage后和控制轮间，**不声称首轮启动前已零残留**；因此环境清洁度也限制了新回归归因。本次结束记录appspawn-x/touchfwd/article.news为空，任务child/parent与转发器停止，未加网络规则。

/data从63G/232G到58G/232G（25%），保留本轮部署与日志。全部VM入口使用orb -m a2hlab bash -lc。仅本板stage/启动/验收及授权残留清理，未改runtime/APK/共享out，未触其他板。产品源码零修改；提交内容仅验证报告、操作夹具和证据。

`evidence/results.json`为逐轮可复算数字；`manifest.json`记录证据哈希，原始VM目录 `~/a2hlab/board/5cd1e3dd00000000000000000923012c/verify32/`；夹具在 `~/a2hlab/ws/out-verify32/`。原始流保留空白，不为了diff格式检查改写日志。测试仅做夹具语法检查、哈希/提交对象/gzip往返校验，未重跑与文档验证任务无关的单测。

**R2=partially**：总集成部署、preload、哈希核对和两个对照烟测verified；头条端到端未通过，不能签总集成“无回归”。只commit、不push。ACK(blocked)的解除条件为在授权的可运行配置上补齐同意、WebView、Cronet、≥3标题和i点条目的现场证据；不在本验证任务内擅自修复。

离线复验（不连板）：`python3 benchmark/2026-09-25-integrated-board/verify.py --git`。
