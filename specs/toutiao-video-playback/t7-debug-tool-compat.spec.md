spec: task
name: "Validate reusable debugger on a dedicated OH probe"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t1-static-evidence]
tags: [diagnostic, bounded, human-review]
---
## 意图
R11 的 SDK15 server 在握手阶段断言退出，未采到窗口事件。先在空闲板的独立自有探针上验证已有替代工具，避免用演示应用反复试错；工具通过也不证明头条播放或窗口对象类型。
## 已定决策
- [platform-specific] 仅允许外环持锁白名单5cd1e3dd00000000000000000923012c执行；先只读boot、内核、SELinux、板锁和进程状态。内环只交离线实现/构建/测试，不调用设备。设备窗口15分钟内，单次观测60秒。
- 复用本地NDK r23b静态AArch64 server SHA256 13c0b4bfcb0b8b83cd9d73df2be0ebffcb1cc5fea2eb420cb7b2f5629254a06a，SDK15 host c6008509f6b4bd8b5766eaad671738364eaa01a039db00e5d94e47204972dbf1。先静态核无PT_INTERP/DT_NEEDED，不将不同SHA等同已验证兼容。
- 新建最小自有OH原生probe：noinline marker接收递增计数，每250ms调用，标准输出计数，120秒自行退出；源码、编译器/工具链哈希、原始stdout/stderr和rc存持久目录。使用现成OH SDK，先核编译命令，不重建runtime。
- 部署仅独占新目录/data/local/tmp/wl-debug-compat-<boot-prefix>-<nonce>内的probe和server；不安装APK、不改系统/应用/runtime/参数，不重启、不接触任何已有应用或父进程。目标由本次启动回执、boot/PID/birth/UID/exeSHA和server身份绑定，不能按名称选进程。命令行用od原始字节核验，socket inode核端口归属；端口5039需先证明空闲，移除仅本次forward。
- observer离线默认拒绝；显式执行需外环新admission和同一held整行。先设置require-hardware、remote-ohos、disable-memory-cache；仅在probe精确marker地址布1个硬件断点，读取两次命中的PC/x0/TID/StopID且计数递增，两次Continue后有新StopID。所有断点显式hardware且读回验证；禁止软件回退、表达式、目标函数调用、改寄存器/返回值。
- 清理删除自有断点、detach keep-stopped false，独立确认probe的TracerPid0/非T状态且计数继续增长。若无法detach，仅可按boot/PID/birth/exeSHA再次确认后终止本次自有server/probe，记录未通过；不得kill其他进程或全局hdc。120秒probe自退是兜底，不能代替清理证据。原始握手、命中、清理证据缺一即unknown/failed。
- 本契约不修改R11冻结工具pin，不允许直接把替代server用于头条；兼容性通过后另行采认观测器后继版本。
## 边界
### 允许修改
- benchmark/2026-10-19-toutiao-video-playback/tool-compat-r12/**
- tools/spec-checks/tests/toutiao_debug_tool_compat.rs
- specs/toutiao-video-playback/t7-debug-tool-compat.spec.md
### 禁止
- 不改历史R11、部署产物、冻结项、SDK、用户数据、网络配置及已有应用进程，不推送远程。
## 完成条件
### Rule: isolated-debugger-validation — 专用探针与严格清理
场景: 默认拒绝及对象漂移
  测试: ttvideo_tool_compat_guards
  假设 缺少显式执行准入或boot、PID、birth、工具SHA、probeSHA、板锁任一不符
  当 请求准备或连接专用探针
  那么 缺准入为零设备调用，身份漂移拒绝后续调试，不附加既有应用
场景: 两次真实硬件命中
  测试: ttvideo_tool_compat_events
  假设 精确自有probe和server匹配且marker地址由本次maps及ELF推导
  当 在60秒内连接并命中后继续至第二次命中
  那么 记录精确硬件断点、两个不同StopID、同一marker的PC与递增x0，缺命中或软件回退不得通过
场景: 失败和超时清理
  测试: ttvideo_tool_compat_cleanup
  假设 连接失败、硬件断点不支持或观测超时
  当 退出本次诊断
  那么 只清理自有断点和进程、保留原始错误与TracerPid及进度证据，无法确认则failed且不得称兼容
场景: 真机准入和作用域复审
  测试: ttvideo_tool_compat_receipt
  审核: human
  假设 离线正反例通过且原始构建和工具身份齐全
  当 外环在空闲5cd上执行并审核真实握手、两次命中、恢复进度和forward清理
  那么 仅签认专用probe上的工具兼容性，头条对象与播放保持unknown，R11不被静默放宽
## 排除范围
- 头条随机退出归因、视频修复、公共API冻结变更、跨板运行时统一态变更和远程推送。
