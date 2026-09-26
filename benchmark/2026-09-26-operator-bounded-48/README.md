# #48 无守护、限时三轮隔离

按外环最新指令重跑。之前带守护数据不并入本组三轮：外环清掉7个头条进程、停止守护、终止挂起的isolated48驱动；资源污染使原组不能作为干净对照。

仅61b06572。test/metasec-bounded-48，基于a1197ba；BASELINE+1021a058桩+78e34445被动记录器，runffb324e4（unset JIT_FILE_CACHE_DIR）。无AOT，无自动重启，无新重编。

每轮前要求pidof头条和appspawn-x均为空，MemAvailable>1GiB，记录free -m和全部7组件SHA。归档三组profile并新启动parent/child。spawn后核记录器目录fd。只启动一个child，不更新/启动operator守护，stop标记全程保留。

按最新“测≤180s”指令，每轮正常观测约173s，随后先kill -9实例、parent和同板残留头条/appspawn，再确认两类PID均空、MemAvailable>1GiB，最后取证。另有只终止、绝不重启的单次板上178s期限计时器，按PID/birth匹配，防VM驱动失联；它不是自动重启守护。此组**不声称详情RESUMED后又存活180s**，避免把最新限时口径混成旧验收。

Mac真实HDC使用独立进程组，最长55s后SIGKILL；VM代理最长59s后SIGKILL进程组。操作超时记该轮失败，finally先清理，再最多各15-20s下载原始日志/快照。不让下载延长活实例窗口。不回收服务端共享HDC，不碰其他板。

第一次single-r1在Mac代理参数映射处exec format error、未接触板/未spawn，保留为夹具准备失败。改为mac bash传递Python源码和base64参数，正式bounded-r1..3。

## 人工点击时序准备轮与自动正式轮

bounded-r1..3均按173s清场，无守护、无超时，但人工读图/发指令使条目点击发生在启动后116.18/103.70/139.74s，短窗不足，不将它们当作正文性能或3轮正式验收。原始失败/截图全部保留。

正式auto-r1..3由驱动每10s检查真实截图中的固定同意框（1200×1920、红按钮/白面板/蓝盾多点交集），匹配后才执行已授权的真实uinput同意和条目点击。判据在3张已人工确认同意框及5张宿主/信息流负例上通过；它仅适配当前固定板UI，不是通用识别器。每次匹配截图与点击uptime留档，最终正文仍由人工读截图。使用独立VM venv-bounded48，Pillow12.3.0，不改其他环境。仍无守护、173s窗口、178s一次性清理兜底、先清场后下载。

## 真实页面与触摸限制

auto-r1/r2的条目尝试紧跟同意约1秒，仍命中正在退出的同意窗口（r1日志session583），末帧均是TransparentAccountLoginActivity登录页；不当作正文通过，也不据此认定桩引入登录副作用。r2看到无遮挡信息流后另补uinput(380,410)，仍记录实际结果。auto-r3改为两个独立截图门槛：先识别并点击同意，再等无遮挡信息流（白色背景/底部头条红图标，五张正负例验证）才点(380,410)，全部输入仍是真实uinput。前两轮不删、不用第三轮替换。

观察窗总计173秒与文章存活180秒是不同口径；此组只执行最新限时指令。记录器fd证明已初始化，未遇SIG11不能证明已成功捕获一次真实native崩溃。日志中的work_thread SIGABRT和主进程是否退出分列。

## Final result: ACK(blocked), R2=partially

All three original processes survived to planned termination. Readable article acceptance: 0/3.

|Round|Child/parent|Observed seconds|SIG11 headers/snapshots|Final image|Post-cleanup MemAvailable KiB|
|---|---|---:|---|---|---:|
|auto-r1|9341/9308|173.008|0/0|Login page, no article body|5938396|
|auto-r2|17894/17860|173.003|0/0|Login page, no article body|5938336|
|auto-r3|22989/22956|173.010|0/0|Login page, no article body|5934752|

Each round selected anonymous JIT; file-backed log count=0, Boolean-null NPE=0, no observed main exit(1). Each had a work_thread SIGABRT banner (TIDs 11588, 20417, 25471) while the original process survived, plus a Chrome_ProcessLauncherThread missing-child-service RuntimeException. These are not SIG11 and do not establish a metasec/JIT cause.

auto-r3 waited for unshaded feed (reviewed feed-gate-113.jpeg), then physical uinput at uptime114148.31. START at114169510 was TransparentAccountLoginActivity; no NewDetail ENTRY. The touch target/login transition is unresolved; neither article success nor a stub-induced login regression is established.

HDC timeout and cleanup failure counts: 0/3. The real Mac HDC timeout self-test (sleep3, timeout0.3) returned TimeoutError in about0.36s. Final board state: no app/appspawn PIDs, stop PRESENT, free1029MiB and MemAvailable5861348KiB; free and available are distinct.

Preparation bounded-r1..3 retained: alive173s, detail ENTRY without RESUMED, final feed images; late manual input shortened article observation. single-r1 failed before spawn. auto-r1/r2 used98f0625; r3 added the feed screenshot gate, so these are not identical-protocol A/B samples. No guardian or #50 A/B was started.

## Follow-up article confirmation: blocked by a captured warm-start SIG11

`confirm-r1` (child10378/parent10348) was a fresh consent preparation, no guardian. It survived173.009s and was killed/cleaned as scheduled. The feed refreshed to video cards; no definite article was clicked. A late tab attempt was refused by the deadline check. This is an incomplete preparation, not an article failure or success.

`confirm-warm-r1` (14699/14666) reused the consent/profile from that preparation, without a guardian or concurrent app processes. It died before article input: detected at24.562s, parent reports `killed by signal 11`. All seven component hashes passed; no #50 was enabled. Do not silently fold this warm-profile result into the previous three fresh-profile observations.

The passive recorder captured SIGSEGV/SEGV_MAPERR at address0, thread `npth-worker` TID15016. PC0x7fa6ddce20 and LR0x7fa6ddcc54 map to `/system/lib/ld-musl-aarch64.so.1`. Correct ELF addresses are0xd6e20/0xd6c54; file offsets are0xd5e20/0xd5c54, because executable PT_LOAD has vaddr-offset=0x1000. At PC: `strb wzr,[x14]`, immediately preceded by `mov x14,xzr`, on a failed byte-check path. This establishes a deliberate null write, not the caller or corruption source. The library is stripped: objdump's nearest exported `wcsxfrm+...` label is NOT a function identification.

Metadata, 4560-byte ucontext, 128-byte siginfo and3827-line maps were captured. Stack bytes were NOT captured: opening `/proc/self/mem` returned EACCES (`mem_open_errno=0xd`). Do not call this a complete native backtrace. The original sysroot library was read, never modified, and its SHA plus PC mapping are in `crash-analysis.json`.

Both instances were cleaned; final app/appspawn PID lists are empty, stop marker retained, MemAvailable5893312KiB. This follow-up provides no article-body screenshot. Warm-start crash evidence must be reviewed before extending the earlier three clean173s runs into a universal stability claim.
