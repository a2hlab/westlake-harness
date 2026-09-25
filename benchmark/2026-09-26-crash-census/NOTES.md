# 崩溃取证分析（进行中，未上板普查）

分支 analysis/crash-census-42，基于 #42 b3245a4。板暂归 #44，当前只做离线读源。后续普查基线加 #44 liblog 和 WESTLAKE_SOURCE_LOG_STDERR=1。

## 当前证据与待证事项

- parent spawn_server.cpp:27–65 只在 SIGCHLD 后 waitpid(WNOHANG) 回收已退出子进程，打印 WTERMSIG；没有先杀再回收的逻辑。不能凭此排除所有父子交互，但不是直接杀掉活跃 dump 的代码。
- 上游 OH 6.1 Release faultloggerd 已冻结 3adedd38fffbda1b5a47f6e70f15be2923dac157：services/fault_logger_service.cpp:56–60 非测试 LITE_DUMP_LIMIT_ONE_DAY=60；LiteProcDumperService::Filter:625–632 按 GetRealUid 累计，24h延迟清空，不是零点清空。LiteProcDumperPipeService 同样累计3倍限额。超过时日志为 litedump service is limited for uid。这是强候选，尚未比对板上二进制和实时日志。
- interfaces/innerkits/signal_handler/dfx_signal_handler.c:319–370 用 g_prevHandledSignal 保证同一进程非dump故障只处理一次；NoNewPriv进程走 DumpPrviRequest/LiteCrashHandler。因此多信号链可能只有首次系统dump，即使配额充足也不保证后续第二故障有报告。
- 既有 ASX_CHILD_FATAL_SIGNAL_DIAG 不适用“只记录”要求：普通action会signal(SIG_DFL)+raise，special observer中有dladdr以及未校验FP直接解引用。不开此开关。
- ART build 的 stubs/sigchain_musl.cc 在 OH special-handler API 存在时直接注册ART且不启reassert线程；源码上不能把“reassert”启动提示直接等同于实际2ms线程运行。需以部署binary/hash/日志核对实际路线。
- **stderr 空 Backtrace 已由部署同哈希二进制坐实**：`out/native-runtime/libart.so` SHA256=`009a08fb8282b4ed8b857eaf014038adb93bb5cac0daa5d32ab89a13f29c8bbc`，与 #42 framework-baseline/device-report.json 一致。三个 `art::DumpNativeStack` overload 位于 `0xed5a50/54/58`，均仅一条 `ret`，证据 `evidence/libart-empty-stack.txt`。`runtime_common.h` 的 Backtrace::Dump 调用该函数；`art-build/stubs/link_stubs_arm64.cc:677–685` 有相应空实现。因此标题后没有帧不表示实际栈为空。这独立于 cppcrash 缺失原因，不能混为同一结论。
- 系统 JSON 配置 `fault_logger_config.cpp` 管文件大小、保存数量与过期；已查的 UID 次数限额是编译常量，不是这个 JSON 的配置字段。改文件保存数量不能清零 UID 请求计数。GetRealUid 只折叠 1000001–1099999 的 ArkWeb UID；宿主 UID 20010053 不在其中。

## ② 取证方案与验收顺序

1. #44 明示释放后，先确认进程互斥，冻结 liblog 哈希，自己的 runtime 副本替换 liblog 并设置 `WESTLAKE_SOURCE_LOG_STDERR=1`。保存完整 hilog，不以筛选后空输出判定“系统未处理”。
2. 捕获 DFX handler 的原始 signo/si_code/pid/tid、UID 配额拒绝、lite pipe 失败，以及 parent reap 时间。读设备配置、NoNewPriv 和 daemon 启动时间，与上述上游版本比对。若报告产出，立即拷走，稍后复查迟到文件以区分生成失败与清理。
3. 先在自己的目录用受控崩溃验证当前系统机制，区分普通 shell 与实际应用身份/NoNewPriv 上下文；前者成功不能证明后者可用。不得变更应用身份来规避限额。
4. 系统机制仍不可用才部署备用记录器。优先补已存在的 ART dump 调用点，不替换信号 disposition；但 ART 不接到的原始故障仍可能漏记，须明确覆盖范围。记录原 siginfo/ucontext、单调时间、tid、寄存器、maps 与可读栈，失败要输出 read error；不能将读取失败填零再当现场。信号处理内禁止不受控 malloc/dladdr/直接读坏 FP，不能把有限 FP 链冒称完整 DWARF 栈。通过受控崩溃核验 signal、si_code 与 fault address 未改变，之后才开始正式普查。
5. 普查至少六轮 baseline，新数据，仅同意输入，最后同意后观察 90s；启动前即开启日志收集以保留同意前故障。无同意的轮次单列，距同意秒数为 N/A。每个信号事件单列，不把 work_thread 重投等同最终 SIGSEGV。记录每轮 PID/starttime，轮末只清自己的进程。完整栈尚未取得时明确写 unknown，不填零。

官方来源：https://github.com/openharmony/hiviewdfx_faultloggerd/tree/3adedd38fffbda1b5a47f6e70f15be2923dac157 。克隆位于 VM ~/a2hlab/ws/out-crash42/sources/faultloggerd；上游源码只能说明该版本行为，不能替代设备验证。

待移交后先捕获完整hilog（非grep后无结果即断言）、服务配置和daemon身份、dfx处理入口/配额拒绝/管道失败；用自己目录内受控crasher验证系统报告链。若修复系统链需要改变共享服务，先与外环确认其授权边界，不改应用UID、不改变信号结局。替代记录器须保留原siginfo/ucontext与chain语义，避免malloc/dladdr/直接解引用破坏故障现场，并用受控崩溃验证。
