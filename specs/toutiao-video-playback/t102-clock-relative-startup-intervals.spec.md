spec: task
name: "T102 relative ordinary startup timing"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t99-permission-restored-clock-analysis, t100-launch-time-reconciliation]
---
## 意图
T99已证明固定运行库POLL/WAKE的now表达式为clock_gettime(1)整数毫秒。将静态证据和已有普通日志结合，仅计算可配对同线程POLL区间，识别有证等待和仍未覆盖的启动阶段。
## 已定决策
- Codex离线读取T99真实Evidence/目标hash、T95B原日志和T100时间线。先核所有SHA，仅对同TID完整enter/exit按原顺序配对；嵌套/缺端/乱序/负值排除，WAKE不作exit。单位来自T99，不凭数值猜测。
- 给出main TID6311前10个最长区间、总覆盖并集及阶段旁的原始计数器，区分POLL等待与CPU工作，不将缺记录当阻塞。时钟跨域、runtime clock_gettime归属未证明，禁止直接与trace/墙钟相减或据此认根因。
- 5分钟首交，原件不公开，少量脱敏证据+可重跑解析器/检查落自己的树；不采新设备数据、REA、权限或部署，不读停止对象。
## 边界
### 允许修改
- benchmark/2026-10-23-clock-relative-startup/**
### 禁止
- 设备、部署、权限、故障归属、此前停止对象
## 验收标准
场景: 完整同线程区间
  审核: human
  测试: clock_relative_startup_review
  假设输入SHA及静态单位证据核验通过
  当配对完整POLL记录
  那么逐项输出原行与时差，独立复验前10项且不把等待等于缺陷
场景: 记录缺失或时钟关系未证
  审核: human
  测试: clock_relative_startup_review
  假设缺端、嵌套、乱序或跨时钟未绑定
  当形成结果
  那么排除对应时差并明确unknown，不补猜测时间
## 排除范围
新板上实验、修复与签认。
