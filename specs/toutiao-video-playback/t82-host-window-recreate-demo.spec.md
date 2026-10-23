spec: task
name: "T82 bounded ordinary host recreation for current demo"
inherits: project
satisfies: [REQ-TTVIDEO]
---
## 意图
当前普通点击已证白屏，旧启动尝试留下 FOREGROUND_HOST_NOT_READY 与后续 hold。对自有鸿蒙宿主做一次标准关闭及桌面重开，检验新窗口是否恢复当前演示；不清数据、不诊断随机退出、不当作冷启动修复。
## 已定决策
- 仅 CC 执行 61b0657200000000000000000324012c，fresh 只读锁/boot/power/网络/本包进程后持新锁。若当前已有真实 feed 则直接保留，或网络不通则停止。保留全部命令 argv、时间、rc、输出及实图。
- 首选标准最近任务中关闭已确认的头条宿主卡；若采用系统 aa force-stop，仅在本机 aa help 明确支持其语法且包名经 bm 确认为 org.westlake.imehost 后执行一次。此卡明确授权该自有宿主正常终止，不直接 kill PID，不终止 appspawn/守护服务，不清应用数据、不安装、不重启设备。若入口无法确认则停止，不猜手势或命令。
- 关闭后核自有宿主窗口/进程变化，再从新鲜桌面 layout 定位一次头条图标点击。不得 aa start 或手工 bootstrap 代替桌面点击。新旧 PID/window ID 分开记，10/30/60/120 秒取实图；有 feed 即保留供演示，不追加正文测试。
- 若仍白屏或现有组件没有自动恢复，则保留失败，不重放启动、不清 hold、不改守护脚本或配置。5 分钟停止实验，10 分钟内恢复本窗 power 前像并释锁。Codex 仅离线核对产物，不访问设备。
- 只交 benchmark 报告和新持久回执；公开不含凭据或个人数据。原先失败和启动拒绝不覆盖；这次恢复成功也不能签物理断电首次启动通过。
## 边界
### 允许修改
- benchmark/2026-10-23-host-window-recreate-demo/**
- 私有 $HOME/.local/share/westlake/host-window-recreate-demo-20261023/**
- 已持锁 61b 标准宿主关闭、一次普通桌面图标点击及电源前像恢复
### 禁止
- 清数据、系统重启、桥接运行时或配置改动、直接进程 kill、其他包关闭、appspawn/守护服务控制、故障/源码/内存分析、权限策略变化
## 验收标准
场景: 新宿主窗口后信息流恢复
  审核: human
  测试: host_window_recreate_demo_receipts_review
  假设包名和标准关闭操作已确认且现场可操作
  当关闭宿主并一次普通桌面重开
  那么记录新窗口身份及真实 feed 截图，保留供用户演示，恢复 power 并释锁，不签冷启动修复
场景: 标准操作不明或恢复失败
  审核: human
  测试: host_window_recreate_demo_receipts_review
  假设无法确认关闭入口、网络不通或120秒仍无feed
  当达到相应停止条件
  那么保留错误与截图且不重复执行，恢复 power 并释锁，不清数据和hold
## 排除范围
守护源码诊断、第三方崩溃修复、强制跳过启动检查、完整封板签认及其他 APK。
