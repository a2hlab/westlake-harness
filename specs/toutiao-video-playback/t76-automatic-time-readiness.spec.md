spec: task
name: "T76 independent automatic clock readiness"
inherits: project
satisfies: [REQ-TTVIDEO]
---
## 意图
T75真实断电后OS日期在普通网络已连接时仍1970，首点120秒白屏。独立检查普通系统自动校时配置，修正明确关闭的自动设置；不把时钟差异归因为白屏或继续已被停止的guardian/崩溃分析。
## 已定决策
- T75 C必须已恢复power释锁才开本窗；只对61b0657200000000000000000324012c fresh读锁/boot/日期/power/网络后持新锁。普通设置UI观察，复用既有采集工具，不读源码/faultlog/内存、不直接调用时间服务或修改配置文件。
- 普通唤醒解锁进入设置的日期和时间页，读图与layout确认自动设置开关和显示日期。自动设置关闭时允许单次打开并保存前后证据；若已开启就不反复拨动，不手工输入日期、时间、服务器、凭据或时区。
- 在网络已连接状态最多180秒观察自动日期是否恢复到当前日期，时间依据host UTC与设备日期分别记录，不跨时钟混算耗时。网络若未连则只报现场，不手动补连，不将本轮结果当物理断电后自动校时已修复。
- 全窗8分钟停止实验、10分钟内恢复本窗进入前power数值并释锁，设置变更若仅将自动设置由off打开则保留这一授权改动并记录回退方法；未知控件不猜点。不得点击头条或再次断电/重启。
- 输出普通UI证据及自动时间状态，任何缺截图/证据均unknown；不声称冷启动通过或白屏根因。只commit不push，本卡human审核而非未实现lifecycle PASS。
## 边界
### 允许修改
- benchmark/2026-10-23-automatic-time-readiness/**
- 私有$HOME/.local/share/westlake/automatic-time-readiness-20261023/**
- 持锁61b普通设置UI、自动日期时间off到on一次、power恢复
### 禁止
- 其他板、guardian/运行时源码分析或部署、崩溃诊断、手工改日期/时间/服务器、网络配置、头条再点、设备重启
## 验收标准
场景: 自动时间关闭且正常开启后同步
  审核: human
  测试: automatic_time_readiness_receipts_review
  假设新boot显示1970且网络已连接
  当普通设置界面显示自动设置关闭并经单次打开
  那么保存前后UI与设备时间观察，180秒内有无同步均如实记录，恢复power释锁
场景: 已开启或无法完成自动同步
  审核: human
  测试: automatic_time_readiness_receipts_review
  假设开关已开启、网络未连、控件未知或180秒未同步
  当到达对应边界
  那么保留证据与unknown，不反复修改，不将问题归因到头条，恢复power释锁
## 排除范围
修复校时服务实现、T74被拒分析、第三方崩溃、冷启动再验收与头条重复启动。
