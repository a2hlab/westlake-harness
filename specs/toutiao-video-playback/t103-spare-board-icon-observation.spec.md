spec: task
name: "T103 spare-board ordinary icon observation"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t100-launch-time-reconciliation, t101-demo-current-state]
---
## 意图
61b保留现有长时存活实例，在5cd用一次普通桌面点击观察当前可复现的白屏类型和启动阶段。此次只取得基线，不声称新运行时或修复已验证。
## 已定决策
- CC唯一上板执行者，仅5cd1e3dd00000000000000000923012c；先只读held、boot、power、当前目标进程/前台和网络状态。其他holder或目标不明停止。61b不操作；不读取T91部署预检对象、配置或停止源码。
- 初态已有活头条child则不终止、不重复暖启动，报告该限制并收口；没有活child才在独占锁内正常唤醒/解锁（遇凭据界面停止），回桌面用新布局定位图标并只点一次。无aa start、清数据、杀进程、重启、WiFi/权限或运行时改变。
- 点击后最多100秒记录普通现状，截图5/10/20/40/60/90秒，实际起止均记录不按计划填。首次feed后保留界面；无feed不点第二次。不得把现有guardian READY当新上屏。明确是否新child、白屏/错误页/feed和身份，未知不猜。
- 整窗6分钟停止观察、8分钟恢复/释锁，恢复原power参数并读回；可用原已审采集器，原件持久，record.json captured/facts原样引用。失败不重试；还原动作有原始回执，不改设备基线。
## 边界
### 允许修改
- benchmark/2026-10-23-spare-board-icon-observation/**
- 私有 $HOME/.local/share/westlake/spare-board-icon-observation-20261023/**
### 禁止
- 61b/5ea、应用数据、部署、重启/杀进程、REA、此前停止对象
## 验收标准
场景: 初态无child且图标明确
  审核: human
  测试: spare_board_icon_observation_review
  假设白名单空闲且当前布局可定位目标图标
  当单次普通图标点击并按有界采样观察
  那么给真实截图/身份/时间和新启动现象，恢复原power并释锁，不称修复
场景: 已有实例或前置失败
  审核: human
  测试: spare_board_icon_observation_review
  假设已有活child、holder冲突、凭据界面、未知目标或读取失败
  当前置或窗口停止条件触发
  那么不强行制造初态或换板，保留真实原因并完成必要恢复
## 排除范围
冷断电保证、白屏修复、随机崩溃预防。
