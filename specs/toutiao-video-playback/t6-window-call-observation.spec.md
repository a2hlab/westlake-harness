spec: task
name: "Bounded exact native-window call observation"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t1-static-evidence]
tags: [diagnostic, bounded, human-review]
---
## 意图
r10 实测播放器 lock 绑定固定 -19 桩，但 fromSurface 内部解析方和调用当时对象类型未知。复用现成 OH LLDB 工具作一次有界调用观测，以决定已有窗口实现能否复用；不把诊断当播放修复。
## 已定决策
- [platform-specific] 仅白名单61b0657200000000000000000324012c、外环显式给定boot/PID/birth的头条child。源码位于diagnostic-r11；先离线脚本与测试，外环独立审查后才允许执行。server/client路径、SHA、版本、原始命令与rc必须记录；未验证attach能力明确unknown。
- 以r10精确libandroid76512d97758c308acf7baff4647f07db792c02b8fae2eda93399bd18eda03727、shim85c789f48b2bc0c31658c9dc591cd27784cc0ddfe559005e8d36d1d7d220476a的PT_LOAD/maps/inode计算地址，不硬编码ASLR；同名多份须选实际player槽对应实例。身份/模块/读取结果不符即停止。
- 在libandroid ELF0x3bd4尾调用前记录x2实际目标与x30返回点，按线程/调用序号在该返回点记录x0；lock ELF0x5e48入口独立记录本次x0。各时点保留当前PC、线程、模块范围；从+0检查0x5f776e64后才读取+0xc8的0x414e5731及+0xc0句柄。失败或不匹配写unknown，不猜raw对象，不调用目标函数、不改寄存器或返回值。
- 对象返回与lock可跨线程；没有完整创建/释放代次证据不宣布是同一对象。每一事件都可独立判断当时类型，不复用旧日志地址。winner依据实际寄存器落到精确映射模块，不能用新一次dlsym或全机符号并集替代。
- 观测最多120秒、最多4次fromSurface与4次lock事件；只使用诊断断点，不修改磁盘运行时文件或全局符号。detach路径删除自建断点、继续被暂停进程并核TracerPid/状态；异常和超时仍执行清理，禁止kill全局hdc/server或按名称杀进程。不能确认清理时外环在持锁窗口中恢复原基线fresh boot。
- 原始观测落持久目录，公开摘录不含媒体URL/用户数据。执行必须先只读检查、持独占板锁、沿既有r10原apply-plan回滚流程；20分钟开始回滚、30分钟硬上限。该契约不授权全局shim/API冻结改动或远程推送。
## 边界
### 允许修改
- benchmark/2026-10-19-toutiao-video-playback/diagnostic-r11/**
- tools/spec-checks/tests/toutiao_window_observation.rs
- specs/toutiao-video-playback/t6-window-call-observation.spec.md
### 禁止
- 不改历史r10及以前的源码、部署产物、冻结项；不诊断随机崩溃、安全机制，不清用户数据，不自动宣称视频通过。
## 完成条件
### Rule: exact-bounded-observation — 精确调用与有界退出
场景: 实际调用身份关联
  测试: ttvideo_window_observation_identity
  假设 精确boot/PID/birth、模块SHA与映射匹配且存在fromSurface尾调用与返回及lock入口事件
  当 解析寄存器与当前对象只读结果
  那么 每事件记录线程和调用序号，winner绑定精确映射模块，魔数及句柄独立判定，不把跨线程同地址自动合并成对象生命周期
场景: 错对象或陈旧身份拒绝
  测试: ttvideo_window_observation_identity
  假设 boot或birth变化、模块多份歧义、魔数不符、读取失败或返回点线程不符
  当 请求记录与分类
  那么 拒绝错误身份和关联，相关对象为unknown，不补猜测值也不调用目标函数
场景: 达到预算及异常退出
  测试: ttvideo_window_observation_cleanup
  假设 已设置诊断断点且目标可能暂停
  当 达到120秒或事件上限，或发生attach/读取/断点安装失败
  那么 删除本次断点、detach并保留原始错误与清理结果，不能确认恢复时要求外环回滚，不输出播放PASS
场景: 真机结果独立审核
  测试: ttvideo_window_observation_receipt
  审核: human
  假设 离线正反例通过且工具与执行计划经外环复核
  当 在独占限时窗口执行并核查原始回执、设备恢复及截图
  那么 实际winner与对象类型仅按采到证据判定，未采到写unknown，播放仍依据t3的两个有声动态周期另验
## 排除范围
- 修复窗口API、随机退出原因、全局调试设施安装、反虚拟化设置变更和自动远端推送。
