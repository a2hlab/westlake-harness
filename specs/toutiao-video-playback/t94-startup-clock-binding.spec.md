spec: task
name: "T94 successful startup clock binding"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t93-existing-success-startup-log]
---
## 意图
T93成功启动日志含TOUCH21-POLL/WAKE的now数值，但时钟域未绑定。离线核对自有普通日志计时实现与已有产物映射，判断能否连接T92的trace时间，不推断退出原因。
## 已定决策
- Codex主车道只搜索本地仓库/已归档源码、补丁与构建映射中的TOUCH21-POLL/TOUCH21-WAKE日志计时实现。引用路径、行号、文件SHA、时钟API、单位和产物关联；仅同名字符串不证明部署件同源。最多5分钟，没找到就列出精确搜索范围，不反复扩大。
- Codex复核车道独立核对T93提取器与原300行输入SHA，再检查主车道计时结论；不能靠now数值接近uptime断言同域。首轮4分钟，主结果未到就提交已做的复核和明确待审项。
- 零设备命令、零部署、零REA新调用；不读T91预检或此前停止的监督器/内存/故障源码，不重试被拦动作，不分析退出原因。路径问题只报外环，不向用户发交互式问题。
- 原始日志保持私有。公开仅脱敏小片段、哈希、复核命令和结果；不写主工作树，内环各自analysis分支提交且不push。
## 边界
### 允许修改
- benchmark/2026-10-23-startup-clock-binding/**
### 禁止
- 设备、运行时实现、冻结项、T91及先前停止对象、CC分析、主工作树文件
## 验收标准
场景: 计时实现与产物绑定齐备
  审核: human
  测试: startup_clock_binding_review
  假设日志与来源实现及部署映射均有可核哈希
  当主车道出具引用并由复核车道独立检查
  那么明确单位和时钟域且只对可绑定事件给出时间，不将相邻日志推为完整阶段耗时
场景: 来源或产物绑定缺失
  审核: human
  测试: startup_clock_binding_review
  假设搜索范围内未找到实现或无法证明部署一致
  当到达限时或发现证据不足
  那么结论保持unknown并列出缺失链接，不猜测耗时且无设备操作
## 排除范围
白屏修复部署、冷启动签认、新启动实验和先前被停止动作。
