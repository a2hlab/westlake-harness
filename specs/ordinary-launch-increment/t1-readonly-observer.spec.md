spec: task
name: "Bounded ordinary log increment observer"
inherits: project
---
## 意图
用现成普通shell读取模式观察parent.log和events.log新增字节及精确child身份，避免无时间戳旧日志被误当请求时延证据。
## 已定决策
- 仅61b完整serial；boot和父PID/birth显式输入，应用UID20011206和完整进程名固定。
- 远端筛选仅用POSIX read/case，不用awk/tr；cmdline固定长度raw dd包含NUL，本地精确匹配。至少13KiB ps受限PATH真实shell样本验证90轮不因无关行耗尽预算。
- 初次只建立偏移；之后约1秒串行，90秒总窗、双流总1MiB、每命令最多10秒。超时仅取消本地HDC客户端，不向板上进程发信号。
- 前后boot、父birth/UID、fd去向、regular日志dev/inode/size核验，child首次出现可锁定，后续身份变化拒绝；未绑定时采样前无child而采样后出生记partial并保留原偏移，下轮重采；已有绑定child消失或替换停止。
- 检出截断/轮转或字节不足即停止；无法发现两次采样间已完全恢复的截断重写，必须保留该限制。
- 输出目录必须新建，原argv/stdout/stderr/rc持续保存；不重试失败或覆盖原件。只报告日志可见区间，不等同发送/接收或feed。
## 边界
### 允许修改
- benchmark/2026-10-24-ordinary-host-timeline/incremental-observer/**
- specs/ordinary-launch-increment/**
- tools/spec-checks/tests/ordinary_launch_increment.rs
### 禁止
- 任何本轮设备调用、旧控制脚本/env、T121及其他停止执行器、运行时更改、UI动作、REA、推送。
## 验收标准
场景: 普通日志增量与child出现
  测试: ordinary_launch_increment_fixtures
  假设合成regular日志和一致boot父身份
  当初始建立偏移后加入真实长度的字节和唯一child身份
  那么只接收增量并记录前后uptime以及child的PID父PID出生时间UID和命令名
场景: 截断轮转或身份漂移
  测试: ordinary_launch_increment_fixtures
  假设上一个采样已确认偏移和身份
  当日志缩短或inode改变或child父boot发生漂移
  那么停止后续采样并保留原件不覆盖已接受记录
场景: 超时和字节预算
  测试: ordinary_launch_increment_fixtures
  假设本地合成子程序部分输出后超时或超过双流预算
  当运行真实本地流读取器
  那么保留部分原输出和失败回执且不再发下一命令
## 排除范围
请求队列根因、控制策略修改、实际UI验收、保证日志未缓冲、捕获采样之间所有短命进程。
