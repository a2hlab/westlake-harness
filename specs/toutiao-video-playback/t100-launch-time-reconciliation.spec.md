spec: task
name: "T100 launch evidence timeline reconciliation"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t95-startup-stage-coverage]
---
## 意图
整合现有普通启动、trace和截图证据，区分图标到spawn、初始化到渲染提交、首个WebView trace标记与真实feed，避免把未采样间隔误认白屏耗时。
## 已定决策
- Codex离线复核T87/T89/T92/T95主树及已有私有原件，输出一张有证据路径/行号/时间精度/身份的时间线。T99未交前不等待、不转换now；交后另补时钟映射，不能把不同线程日志顺序当同步时间边界。
- 给出当前最有区分力的一项正常启动观测及精确缺口，最多3条，禁止重复宽泛归因或猜测补丁。5分钟首交，无设备/REA/被停止源码读取。
## 边界
### 允许修改
- benchmark/2026-10-23-launch-time-reconciliation/**
### 禁止
- 设备操作、部署、故障/内存分析、T91及此前内容停止对象
## 验收标准
场景: 时间与身份可绑定
  审核: human
  测试: launch_time_reconciliation_review
  假设原件SHA与各事件身份核验通过
  当合并时间线
  那么逐事件标精度与证据，不把trace首标记冒充首帧，不累计重叠区间
场景: 时间域或覆盖缺失
  审核: human
  测试: launch_time_reconciliation_review
  假设时间域未知或截图采样不足
  当形成结论
  那么相关区间保持unknown并指出可区分的正常观测，不猜测耗时或修复
## 排除范围
代码修改、部署、签认。
