# 头条战役·知识精华与陷阱清单（所有车道上岗必读）

> 外环维护。派单时引用本文件；任何 agent 开工前先读。新增确认知识/新踩的坑都往这里加，不要只散落在黑板长文里。

## A. 已确认的事实（别重新论证/别推翻）

1. **点击已通**：真实 uinput → InputConsumer 收到（source=0x1002）→ FeedItemRoot.performClick → startActivity。窗口焦点(#34)+dispatchAppVisibility(#38)是根。
2. **七类崩溃全部定位，全部可在鸿蒙侧治标（都不需要 Bionic）**：
   - #46-1 WebView 渲染 SIGSEGV = shim dlopen 先开 NDK libGLESv2 门面、§734 到 libGLESv3 成死代码 → GL 初始化失败 GrContext 空。修:shim 顺序(85c789f4)。
   - #46-2 视频 88s SIGTRAP = MediaCodec native_setup 不报错交空壳 + getOwnCodecInfo 未注册 → UnsatisfiedLinkError(Error 绕过 catch)。修:mc46(d4fae8e5)。
   - #46-3 npth 死循环 = libnpth JNI_OnLoad 走线程链表 while(x){x=*x}，Bionic 偏移0是next(到NULL)，**musl 偏移0是self(指向自己)→ 死循环**。修:libnpth ret 补丁(8b8d559c)。
   - #46-4 TicketGuard SIGSEGV@0x28 = 默认命名空间第二份 libttboringssl 把 HMAC_Init_ex 绑到 OH OpenSSL3(布局不同)。修:LD_PRELOAD libttcrypto(33b4ab08)。
   - #46-5 渲染器 OOM = 单进程 Blink PartitionAlloc 无界增长撞 vm.max_map_count=65530(内存还剩、overcommit=1)。修:map_count 抬到 1048576。
   - #49 堆损坏 = **libnpth_xasan/libnpth_heap_tracker 伸手进 Bionic `__libc_malloc_dispatch` 挂钩 malloc，在 musl 上踩坏 mallocng 块头**。受害者随机(SQLite/Mali/bd_tracker)。修:shim 拒绝加载这两个纯调试库(并入 85c789f4)。
   - #48 metasec 退出 = libandroid 缺一串符号(先 7 个 ASensor*，再 __system_property_read 等 8 个 Bionic-libc 兼容符号)→ 重定位失败 → 线程死 → X.DEv null Looper NPE → exit。**这不是概率性，是缺符号**。
3. **metasec 的根本边界**：把符号补全让 metasec 完整加载 → 它的 init 读 Bionic pthread 内部，musl 上 SIGSEGV（真正 Bionic-bound）。所以**方向是"架空 metasec"（no-op 桩）而非"让它跑"**。#41 已证 metasec 对 feed+文章非必需(惰性)。
4. **寒冰(hanbin)没解决 metasec**：其方向以 metasec 为原始目标，但 debug.md 冻结在 8-01，7-22"头条可用"7-27 自证伪(进程已死)，7-31 仍在查 libmetasec 崩溃；9 月转做上屏管线，现处阶段 2/7、DAYU200 32位。转寒冰不是 metasec 快速解。
5. **JIT 慢的真因+解法(仓库已有)**：OH XPM(代码签名)拒 memfd RX，ART 退回匿名缓存、发布代码时 RX↔RWX 来回切(主线程等 mmap 写锁)。解:`WESTLAKE_OH_JIT_FILE_CACHE_DIR` 用 app 私有 O_TMPFILE 双视图，免切，p90 -61.6%（docs/parity/OH-ANDROID-PARITY-2026-09-05.md）。**前提:该目录必须以 app UID 预建、0700**，否则静默回退匿名。
6. **AOT(dex2oat) 提速**:必须用 westlake 自建 host dex2oat(oat247 同源)，operator 本地/寒冰的是 oat230 不兼容(#42)。speed 臂约把开文章砍半(7.2/5.8s vs 12-22s)。
7. **metasec 架空落地(#48)**：整个 app 面 native ABI 极小 = 1 个 `JNI_OnLoad` + 1 个分发口 `ms.bd.c.m.a(int cmd,…)Object`（其余 `com.bytedance.mobsec.metasec.ml.*` 全纯 Java 包装、零 native；无库 DT_NEED metasec）。空壳桩必须按 cmd **返类型正确的非空值**（返 null 被 Java 拆箱→NPE；返错类型→CCE）：`0x01*`+`0x02000007/0c`+`0x04000003`/String→`""`、`0x08*`/Integer→`0`、`0x04000001`+`0x04000004`/Boolean→**TRUE**、`0x02000006/0a`+`0x03000001`/String[]→空数组、其余(setter/`if-nez`)→null。Boolean 必须 TRUE：`f3.run`(0x04000004) 是自旋等待 `while(!a())sleep(500)`，false 挂死。cmd→类型表:operator-stub-48 `scripts/dispatch_map.py`(617 点)，安全值桩 sha `1021a058…`。

## B. 方法论陷阱（别再犯）

1. **别数子串**：`grep -c NewDetailActivity` 会命中服务端 settings JSON。活动是否启动只看行首生命周期行(onCreate/onResume/START/Displayed/`[B47-SLA] ENTRY`) + 截图。
2. **别数 dmesg 行数**：环形缓冲已满，前后行数不变会漏掉新 avc；直接 grep 原文。SELinux normal_hap 是 Enforcing，su 域是 permissive。
3. **缺栈别硬归因**：SIG11/SIGABRT 没抓到 native 栈时，不宣称是 metasec/Bionic/JIT。DFX 有配额(单 UID 60次/24h)、只处理首个信号 → 常常无 cppcrash。要栈就上被动记录器(out-crash42/recorder)。
4. **一次只改一个变量**：别把两个修复(如空壳+JIT#50)同时上再测，崩溃因果会不可分。
5. **观察窗 ≥40s**：真实详情页启动可能在触摸后 15-26s 才发生，短窗会漏。带视频文章要 ≥120s 才见 metasec/OOM 层。
6. **区分同意点击 vs 条目点击**：run 里有两次 uinput，queueMs 引用前先分清是哪次。
7. **截图是地面真相**：日志信号模糊时以 after-Ns 截图为准（正文页 vs 信息流 vs 宿主）。外环判早过多次都是只信日志。
8. **maps 取全**：`hdc recv /proc/PID/maps` 只得约 4KB 截断；要板上 cat 到文件再 recv。
9. **VT 空树 + P4b pass = 取证缺口，不是画面缺失**：child.stderr 的 `VT ==== root[0] ==== … VT ==== end ====` 之间零 rect 行、但同 log 有 mAppVisible<-true/DecorView 标记且 P4b(RenderService 见窗)过 → 窗口在、渲染链通，是 tap/VT 通道本轮无输出（#22/#40/#47 burgerking 同型）。判据侧应把该组合告警为“取证失败”而非记 P4a fail。重跑大概率过。
10. **split APK 的 dex 搜索会落到语言 config split**：candy/discord 的 launcher 类在 base APK（classes3.dex/classes.dex，strings 可证），装载器却在 ~64KB 的 config.en/ar split 里反复 `Unable to find entry`（EOCD 偏移≈split 尺寸即铁证）→ 活动停在 inflate 前。splits 明明 staged（ASX_SPLIT_APK_PATHS）——是 base/split 的 dex 搜索顺序缺口，非 splits 缺失、非 AAsset 回归。

11. **dlopen 是 depth-1 符号作用域**：OH musl 里被 dlopen 的库，其未定义符号只在自己**直接 DT_NEEDED**+全局作用域解析，不看传递依赖——metasec 缺 `__system_property_read` 不能靠 depth-2 的 libbase 兜，必须补到它直接 NEED 的 libandroid。补缺符号要**一次算全闭包**（UND−直接依赖导出，脚本 metasec_direct_missing.py），别一轮补一个：板子每次只报字典序第一个缺符。
12. **桩/no-op 别拍脑袋返值**：分发口返 `Object` 时，返 null 会被 Java 自动拆箱→NPE，返错类型→CCE。必须先逆 cmd→返回类型表（dispatch_map.py）再按类型返非空；Boolean 的 true/false 要读调用点控制流（自旋等待循环 `while(!a())sleep` → 必 true），聚合表看不出来。

## C. 稳定基线（确定收益，known-good，见 westlake-harness-triage46/BASELINE.md）
WebView shim 85c789f4(含 #46 GLES + #49 拒堆库) + bridge mc46 d4fae8e5 + libnpth 8b8d559c + tt targets/LD_PRELOAD + map_count 1048576。metasec 空壳(#48)与 JIT 文件缓存(#50)、AOT(#42)是在此之上的叠加项，各自单独验证后并入。

## D. 新增核实（内环追加）

- **AOT 同源检查不能只看 OAT 版本或旧 framework report**（codex，2026-09-26，`2eb427d`）：operator 的实际 libart 已由009a08fb变为A1的ae2cb182，旧报告仍记前者。本次核36项BCP/boot、实际启动BCP顺序及A1单对象加载器改动后，确认#42 speed产物可离线复用；安装时仍须核实际runtime文件SHA，不能只信报告。新组合的设备接收/提速尚未验证；旧speed有效点击n=2，不作为当前收益证明。

## D. 新确认的现场取证陷阱（codex-2，2026-09-26）

- **记录器库存在≠已启用**：operator appspawn 的 child 日志实际出现 `SigchainStartReassert not found`；原crash42在此入口初始化，因此只换libart也不会抓栈。隔离测试将目录初始化移到非信号上下文的special-handler注册阶段并幂等，原callback顺序/返回值/信号上下文不变；parent及真实child均实证fd6指向crash42目录。今后必须检查初始化日志+子进程目录fd，再以真实快照确认捕获；不得因目录存在或候选SHA正确就声称已覆盖原生崩溃。代码`test/metasec-isolated-48 @7aec455`，后续三轮在途。

## D. 备用线（Bionic / 寒冰 oh-kit 64 位）已确认（claude-2 加，2026-09-26）

1. **端到端可行(M3.crux)**：Bionic 进程(#43 AOSP14 linker64/libc)能 dlopen 6.1 源+NDK r27c 编的 oh-kit 库并调进 OH 服务——liboh_kit_hilog 调 HiLogPrint，hilog 读到（板 5cd1e3dd）。已编 11 库(utils/hilog_base/begetutil/hilog/ipc/samgr/eventhandler/surface/display_mapper/display_buffer_vdi/native_image)，DT_NEEDED 全干净。产物 hw248 `/opt/build-runs/20260926-oh6.1.0.31-westlake-ohkit-aarch64/`。
2. **oh-kit-for-Bionic 工具链两坑**：①NDK r27c libc++ 是内联命名空间 `__ndk1`+abi-tag nn180000，与设备平台 libc++.so 的 `__1` 不匹配 → 直链平台 libc++ 报 undefined `std::__ndk1::…`；解法=把 NDK `libc++_static.a`+`libc++abi.a` **静态**链进每个库(无 libc++ DT_NEEDED、无冲突)。②libc++18 删了私有头 `__mutex_base`(OH 6.1 ipc 直接 include)→ 补转 `<mutex>` 的兼容头。
3. **用 6.1 源而非寒冰 7.0 pristine**：按寒冰 origin.txt 路径清单从板子同版 6.1 树(/opt/build-trees/oh610_lts_source)取文件、重生成 6.1 md5；寒冰 7.0 patch 多能 fuzz 套上。gen 生成物(IDL 头/proxy 源)从 `out/wukong100/gen` 暂存进 pristine/gen。
4. **rs 是 6.1↔7.0 架构反转，寒冰 rs patch 对 6.1 方向相反(别照搬)**：6.1 事务=RSRenderServiceClient→服务连接(`GetClientToServiceConnection`，真实现)；7.0=RSRenderPipelineClient→渲染连接。6.1 的 RSRenderPipelineClient::CommitTransaction 是空体。寒冰 0004/0005(丢服务连接)对 6.1 反了，0015(裁 RSRenderPipelineClient)裁的是 6.1 里的空壳。rs 移植 6.1 需围绕 RSRenderServiceClient 从头设计裁剪(借鉴方法非移植)。

## B 补充（claude-2）

9. **env 未必透到 app 子进程**：run.sh 里 export 的环境变量，appspawn-x fork app child 时会重置 environ，child 内 `getenv` 拿不到（#44 的 WESTLAKE_SOURCE_LOG_STDERR 就这样失效）；只有框架在 fork 前读的(如 WESTLAKE_TRACE_NATIVE_LOADER)才生效。要传给 app native 代码需 appspawn-x 的 env 转发白名单。
