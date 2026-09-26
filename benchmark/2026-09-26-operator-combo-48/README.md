# #48 monitor组合补丁warm终测

**结论：ACK(blocked)，R2=partially。五轮3/5存活240s，三篇不同文章正文确认；另两轮仍SIG11，未达到5/5可靠性交付。**

测试板仅61b0657200000000000000000324012c。独立分支test/monitor-combo-48，基于harness6bde712，npth sigaction工具取自bb6d06e。只commit，不push。

## 配方与边界

现场保留ability38-v7底座、稳定shim85c789f4、mc46 bridge、metasec安全值桩1021a058、tt targets/LD_PRELOAD和map_count1048576。不带#50文件JIT、不带总闸/df拒库。只直接替换实际SOURCE-NATIVE-LOAD路径四库：

|库|完整SHA256|
|---|---|
|libnpth.so|7639af0004a2a0da079e3ad3af339cb3aa341d4a9fe9d4cdce3983db6d80d39e|
|libgodzilla-memsponge.so|2f06633265527e448e9ad1b55f5907358f5872b564000b86736a0ed9e0a664e5|
|libmonitorcollector-lib.so|f3918bdc42b60a19edc3b80c4bd1c1cadc972eba286e5f1b1447505a6bff1793|
|libgodzilla-sysopt.so|c92d0ea5e25e3aa68f9e64f4ad1015d054e783502ed0f614065065084411bb07|

宿主runtime：`/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d`，应用内为`/data/local/tmp/asx`。stage：`/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d`。四库各先备份到`/data/local/tmp/operator45-crashes/combo48-original/<lib>.<old-full-sha>`。原件/候选/patch日志与SHA分别在evidence/deployment、evidence/deployment7639。无重编，无系统分区写入。

npth7639在4f7c上改14处sigaction调用，保留20处old=NULL调用；JNI_OnLoad导出、class-3 ret、两个hook假成功指令均保留，静态六项通过。其他三库patch安装调用数4/1/4，sysopt是4个callsite（两类API），不是两条指令。memsponge/sysopt没有JNI_OnLoad导出，运行时按构造函数加载判断；不宣称不存在的JNI返回码。当前无直接JNI返回值日志，映射+SOURCE-NATIVE-LOAD后无ULE是成功加载的间接证据。

## 方法

warm保留同意，禁两种守护，每轮前确认头条/appspawn为空、MemAvailable>1GiB，起单实例记录PID+birth，计划观察240s（从spawn计，不是文章后240s）。每轮结束无论结果清child和appspawn，核pidof空及内存后再开下一轮。板上另有按PID/birth检查的248s一次性kill定时器；没有自动重启。所有HDC命令有55s以内超时，VM代理也有deadline。

每10s取屏，20/60/190s板上cat完整maps到普通文件再拉取。条目点击只用`uinput -T -d x y -u x y`；先人工看feed截图，避免广告/诱导登录；正文必须人工读图，加行首B47-SLA NewDetail ENTRY及对应RESUMED。数服务端settings JSON不算。图片原始未加工。

崩溃判据合并parent、child Fatal signal、CRASH42 signal=0xb，不能只数Fatal横幅。寄存器及maps能抓到；若mem_open EACCES则不能声称完整回溯。musl文件偏移经PT_LOAD换成ELF虚址，分别统计0xd6e20与npth-worker sigaction0x111974；其他SIG11同样导致可靠性失败，不因偏移不同放过。

旧combo-r1/r2/r3仍用npth4f7c，分别17.418s SIG11、24.415s SIG11、240.002s存活；没有正文验证。它们是被更新指令替代的独立旧队列，绝不并入final五轮。旧r2精确命中musl ELF0xd6e20，旧r1为0xd5e1c。

## 证据复核

VM脚本通过`orb -m a2hlab bash -lc '<cmd>'`运行；五轮命名final-r1…final-r5。review.py核日志/maps，record_visual.py只登记实际读图结果，report.py导出原始证据（大文件gzip），aggregate_final.py只汇总final五轮。`python3 verify.py --git`同时验证manifest原始/压缩SHA与HEAD blob，防止工作树证据冒充已提交证据。

最终数据见evidence/final-acceptance.json；每轮原日志、parent、maps、输入uptime和人工截图记录位于evidence/final-rN/。测试结束保持补丁/同意数据，守护停用，不留交付实例。

## 正式五轮结果（npth7639af00）

|轮次|child/parent|观察秒数|结果|文章|
|---|---|---:|---|---|
|final-r1|13299/13263|240.008|存活，计划清场|央视“假期火车票预售超1.32亿张”，17.059s至RESUMED|
|final-r2|18683/18646|240.005|存活，计划清场|新华社“未来五年，田埂上的新希望”，15.491s|
|final-r3|24183/24140|240.010|存活，计划清场|新华社“心相近…中美人民友好故事”，22.865s|
|final-r4|29677/29650|20.576|SIG11，bd_tracker_w:13|未到正文|
|final-r5|30677/30644|17.458|SIG11，npth-worker|未到正文|

前三轮均先确认真实feed，uinput(380,541)，NewDetail ENTRY及对应RESUMED与正文截图配对。截图：[央视正文](evidence/final-r1/article-body.jpeg)、[新华社农业正文](evidence/final-r2/article-body.jpeg)、[新华社友好故事正文](evidence/final-r3/article-late.jpeg)。第三轮article-body.jpeg仍白壳，只有article-late.jpeg计作通过。本轮验证渲染可读，尚未验证视频播放，点击到RESUMED仍超过2s。

五轮ULE=0、parent exit(1)=0。npth与monitorcollector五轮均有完整有效maps；前三轮四库全映射，第四轮故障时sysopt尚未见映射，第五轮memsponge/sysopt尚未见映射。因此“每轮四库全部映射”没有全过，不能用无ULE补足未加载证据。前三轮另以/proc/PID/root/data/local/tmp/asx核实际四库SHA。r1/r2有非致命Chrome_ProcessLauncherThread缺child service异常，原栈保留；r3没有该未捕获异常。

### 残留故障交claude-3

两次均为r3类musl ELF PC0xd6e20，LR0xd6a18，signal11、fault0；原r5的npth-worker sigaction ELF0x111974在本次未观察到，但不能据五轮宣称根治。final-r5虽名为第五轮且线程npth-worker，其故障是mallocng而非sigaction，必须按PC分列。

- final-r4：event-73ed-7628-1，TID30248，bd_tracker_w:13，3767行故障maps；npth、monitorcollector、memsponge及jato已映射，sysopt未见。
- final-r5：event-77d5-78ec-1，npth-worker；故障maps含npth、monitorcollector、bytehook/shadowhook及npth backtrace组件，**未见memsponge/sysopt/jato**。这不支持“仅凭剩余库名单就将jato定为唯一真凶”；snapshot不能排除更早已卸载库，仍需实际写坏来源证据。

每轮crash-analysis.json/crash-events.json、faults原始寄存器/maps与PC/LR反汇编齐。两次mem_open EACCES，未得完整栈。无新增jato patch。四库组合不足以保证warm稳定是已确认反例；不把受害线程当破坏源。

结束时头条/appspawn为空，旧守护stop与fresh守护stop均在且无lock，map_count1048576，现场保持85c789f4+7639af00+三库patch及同意数据。最后检查见evidence/final-check/board-state.txt。
