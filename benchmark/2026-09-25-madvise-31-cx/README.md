# #31 ART 文件预读种子：板 5cd1e3dd 前后测量

本轮完成了最小配置接入和启动测量，**目前没有证据把它采认为本板的提速修复**。不把 hanbin 的 7.60→4.58 秒当作 westlake 实测，不宣称原 #31 的物理点击 <2 秒已完成。

## 改动与构建

确切属性是 `dalvik.vm.madvise.{vdexfile,odexfile,artfile}.size`，单位为字节，不是布尔 true。hanbin 源码为 vdex/odex `104857600`、art `4294967295`。ART 15 的内部默认值为 0，解析三个 `-XMadviseWillNeed*FileSize` 参数；本项目 AppSpawnX 自己构造 VM 参数，不经过 AOSP AndroidRuntime 的属性翻译路径，所以仅加 Java SystemProperties fallback 不足以启用 ART 预读。原文和本地 ART 读取位置见 [source-evidence.txt](source-evidence.txt)。

现场已有 `fix/madvise-seeds-31@3d620a1` 种子提交，本轮以其为输入另开 `westlake-madvise31-cx` / `fix/madvise-31-cx`，追加 **ef0db66**：把预读选项移出 forced-JIT 条件，按统一运行时默认配置接入，与 JIT 开关无关；未修改属性 provider、APK 或 SDK。新分支相对 #14 基线只有 appspawnx_runtime.cpp 的八行新增。原分支/原 out-madvise31 未改动。

`out-madvise31-cx` 只编 **1 个 TU**（appspawnx_runtime.cpp），重链 **1 个 appspawn-x**；构建命令见 evidence/build/commands.json。其余五个对象及依赖沿用 out-integrate，未跑 native-runtime 全链、未改共享 out。候选 SHA256 `ed3274109d3baca8b5b520338524fb7aaa85e3fd7d0657c361312d635dc1c279`；基线 `a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c`。framework stage 306 文件仅 appspawn-x 不同；实际预加载 PASS，日志明确列出 ART 收到三个 VM 选项。

## 测量口径

- 独占板 `5cd1e3dd00000000000000000923012c`；#14 framework + out-sp20 WebView；native targets为libvision_core、libc++_shared、libsscronet，net target为libsscronet；WL_TOUCH_TRACE=1各轮一致。未混入 #23、all0925 或 #30 targets。
- 每轮全新部署与应用数据，未重启/清内核页缓存；这是新应用进程启动，不是严格冷存储实验。网络内容可变，结果仅代表本次条件。
- 夹具 `measure.py … --p2-wait 120` 持续观察到120秒或进程/UI提前退出；底层probe本身不带该参数，由夹具实现长窗，未使用board-loop早期P2判负。
- t0是板上紧邻host_spawn请求之前的/proc/uptime，非宿主墙钟。D态统一统计 `[t0,t0+23s]`，trace提前开启、约30秒停止。AppSpawnX的进程主线程与Java UI线程不是同一TID；UI TID用窗口创建的WESTLAKE-GONW日志对应，两个线程分别统计。
- D区间从sched_switch的prev_state=D到sched_wakeup，**不包括唤醒后的CPU排队**。完整有效样本的trace均覆盖23秒；无丢事件（entries-in-buffer=entries-written），无用switch-in替代wakeup的回退。D态不是纯磁盘I/O时间。
- 首屏为实际截图首次观测到应用信息流；同时保存前一张host截图及两次截图命令的板端时间边界，不声称得到vsync/首帧回调的毫秒级时间。VT中发现同意后注入c命令，与物理点击延迟验收不同。完整可读文章页不在本轮范围。
- baseline-1是预采样：第30秒同步导出大trace阻塞观察者，不能用于首屏比较。其前23秒D态仍可复算，但不合并到正式对照均值。之后所有轮次改为约30秒只停trace，120秒观察结束后才导出。导出期间进程继续运行，因此终态日志可能含观察窗后的异常，不能把导出结束时刻当作120秒首屏指标。

## 逐轮结果

|轮次|child / UI TID|23秒UI D态|最长D区间|进程主线程D态|首次信息流截图采集区间|
|---|---|---:|---:|---:|---|
|baseline-1（预采样）|16274 / 16291|5.511504s|12.086ms|0.005748s|不参与首屏比较|
|baseline-2|21351 / 21371|4.509239s|11.907ms|0.005520s|65.88–66.54s|
|candidate-1|28214 / 28231|5.909088s|30.581ms|0.003877s|70.49–71.22s|
|baseline-3|3585 / 未确证|—（窗口不足）|—|不比较|未出现，11s早退|
|candidate-2|7918 / 7945|4.462262s|15.285ms|0.002743s|69.41–70.05s|

候选两次D态为5.909/4.462秒，未重复得到低于有效基线4.509秒的明确收益；预采样本身5.512秒，也显示轮间方差。信息流首次正截图候选约70–71秒、基线约66秒；样本少且在线内容/页缓存未严格控制，不能宣称改善，也不足以精确归因变慢。保守的“上次host到首次信息流”外包区间为基线59.07–66.54秒、候选65.42–71.22/63.22–70.05秒；不是精确首帧回调时间。数值可由screen-times.json与events.json重算。

截图：[基线首屏](evidence/baseline-2/frame-0064.76.jpeg)、[候选1首屏](evidence/candidate-1/frame-0069.27.jpeg)、[候选2首屏](evidence/candidate-2/frame-0068.31.jpeg)。三者均是真实信息流，灰图是固定底座未加#30 targets的已知行为。

异常未省略：baseline-3的cppcrash记录11s、a-5 SIGABRT、ART/WebView plat-support栈，stderr没有`Fatal signal`行但确实崩溃，不能仅grep判存活。baseline-2 / candidate-1 / candidate-2各有一条work_thread SIGABRT日志（L17544/L17613/L16116）；候选最终日志另有null Looper的INITCHILD-FAIL（L24060/L27266，X.DEv→X.DPS→X.DPb）。候选最后正截图仍是信息流，最终日志在后续trace导出后才收集，未确定UI退出的精确时间；不宣称整个采集期间UI稳定。Chrome child-service元数据异常、metasec app_lib errno13、部分Fresco/gifimage缺符号均留存，未在此任务修改。

结论是**配置接入可用，提速收益未证实**；本轮停止继续加大预读或追修SDK/线程故障。原#31点击<2秒不在此证据中成立。

## 证据与边界

全量trace原件在VM `~/a2hlab/board/5cd1e3dd00000000000000000923012c/madvise31cx/`，数百MB/轮。提交保留原件路径/字节数/SHA256，以及两目标线程的原始调度行（headers、首尾事件、switch/wakeup，未改写行内容）；从完整trace和精简trace分别复算D区间逐项相等。另附原始截图、VT、stderr、parent日志、faultlog、构建/部署报告。首屏人工查看记录在visual-review.json。

宿主已知答案测试69项OK（2 skipped）；D态分析器用合成时间线核过“唤醒到重新上CPU”的排队时间不计入D态。离线复验：`python3 benchmark/2026-09-25-madvise-31-cx/verify.py --git`。

只commit、不push。源码候选和报告均独立分支；未将候选替换到共享底座。R2：配置接入和有完整窗口的测量verified；收益与原#31的<2秒目标未证实，整体partially。

移植需3d620a1+ef0db66两提交，或取附带相对5f9a435的madvise-net.patch；不能只挑ef0db66。收尾已清理测试子进程/父进程与touchfwd，tracing_on=0；板已向#39释放。部署目录和全量原件保留，/data占用71G/232G。五轮WebView/APK输入一致，source_files差异仅候选的appspawn-x，最后一次板上SHA256匹配候选；见evidence/provenance.json与evidence/cleanup.json。
