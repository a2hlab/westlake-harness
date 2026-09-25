# 崩溃普查：离线分析与 VM 夹具

板 5cd1e3dd 仍由 claude-2 执行 #44/M3.crux。本阶段没有执行 hdc，没有修改共享源码、共享 out 或板子。独立输出 `~/a2hlab/ws/out-crash42/`。**设备原因尚未最终确认，完整栈恢复与六轮普查尚未完成。**

## ① 为什么缺证据：目前能确定到哪一步

`scripts/audit_previous.py` 重读九轮正式 #42：九轮 parent 均有 OH special-handler chain 注册记录，九轮最终 SIG11，初查及迟到复查均没有 cppcrash。可重算原文、行号及哈希在 `evidence/previous-formal.json`。

| 环节 | 已证实 | 尚不能下的结论 / 下一步 |
|---|---|---|
| ART stderr | 部署同哈希 libart 的三个 DumpNativeStack overload 都是 `ret`，因而 Backtrace 标题不输出帧 | 不能把空标题当栈为空；与 cppcrash 缺失是两个问题 |
| OH LiteDump 配额 | 冻结的 OH 6.1 源码按 UID 60次/24h 限制；pipe 是180次；不是零点重置。宿主 UID 不在 ArkWeb UID 折叠范围 | 未取得设备拒绝日志，不能认定配额已满。新轮完整 hilog 需找 `litedump service is limited for uid` / `litedump pipe service is limited for uid` |
| 去重/首次故障 | DFX `g_prevHandledSignal` 使同一进程只有第一次非诊断信号进入 dump；此后即使出现不同线程/信号也不再 dump | work_thread 重投或较早事件可能先消耗机会，但正式轮缺首次 DFX 日志，不能证明顺序 |
| 路径/保留 | 已查 `/data/log/faultlog` 整树，后补查仍无；空间155GB。上游 JSON 配置管保留数量/大小/时间，不管 UID 请求计数 | 设备实际配置/版本、曾生成后被删尚未排除。新轮必须在启动前收日志并即时拷出报告 |
| parent | SIGCHLD 后 `waitpid(WNOHANG)`，只记录已结束子进程，无先杀活进程逻辑 | 不证明所有 dumper 子进程/异步写入无竞争；要把 DFX 启停、pipe 和 parent reap 放在同一时间线 |
| sigchain | 九轮 parent 明确注册 OH special-handler chain；对应源码不会启动 legacy reassert 线程 | npth 的普通 handler 与 OH special chain 的实际流转须从原始信号观察确定；不能仅由 callback 安装日志判其吞掉报告 |
| npth | #46 已有 work_thread 经 npth syscall 重投的证据；正式轮 ART stderr 的空栈另有空实现原因 | 不把重投当原发故障，不据此归因某个 SDK；完整 native 日志用 #44 liblog 补齐 |

上游 `LiteCrashHandler` 先 RequestLimitedProcessDump，再申请 PIPE_WRITE 并写 request/收集的内存/maps。pipe 申请失败会打印 `lite dump failed to request pipe`；正式证据没有同时段未筛选 hilog。旧 `formal-first-hilog.txt` 只有执行 grep 的 HDC 命令行，不能据此排除系统 handler、限额或管道错误。

## ② 已准备的诊断代码

优先尝试系统链，**不预先重启 faultloggerd、不变更应用 UID、不改变系统配置**。实际配额/服务状态取证后再决定系统侧处理。下面的候选仅为系统机制不可用时的备用，并非默认部署配置。

`native/crash_snapshot.c` 是被动记录函数，不安装 handler，也不调用 raise/sigaction。初始化在子进程既有 `SigchainStartReassert` 入口进行，通过 `WESTLAKE_CRASH42_DIR` 指定已有的、应用可写的私有目录。未设置时不捕获。

- 记录 siginfo/ucontext 原始字节、单调时钟、PID/TID/comm、PC/SP/FP/LR、完整 maps，以及 SP 到其可读 VMA 末尾的栈字节（最多64MiB）。读取失败输出 errno，截断与完成标记明确，不填零冒充现场。
- 另外输出最多256步、地址范围与前进方向均校验的 FP 链。使用 `/proc/self/mem` pread，不直接解引用可能损坏的 FP；没有 malloc、stdio、dladdr、互斥锁。并发/重入事件输出 skipped，不伪称已捕获。
- 原始栈快照用于离线展开，**不是已经成功的完整 DWARF 回溯**。无 FP、坏栈、JIT 元数据缺失、不可读内存、上限截断、同时发生多个信号均可能限制回溯；maps/stack 也不是所有线程停机后的原子快照。需要板上受控崩溃和真实 RenderThread 栈验证。
- 覆盖边界：只观察经过现有 ART special chain 的信号，适合优先追 RenderThread SIGSEGV；没有为 SIGABRT 等另装 handler，不能据候选没有记录就断言它们没发生。系统 hilog、#44 native 日志与 parent 结局仍需联合采集。
- `prepare_sigchain.py` 生成私有副本：保留原 callback mask/flags 与 claim 结果，最后一个 ART callback 返回 false 后捕获，再返回 false 让原 OH 链继续。移除 callback 时映射回注册的 wrapper，不增加 OH special-handler 槽位。不改 app handler，不抑制或伪造退出信号。捕获事件表示“ART 未处理”，不自动等同最终致命事件；还需与系统报告/parent 对齐。
- 初始化、磁盘写入与栈复制有诊断开销，不将该候选用于性能结论。正式六轮如采用它，表中明确标 diagnostic；原基线+#44 logger 与诊断候选的数据分列。

### 最小构建与验证

`build_vm.sh` 只编译记录器、受控崩溃夹具及 sigchain 包装测试。`relink_art.py` 核454个原对象哈希，先重链原库，得到与 #42 **逐字节相同**的 `009a08fb…c8bbc`；然后只替换 `sigchain/sigchain.o`，加 `crash_snapshot.o`，重链诊断 libart。

候选 `~/a2hlab/ws/out-crash42/recorder/art/libart.so` SHA256：
`7d5a3b2ab1a00d0d0fe0dfd3398d2c40a7e388b138bc55bdf6f69096b6f43bfe`。

注意：额外生成的 `recorder/libsigchain.so` 只是独立链接检查产物，**不能直接覆盖部署**；#42 的 sigchain 静态链接在 libart 内，设备候选是上述重链 libart。

VM 已通过：

- 有/无观察器受控 SIGSEGV 对照，errno/siginfo/ucontext 字节不变，si_code 与最终 WTERMSIG 相同。
- 原始上下文/maps/栈保存，测试现场 SP→VMA末尾字节数匹配、完成标记成立。
- OH API mock 测试：处理顺序、mask/flags、claim、移除/重注册；ART已处理不写记录，全部拒绝只写一次。
- arm64 OH SDK 编译通过；备用 sigchain 独立库只依赖 libc。

**未验证**：真实 OH signal chain 并发/重入压力、应用沙箱中 self/mem 可读性、真实 RenderThread 的完整 DWARF 展开、设备稳定性。受控测试初稿把 PROT_NONE 必定返回 SEGV_ACCERR 当假设，VM实际为SEGV_MAPERR；现按有/无观察器相同 si_code 检验，不假造ACCERR。一次共享文件挂载同步导致编译读到半份文件，已改为 tar 冻结 VM 私有夹具再编译。

## 上板移交后的脚本

所有命令均在 VM 通过 `orb -m a2hlab bash -lc` 执行，必须等外环释放后才运行带 `--board-released` 的命令。脚本固定5cd1e3dd，启动前检查无其他 dalvikvm/linker64/头条/appspawn；不动 bionic43。

1. `prepare_stage.py --board-released`：私有复制 #42 baseline stage，只覆盖 #44 liblog，核所有文件哈希并跑 preload。若系统机制无解需用备用候选，再单独 `--diagnostic` 建另一 stage。
2. `run_census.py idle-1 --board-released --framework-report <私有stage报告> --reference <#38 idle-a1/launch-config.json>`。新应用数据，开启 `WESTLAKE_SOURCE_LOG_STDERR=1`，完整 hilog 自启动前开始。截图确认同意后写其提示的 `consent-N-xy` 文件，只点同意，不点条目。
3. 最后同意后90s或真实退出，保存5s间隔 maps、1s存活界限、stderr、parent、系统报告；延迟3/10s再收报告，最后刷新stderr以防漏掉末尾信号。按 PID+starttime 清自己进程。夹具错误及同意前退出另列，不用作有效90s样本。
4. `idle-2` 至至少 `idle-6`，逐轮先互斥检查。重点查 RenderThread 的原始 PC/LR/完整栈与 WebView ELF 的 build-id/sha；`+0x3e026f0` 是外环现场待匹配偏移，不能不核 ELF 就与本板早期 `+0x26016f0` 当作同一位置。若90s空闲协议没出现该故障，明确报告未复现；不能暗中增加文章点击后仍标空闲基线。

设备脚本目前只做语法检查，**尚未运行/尚未宣称可上板验收通过**。下一步受控验证会据设备实情修正脚本，然后才执行正式六轮、出表交 #46。
