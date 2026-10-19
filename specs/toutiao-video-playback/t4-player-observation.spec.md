spec: task
name: "Exact-player native diagnostic mirror candidate"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t2-minimal-repair]
tags: [offline, observability, human-review]
---
## 意图
为r7封面停滞补足实际播放器调用证据：离线制作仅由精确libttmplayer消费者调用的日志镜像候选，把已到达的native日志复制到现有child fd2，并保持原日志行为。只交可复现候选，不把日志候选当视频修复，不在本任务上板。
## 已定决策
- [platform-specific] 输入为已验证r4播放器SHA5fba80506cd1a494de5fb6aee63930192d6d0539657cca51e99381ff8a052ee4、compat9f558aaf1d48cedbc10e6774073d71177efb6d1e196fe528f0203505d1ee761f；复用candidate/src/opensles_android_compat.c和既有OH clang15 dockbuild配方，另起candidate-r8目录，不覆盖历史件。先读cx的player-stderr-feasibility.json与r7原件。
- 使用唯一新命名的日志函数，确定性派生仅该player的目标import以绑定新函数；不导出全局同名__android_log_print抢占，不改系统liblog/runtime。先证明目标dynsym/relocation/version/hash边界，再实现派生；优先等长且SysV hash同bucket的唯一新名称（候选__wl_ttlog_00000659与原名均19字节，bucket413/521，须独立复核），不改变hash表；任何共享字符串引用或哈希影响无法证明就拒绝该派生。保留105项既有self-relative缓存重定位与全部其它字节。
- 镜像只用现有fd2，不建日志文件、不调日志阈值。单条总长包含marker/tag/newline最多1024字节、每进程最多256次镜像尝试，以饱和原子计数界定并在格式化前检查；停止镜像后仍逐次转发原日志。禁止sleep、重试写、全局锁和进程内GOT写入。保存镜像前errno并在原日志转发前还原，返回原日志函数返回值与返回后errno。
- 正确转发原priority/tag/格式与全部varargs。__android_log_vprint仅在exact liblog中ABI与实现语义复核通过时可用；va_copy必须独立，验证整型、浮点、宽度精度、字符串及长文本。仅对有界支持的格式子集镜像；%n（含位置参数/长度修饰）或无法安全解析格式只原样转发一次，不先求值，可打印固定跳过标记。%m使用入口errno；补filtered-%n与字符串/写入地址别名反例。不凭RTLD_DEFAULT/RTLD_NEXT猜provider；候选卡需列实际GOT与provider读取点，动态绑定未验证前不得上板采认。
- 复用compat原源码并把新增镜像放独立文件，保留原OpenSL标识和构造行为。脚本显式选择新源码，避免旧build脚本复制旧源码覆盖新实现。构建前check_frozen；工具链、输入、源码、产物SHA和原始stdout/stderr/rc持久保存，公开副本脱敏且标明转换。
- 原始payload仅保存在私有实验日志，公开报告不刊登URL、账户或内容数据。这里只保证已到达目标print边界的诊断可见，Java dataSource、未执行prepare、FILE或callback旁路均不保证；不能宣称首致命点已修复。
- 交付候选四件后像清单和部署前只读检查/失败回滚卡，保持run79275cf9与media d2882303不变。外环另行审新后像与上板契约；本任务禁止设备命令。合理性不能成立时交可验证拒绝原因，不强凑产物。
## 边界
### 允许修改
- benchmark/2026-10-19-toutiao-video-playback/candidate-r8/**
- specs/toutiao-video-playback/t4-player-observation.spec.md
- tools/spec-checks/tests/toutiao_player_observation.rs
### 禁止
- 不修改历史candidate、冻结项、系统liblog/runtime、主API历史表或其它worktree；不执行设备命令，不推送。
## 完成条件
### Rule: exact-consumer-and-preserved-forwarding — 精确消费者与原行为保留
场景: 派生只改已证明独占的目标导入
  测试: ttvideo_observation_derivation
  假设 输入为精确r4 SHA且目标导入与哈希及字符串引用边界已解析
  当 生成候选并逐字节比较输入输出与全部105项self-relative缓存重定位
  那么 只有批准的目标导入字节变化且重定位不变，并输出输入输出SHA和机器可读差异
场景: 漂移或共享字符串拒绝
  测试: ttvideo_observation_derivation
  假设 输入SHA漂移或目标不是唯一UNDEF函数或共享字符串引用影响未排除
  当 请求派生
  那么 非零退出且不产生可部署输出，保留明确拒绝原因
场景: 镜像不改变原函数参数返回和errno
  测试: ttvideo_observation_forwarding
  假设 镜像函数与可观测参考后端以同一调用约定链接
  当 用混合整型浮点宽度精度字符串长文本、非零errno、filtered-%n及别名反例调用并跨越256条镜像上限
  那么 原后端每次恰好调用一次且priority/tag/格式参数语义不变，返回值与errno等于仅调用原后端，镜像大小及计数不越界
场景: exact生产ABI和构建证据审查
  测试: ttvideo_observation_receipt
  审核: human
  假设 源码派生和参考后端用例已通过
  当 复核exact liblog ABI与新compat导出导入、完整构建日志及后像清单
  那么 原OpenSL行为保留且构建入口能选到新源码，raw日志可追溯；实际provider绑定和视频播放仍为unknown，未执行设备部署
场景: 镜像和构建日志输出边界
  测试: ttvideo_observation_receipt
  假设 使用另目录新源码且构建输出流被逐项记录
  当 检查stderr镜像、stdout和构建raw stdout/stderr/rc及后像清单
  那么 镜像不写stdout也不新建文件，公开材料无原始payload，构建日志对应实际新源码且run79275cf9和media d2882303保持原SHA
