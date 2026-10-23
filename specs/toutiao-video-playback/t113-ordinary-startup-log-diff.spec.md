spec: task
name: "T113 ordinary startup evidence diff after reboot repeat failure"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t109-spare-board-power-entry]
---
## 意图
从T109两份新启动普通日志查是否有明确公共API、类加载、服务或初始化失败证据，为可实施修复选择目标；不把已知共有警告或随机退出当成已定位的桥接缺陷。
## 已定决策
- Codex只读T109实际7011/9860日志前缀及boot/身份/mtime回执，分别绑定，禁止混PID。对照既有T95成功4MiB日志的同类阶段；覆盖不同须明确。
- 优先提取完整异常/明确失败及其前置阶段，不只grep No such file或fatal。只有新且实际阻断的普通API错误才沿本地已有源码找实现路径和候选；没有则明确未发现可实施公共API修复，不凑代码。
- 不设备调用，不内存/信号故障归因，不保护机制分析，不读取T71/T74/T91停止对象；REA本卡不调用，只有具体产物问题另派。五分钟首交，公开结果只保留允许的阶段/错误字段，不发布token或个人数据。
## 边界
### 允许修改
- benchmark/2026-10-23-reboot-startup-log-diff/**
### 禁止
- 设备操作、运行时修改、停止对象、原始私有日志入库、随机崩溃归因
## 验收标准
场景: 新普通API失败可绑定
  审核: human
  测试: reboot_startup_log_diff_review
  假设原始日志有明确错误及进程身份
  当对比同类成功阶段并查已有源码
  那么给精确行SHA和实现路径，说明是否能支持候选，保留因果限度
场景: 日志不足或仅共有警告
  审核: human
  测试: reboot_startup_log_diff_review
  假设日志覆盖不足、错误未显式或与成功共有
  当形成分析结果
  那么写无确定API候选及缺项，不将空白或退出倒推为API错误
## 排除范围
修复随机退出、二进制补丁、部署、封板、重复已有时钟分析。
