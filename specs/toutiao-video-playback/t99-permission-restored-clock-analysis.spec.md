spec: task
name: "T99 user-restored execution clock analysis"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t98-rea-supported-local-environment]
---
## 意图
用户已亲自切换cx-reentry-peer权限，外环重新/status确认Full Access。以改变后的真实执行条件恢复普通日志计时静态分析，保留此前全部失败，不把权限恢复当白屏修复。
## 已定决策
- 唯一Codex主车道复用T98记录的配套Swift/SDK、Java21/Ghidra和工作区cache设置；新目录新回执，先一次java -version验证执行，再一次REA搜索同SHA8ab6742d运行库TOUCH21标记。MCP会话审批状态未变，不重试T96查询，不触及T91内容停止动作。
- 成功后沿返回引用读取最小相关计时函数，列Evidence ID/地址/单位/时钟API；不运行目标或修改产物，不做内存/故障分析。每次只消费真实工具输出，不猜函数或时钟。6分钟首交，长任务报活句柄，不重复启动。
- 所有原件持久保存，公共副本脱敏。未知/失败明确报外环，实际权限仍不符立即停止，不自行调整权限或另换执行者。
## 边界
### 允许修改
- benchmark/2026-10-23-permission-restored-clock/**
### 禁止
- 设备、部署、权限配置、目标二进制、T91及此前内容停止对象
## 验收标准
场景: 新执行条件下工具成功
  审核: human
  测试: permission_restored_clock_review
  假设外环已确认用户改变权限且目标SHA匹配
  当Java探测及REA实际返回计时函数证据
  那么给出限定时钟结论和完整回执，不宣称修复或运行时对齐已通过
场景: 工具失败或尚未完成
  审核: human
  测试: permission_restored_clock_review
  假设工具失败、对象不符或长任务仍在运行
  当采集结果或首交期限到达
  那么如实区分失败和活句柄，不变更权限或重复拒绝动作
## 排除范围
修复部署、冷启动签认。
