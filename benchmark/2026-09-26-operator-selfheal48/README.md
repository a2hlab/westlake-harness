# #48 路 B：原 sscronet + 板上自愈守护

部署目标板61b0657200000000000000000324012c。分支deploy/operator-selfheal-48，独立worktree，以01afdab为基线；仅commit不push。验收结果与限制在本文末尾，不以“生产级”名称代替实测。

## 配置选择

保留原sscronet38f0dd42、monitorcollector8c97ef7c、npth9966e296、metasec1021a058、memsponge2f066332、sysoptc92d0ea5、shim85c789f4、bridge d4fae8e5、clamp BCP jar ea5d8b27/配套oat247 boot、hollow引擎fbb761a0/34378f5c、map_count1048576。未加速度AOT/JIT。八库完整SHA在install/baseline-hashes和活体capture/native-identity中。

理由：hollow引擎历史5轮3轮360s并读过两类文章；去引擎的clamp样本亦3/5且有SQLite/mallocng故障，缺少证明去引擎更稳的对照。最近原sscronet+r5neuter warm对照1/3存活，另2/3mallocng。保留可读配方，使用fresh恢复，不声称这就是全局最稳。control-r1是warm首轮，不是fresh稳定证据。

## 守护机制

板上 `/data/local/tmp/operator45/selfheal48/watchdog.sh`，所有VM操作通过`orb -m a2hlab bash -lc`。旧operator45及fresh48守护stop保持。

- mkdir独占锁，owner PID/birth识别，只有owner已死才可接管过期锁。
- 3秒循环检测原PID/birth；额外app/parent才触发清场，允许启动改名前短暂pidof=0。只把当前进程时间窗口内的记录器SIG11视为致命，良性SIGABRT不触发恢复。
- 每次启动前清理明确child/parent及pidof找到的剩余头条/appspawn，确认空PID和MemAvailable>1GiB才启动；清理不成停止并标记BLOCKED，不继续堆实例。
- fresh前将原同意profile保存到runtime/operator-selfheal-original；后续只轮换operator-selfheal-previous，不重复堆积数据副本。启动前设置map_count、唤醒、前台宿主。
- 启动阶段用本目录screen-gate（固定1200×1920，10种实拍正负样本通过）识别真实隐私框/登录页再uinput同意或关闭；连续两次feed识别才READY。180s仍未READY则清理重试，连续3次失败增加30s退避。
- READY后完全不触摸、不抓屏、不抢焦点，仅检查进程和记录内存/计数。operator主动进入登录页也不会被自动关闭。
- 每次退出清场后、下次启动前，将child.stderr/parent.log/CRASH42/faultlog/cppcrash拷到`/data/local/tmp/operator45-crashes/selfheal-序号-时间/`，INDEX记录退出原因、存活秒、清理/孤儿数。归档不能替代完整native栈，EACCES限制照录。

## 操作

停止自动重启（当前app保留）：`touch /data/local/tmp/operator45/selfheal48/stop`。待events出现STOPPED/lock消失后，可用本目录`control.py cleanup`彻底清掉实例。不得只kill guardian后立刻另起一份。

启动：`control.py start`要求现场无app/parent且无活锁。常用`control.py status`、`shot 标签`、`input x y`、`swipe`；`kill-test`/`crash-test`只针对当前PID/birth记录并发送SIGKILL/SIGSEGV，属于人工恢复测试，不能算自然崩溃。

## 实测中的修正

初版seq1–4把启动改名前的pidof=0误判为异常，并只按进程名清理，留下短时孤儿。已停守护显式清场后修正；这些是守护缺陷触发的人工中止，不计app自发崩溃。修正版从seq5起，清场涵盖已知child/parent，PID/birth承重判断，app/parent数量大于1才认额外实例。



第三版修正：seq6实际出现无遮挡feed，但旧像素规则要求内容区y=1800为白色，视频封面占满此处时误判unknown。停守护保留实例取证后改为检查固定底栏y=1900；10个实拍样本（同意/登录/feed/遮罩/文章）板上通过。seq6不计完整自动READY通过。第三版watchdog 8023c6b6、screen-gate 808f58a1，从seq7起重新测；RSS解析已兼容制表符。旧版metrics空RSS不作为0或有效测量。

复现部署：先在VM执行`bash scripts/build_gate.sh`（只编独立识屏小程序，不编runtime），然后停止旧守护并清空单实例，再`python3 scripts/install.py`、`python3 scripts/control.py start`。`test_gate.py`在板上核实正负样本；Mac sips仅转PNG输入，不改截图内容。独占锁实证：活守护期间第二份执行返回2且未新建实例。


## 可用性实证与边界

seq5在同一原PID3825/birth15862152中，真实uinput先点普通信息流条目(380,1510)，得到ArticleInflow ENTRY/RESUMED 158843005；点击159012.18s的置顶条目(380,367)，得到NewDetail ENTRY/RESUMED 159019406。截图分别`evidence/validation/inflow5-later.jpeg`（段落+配图）、`newdetail5-later.jpeg`（标题+正文长图）；早期`*-body`占位截图不计成功。原实例活702s后按测试计划kill，非自然崩溃。两路可读证明不等于消除既有间歇mallocng。

自动恢复使用全新profile，会失去该次会话的登录/浏览数据；原同意profile单独备份保留。当前未承诺保存operator登录状态。固定分辨率像素识别只对已有正负样本验证，不是任意App版本/OCR通用识别；未识别页面不盲点。无ANR承诺，当前监控死亡及记录器SIG11。崩溃归档保留供诊断，尚无无限期运行/磁盘保留策略压力测试，不将有限实测写成生产可靠性证明。

SIGABRT/work_thread横幅与真实退出分列，不能报全信号0；手动SIGSEGV会自然出现在记录器，不算应用自发SIG11。`cleaned ppid1`包含预期脱离会话的appspawn父进程，不能直接等同应用孤儿数；以应用PPid指向当前parent及进程数取证。metrics的MemAvailable含可回收页，不把它写成free物理内存。

## 本次结果：ACK(blocked)，R2=partially

实例可试用且自动恢复已证实；约30s恢复目标未达，不能标done。最终版两次完整自动恢复（无手动同意/导航）：100.89s、101.41s（READY秒级采样，不是精确首像素时间）。瓶颈主要在fresh到同意前约72–82s，未擅自加入AOT/JIT。

| 序号 / 版本 | PID | 观察/结束 | 正文 | 恢复结论 |
|---|---:|---|---|---|
| 5 / rev2 |3825|702s后主动SIGKILL|ArticleInflow段落/配图 + NewDetail长图|首启101s；随后seq6门控误判，首次恢复不算全通过|
| 6 / rev2 |16928|保留存活取证后人工停守护/清场|未点文章|真feed已恢复但像素规则误判unknown，修复后重测|
| 7 / rev3 |24655|151s后主动SIGKILL|未点文章|首启119s；seq8在100.89s自动READY真feed|
| 8 / rev3 |28298|119s后主动SIGSEGV|未点文章|seq9在101.41s自动READY真feed；parent signal11与CRASH42归档齐|
| 9 / rev3 |31338|最终取证约286s存活，继续常驻|恢复后NewDetail段落+配图|回无遮挡feed交operator试用|

首版seq1–4错误中止全部保留，不能删掉重凑成功率。rev3两次恢复不是无守护可靠性N轮，不证明自然崩溃根治。seq5/9 ULE、Layout:-79、主线程throw exit1均0；仍各有work_thread SIGABRT横幅，不报全信号0。SIGSEGV人工测试确有event-6e8a-6e8a-1与parent `killed by signal 11`，不伪装成自然堆崩；守护此次走进程死亡分支，未强称“记录器发现仍活进程SIG11分支”已动态覆盖。

无孤儿证据：rev3启动前app/parent均0；启动稳定后各1，应用PPid均指向当前parent，独占锁拒第二守护(rc2)。seq7/8/9就绪审计RSS约900668/836092/824644KiB；下次启动前MemAvailable5873176/5848392/5811716KiB，差约60MiB，不是严格恒定，但没有旧实例累积或6.8G占满现象。只覆盖这次有限重启窗口，不承诺长期无增长。

最终活体八库SHA、maps inode一致（capture-final/native-identity.txt + live.maps.gz）；seq5双文章实例亦一致。clamp/boot/shim等部署前完整SHA核对在install/baseline-hashes.txt。配置未叠R1GUARD、未叠速度层。

## 现场交接

- app PID31338、parent31309、守护24564，seq9（后续自愈PID会变，以instance.txt为准）。
- stage `/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d`。
- runtime `/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d`。
- 当前stderr为runtime下`private-tmp/adapter_child_31338.stderr`；动态指针`/data/local/tmp/operator45/child.stderr.path`。
- guardian `/data/local/tmp/operator45/selfheal48/watchdog.sh`，日志events.log/metrics.log/guardian.log，动态PID在instance.txt。
- 停守护：板上`touch /data/local/tmp/operator45/selfheal48/stop`，等待STOPPED/lock消失；app保留。要彻底停app，再用本任务`control.py cleanup`。原两个守护stop始终存在。
- archive `/data/local/tmp/operator45-crashes/selfheal-<seq>-<time>/`与INDEX；原同意数据runtime/operator-selfheal-original，未删除。
- 截图：`evidence/validation/inflow5-later.jpeg`、`newdetail5-later.jpeg`、`recovered9-later.jpeg`、`operator-final-feed.jpeg`；两次完整恢复feed为`recovery2-feed.jpeg`、`recovery3-feed.jpeg`。
