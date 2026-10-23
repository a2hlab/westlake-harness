spec: task
name: "T87 current boot normal icon reopen"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t86-existing-launch-output]
---
## 意图
T85同boot已正常创建child7049后退出，T86未发现足以修复的配置/依赖错误。针对用户要求的退出后正常图标重开，验证当前AWAITING_REENTRY是否能恢复信息流，并覆盖完整启动窗口；不重启、不改程序、不签断电封板。
## 已定决策
- CC唯一执行61b0657200000000000000000324012c。先只读boot、holder、当前WMS/进程/状态及截图；预期boot61aa5791-fd69-4bbb-a7b5-333b5d913c81。已有feed则保留，boot改变、其他holder或状态非AWAITING_REENTRY则停止并报新事实，不套用旧判断。
- 持独占新锁、核power前像后，只允许普通Home/解锁及新layout定位一次头条桌面点击；不aa start、不force-stop、不清hold/数据、不控制进程、不改网络/时间/配置。已有trace会话则不覆盖。
- 按T84已核help使用ability/window有限90秒4MB trace；先定位图标再启动trace，立即单次点击，不把定位耗时耗在trace内。不改trace_level、不启常驻trace。记录起止与点击时刻，trace失败不改模式重试。
- 同步读取普通WMS、ps、uptime、当前boot events/spawn：点击前、点击后前10秒以不快于1秒频率，之后30/60/90秒。截图10/30/60/90秒，逐图目读；真实feed出现即报告保留、不再页面操作，仅正常结束trace/恢复power。标签不得冒充实际采样时间。
- 新spawn拒绝或进程退出则停止追加UI动作，收取同boot普通events/spawn记录；只有明确新PID才按T86普通stderr规则只读末200行，不读取faultlog/内存、不做故障归属。未知不试第二次点击。
- 从持锁起绝对单调时间6分钟停止实验，8分钟恢复power并释锁；trace须正常结束并拉回持久目录，删除仅本轮自有trace临时件。失败回桌面；成功保留feed。记录完整argv/时段/rc/stdout/stderr且检查rc0错误正文。
- Codex只离线读新增截图和普通事件，区分真正新spawn与旧记录。仅交短results与证据路径，不因报告拖住恢复；实际普通UI恢复成功也不能替代首次断电启动验收。
## 边界
### 允许修改
- benchmark/2026-10-23-current-boot-manual-reopen/**
- 私有 $HOME/.local/share/westlake/current-boot-manual-reopen-20261023/**
- 独占61b普通UI、有限trace及本轮临时件和power恢复
### 禁止
- 重启/第二次点击、配置/运行时/网络修改、清数据/hold、进程或服务控制、源码或故障内存分析、其他设备
## 验收标准
场景: 一次普通重开显示信息流
  审核: human
  测试: current_boot_manual_reopen_review
  假设同boot处于AWAITING_REENTRY且无其他holder
  当一次图标点击并执行有界trace及截图观察
  那么真实feed截图绑定新进程与实际时间，保留画面，结束trace并恢复power释锁，不签断电封板
场景: 不适用或一次重开失败
  审核: human
  测试: current_boot_manual_reopen_review
  假设状态不符、命令错误、新spawn拒绝或90秒未见feed
  当触及失败或6分钟停止条件
  那么保留原失败证据，不重复点击或重启，8分钟内结束trace清理恢复释锁，判恢复失败
## 排除范围
代码修复部署、故障归属、断电首次启动验收、原神和全量APK。
