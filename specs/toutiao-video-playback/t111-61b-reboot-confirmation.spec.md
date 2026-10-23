spec: task
name: "T111 61b reboot first icon confirmation with 5cd fallback"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t109-spare-board-power-entry]
---
## 意图
保留5cd已经连续复测的备用演示状态，回到原问题板61b做一次软件重启后首次图标启动。用真实首轮结果区分现存实例返回与新启动，明确软件重启不等于物理断电。
## 已定决策
- 必须在T109闭窗且外环目读5cd正图/当前实例可用后才启动本卡；5cd为保留的备用演示状态，不操作。61b唯一白名单序列号61b0657200000000000000000324012c。用户本轮明确允许agent自行发重启命令，不等待人工断电。
- CC唯一61b操作者，5cd/5ea不动。先只读held/boot/power/进程/网络和既有恢复说明，持独占锁，一次普通reboot。复用已验证有界传输与采集入口，不部署、不改配置/网络/应用数据。
- 等待设备重连和新boot确认最多120秒，正常唤醒解无凭据锁屏。读boot readiness、系统日期、当前网络IPv4/route，最多60秒等待；无网络或就绪失败停止、不通过切网或第二次重启制造初态。
- 当前布局完整定位图标（至多16个不同页/重复页边界）后一次普通点击；点击前若已有目标child则记录自动启动现象，不杀进程伪造无child。点击后截图10/30/60/90/120秒、普通进程/前台状态；保存实际采样时刻。若child退出，只读按当轮实际PID/boot归属的普通启动日志固定前128KiB，排除fault/内存/保护机制归因，不第二次点击掩盖首启失败。
- 整窗8分钟停观察、10分钟恢复原power参数并释锁。网络保持，若有feed保留，不为收口再重启。截图/facts按实采，原件持久；first use成功只判本轮软件boot，不能据此签物理断电。
## 边界
### 允许修改
- benchmark/2026-10-23-61b-reboot-confirmation/**
- 私有 $HOME/.local/share/westlake/61b-reboot-confirmation-20261023/**
### 禁止
- 5cd/5ea操作、第二次重启、数据清理、部署、网络设置改变、随机崩溃/停止对象分析
## 验收标准
场景: 就绪后首次普通图标启动
  审核: human
  测试: demo_board_reboot_confirmation_review
  假设新boot、网络和界面可正常定位图标
  当一次普通图标点击并有界采图
  那么记录首轮真实页面及进程，不隐藏白屏或退出，恢复power释锁且不签物理断电
场景: 重连就绪或页面异常
  审核: human
  测试: demo_board_reboot_confirmation_review
  假设重连超时、凭据锁屏、网络无IPv4或采集失败
  当达到有界停止条件
  那么保留失败和原件，不通过重启切网重试制造成功，完成可执行恢复
## 排除范围
反虚拟化或随机崩溃预防、原神、修改运行时、物理断电封板。
