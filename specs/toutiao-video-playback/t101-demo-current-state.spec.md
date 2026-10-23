spec: task
name: "T101 demo current state and ordinary launch acceptance"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t95-startup-stage-coverage]
---
## 意图
用户允许CC加入。由CC单独核对61b当前现场，为下一次普通手点验收准备精确入口，外环和其他车道不同时操作板子。
## 已定决策
- CC仅现场核验，不使用REA或读取此前被停止源码。先只读held/boot/当前时间和既有进程身份；唯一白名单61b0657200000000000000000324012c。若有其他holder立即停止，boot变化照实报告，不沿旧PID盲查。
- 最多一次snapshot_display截图，允许独占锁内保存/收取/删除本任务临时截图文件，原始命令/rc/时间持久记录，3分钟收口释放锁。不得重启、启动/停止应用、点击、解锁、改电源/WiFi/权限或部署；锁屏则报告锁屏，不主动唤醒。截图须目读，活进程不证明feed。
- 离线复用已验普通桌面点击验收方式，列下一次手点所需的最小采样与通过判据；不要执行后继测试，不读T91或旧拒绝对象。给截图实际数量和facts来源，未采就0或unknown。
## 边界
### 允许修改
- benchmark/2026-10-23-demo-current-state/**
- 私有 $HOME/.local/share/westlake/demo-current-state-20261023/**
### 禁止
- 设备运行状态修改、应用操作、部署、REA、内容停止对象、其他设备
## 验收标准
场景: 当前现场可安全读取
  审核: human
  测试: demo_current_state_review
  假设白名单设备在线且无其他holder
  当独占窗口读取当前状态并取得最多一张图
  那么用实际截图和身份报告当前状态，不沿用17点历史feed作为现在可用证据，释放锁
场景: 锁占用或读取失败
  审核: human
  测试: demo_current_state_review
  假设设备不可读、锁被占用或命令失败
  当停止条件发生
  那么保留真实失败且不重试/重启/改设备状态，完成必要锁恢复
## 排除范围
白屏修复实施、冷启动签认、随机崩溃归因。
