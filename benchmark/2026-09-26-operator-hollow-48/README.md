# #48 npth hollow stub warm五轮

**ACK(blocked)，R2=partially：4/5原PID存活240s；第5轮167.546s因ArticleInflowActivity负布局宽度异常exit(1)。本轮5/5未观察到SIG11，目标mallocng/sigaction签名均未出现，但未达5/5稳定交付。**

板61b0657200000000000000000324012c；独立分支test/npth-hollow-48基于claude-3的b21b284，只commit不push。相对ef78d68组合，仅替换libnpth7639af00为hollow9966e296，保留shim85c789f4、memsponge2f066332、monitorcollector f3918bdc、sysopt c92d0ea5，以及mc46 bridge、metasec1021a058、tt targets/LD_PRELOAD、map_count1048576。无#50文件JIT，无守护，同意数据保持warm。

## 新稳定基线候选（外环采认，待Layout修复）

采用shim85c789f4 + npth hollow9966e296 + memsponge2f066332 + monitorcollector f3918bdc + sysopt c92d0ea5，完整部署参数与SHA见下节及evidence/deployment。外环已独立复核本次五轮中mallocng/sigaction SIG11未出现、4/5存活240s及文章可读，采认为后续修复的基线候选。

候选边界：ArticleInflowActivity负宽度Layout -79导致第五轮exit(1)，尚未达到5/5；五轮work_thread SIGABRT横幅仍在，来源未定。继续保留现有同意数据、map_count1048576，禁守护，不恢复旧npth或叠JIT；等待单独的Layout修法验证。仅commit，不push。

## 部署

`stub/build_npth_stub.sh`在a2hlab VM单库重建，SHA精确为`9966e2966057c4d7d31f81232decf58da046898b9a2be900df675d44d016a107`，静态8项通过。app内实际SOURCE-NATIVE-LOAD位置为`/data/local/tmp/asx/lib/arm64-v8a/libnpth.so`，宿主runtime为`/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d`。

原件备份：`/data/local/tmp/operator45-crashes/hollow48-original/libnpth.so.7639af0004a2a0da079e3ad3af339cb3aa341d4a9fe9d4cdce3983db6d80d39e`。证据deployment内保留原件、重建stub、完整SHA、静态断言及部署前后状态。后三库原备份在前一combo48任务，不重新替换它们。

## 方法与判据

每轮单child PID+birth，守护停用；起前pidof头条/appspawn空及MemAvailable>1GiB，warm保留数据；计划240s，结束先kill原实例/parent、核pidof空/内存，再下一轮。另有248s按PID+birth的一次性kill期限，无自动重启。HDC命令≤55s且VM代理有超时。所有VM命令使用`orb -m a2hlab bash -lc`。

实际读图确认无遮挡feed后只用`uinput -T -d x y -u x y`点击文章。文章必须行首NewDetail ENTRY+对应RESUMED，以及实际正文截图；白壳、feed、登录页不计。240s从spawn起算，不是文章后240s。无人工/自动i/c注入。

20/60/190s板上cat完整maps到文件再pull，另采线程comm。每轮核四库SHA；活体/proc/PID/root进一步核实际挂载路径。npth成功加载判据为maps+SOURCE-NATIVE-LOAD、无ULE；静态81项注册覆盖不等于运行时81个native全调用成功。JNI_OnLoad未打印返回码且清除注册异常，故不伪造直接返回值证据。memsponge/sysopt无JNI_OnLoad，以构造函数加载计。

崩溃判断覆盖parent、child横幅及被动CRASH42记录器；检查mallocng ELF0xd6e20和sigaction0x111974，其他SIG11同样失败。若发生故障，寄存器/maps可取，mem_open EACCES时没有完整回溯。线程列表无npth-worker只代表采样时未见。

## 复核

VM证据根`~/a2hlab/board/61b0657200000000000000000324012c/hollow48`，与旧combo48隔离；正式轮次final-r1…5。review.py核日志/maps，record_visual.py登记已看图结果，report.py压缩导出原证据，aggregate_final.py只汇总本目录五轮。`python3 verify.py --git`核manifest、raw/gzip SHA及HEAD blobs。不以旧组合结果补充本次轮次。

## 五轮结果

|轮次|child/parent|观察秒数|存活/退出|文章证据|
|---|---|---:|---|---|
|final-r1|22909/22876|240.005|存活，计划清场|央视访谈谭森，段落正文+配图，22.222s至NewDetail RESUMED|
|final-r2|28371/28347|240.009|存活，计划清场|新华社月满中秋，NewDetail 17.021s；标题+图片，未取正文文字，独立列出|
|final-r3|2103/2066|240.003|存活，计划清场|新华社心相近友好故事，段落正文+配图，13.389s|
|final-r4|7790/7754|240.002|存活，计划清场|央视中美关系新定位，长图正文，14.222s；物理上滑另图|
|final-r5|13042/13011|167.546|主线程Layout -79异常，parent exit(1)|普通卡片→ArticleInflowActivity，无NewDetail/正文成功|

[r1正文](evidence/final-r1/article-late.jpeg)、[r3正文](evidence/final-r3/article-body.jpeg)、[r4长图正文](evidence/final-r4/article-body.jpeg)、[r4上滑后](evidence/final-r4/article-scrolled.jpeg)。三篇内容=两篇段落正文+一篇带文字长图；r2详情图片不计入此数。所有feed-ready.jpeg先实际目视确认，无登录覆盖。r5点击普通卡片也是真实uinput，实际路由为ArticleInflowActivity；不能因不同页面退出就删除这轮或换样本。

五轮均四库映射、npth stub实际挂载SHA匹配、ULE=0。所有SIG11横幅及CRASH42 signal11快照为0，故本观察窗内mallocng0xd6e20/sigaction0x111974均未见，不推论永不复发。**五轮均仍有一条work_thread Fatal signal 6 (SIGABRT)横幅**；前四轮其后仍存活到240s，r5的最终进程状态是exit(1)。横幅没有完整backtrace，不能据此归因某库或称“所有信号0”。

五轮20/60s及前四轮190s线程采样仍有npth-worker，故“stub不导入pthread_create”不等于“进程没有同名线程”；可能来自Java/其他组件，未取其创建栈，不定来源。源码不产生worker、静态导入与真正线程名存续是不同层面。不能把同名线程存在误判为真实libnpth尚在。

## 第五轮退出证据

真实uinput(380,750) uptime131934.08，随后行首ENTRY为`com.bytedance.ugc.forum.innerfeed.ArticleInflowActivity`。main抛`java.lang.IllegalArgumentException: Layout: -79 < 0`；调用链：`android.text.Layout.<init> → StaticLayout.Builder.build → TitleResource.h → InnerFlowCardProcessor.c → NormalCardSectionController → LiveData/Fragment.performStart → ArticleInflowActivity.onStart → TransactionExecutor → ActivityThread.main`。`[CM-EXIT] launchActivityThread RETURNED — child_main:_exit(1)`与parent`child 13042 exited(1)`互证。

[确切Java栈](evidence/final-r5/main-exception-excerpt.txt)，[独立SIGABRT横幅](evidence/final-r5/sigabrt-excerpt.txt)，完整child/parent原日志同目录。SIGABRT发生在较早初始化窗，不能把它直接当作167.5s退出原因。负宽度从何而来尚未查明，也没有证据说这是npth stub副作用；应独立调查该文章页的测量/布局参数。

最终板上头条/appspawn为空，守护stop与无lock确认，map_count1048576；stub与后三库patch、shim85及同意数据留存。未部署额外jato或重启守护。
