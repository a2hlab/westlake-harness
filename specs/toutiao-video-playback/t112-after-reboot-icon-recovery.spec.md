spec: task
name: "T112 ordinary icon recovery after recorded reboot failure"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t109-spare-board-power-entry]
---
## 意图
T109首次软件重启点击失败已完整留证，进程变化7011→9860→未观测。此卡单独验证用户要求的退出后再点桌面图标恢复，不改变T109失败判定，也不宣称预防随机退出。
## 已定决策
- 先核T109闭窗且fresh无目标child；如实例自动已恢复则不重复启动，记录实际图。CC唯一上板执行者，仅5cd1e3dd00000000000000000923012c；先只读held、boot、power、当前目标进程/前台和网络状态。其他holder或目标不明停止。61b不操作；不读取T91部署预检对象、配置或停止源码。
- 初态已有活头条child则不终止、不重复暖启动，报告该限制并收口；没有活child才在独占锁内正常唤醒/解锁（遇凭据界面停止），回桌面用新布局定位图标并只点一次。图标发现最多16个不同WorkSpace页，遇相同页边界停止；以每页实际控件ID、bundle、ability、bounds核目标，不抄历史坐标。不能因前三页没有目标就宣称全桌面缺失。完整找不到则交页清单和一次当前截图，不安装/重排。无aa start、清数据、杀进程、重启、WiFi/权限或运行时改变。
- 点击后最多100秒记录普通现状，截图5/10/20/40/60/90秒，实际起止均记录不按计划填。首次feed后保留界面；无feed不点第二次。不得把现有guardian READY当新上屏。明确是否新child、白屏/错误页/feed和身份，未知不猜。
- 整窗8分钟停止观察、10分钟恢复/释锁，恢复原power参数并读回；可用原已审采集器，原件持久，record.json captured/facts原样引用。失败不重试；还原动作有原始回执，不改设备基线。
## 边界
### 允许修改
- benchmark/2026-10-23-after-reboot-icon-recovery/**
- 私有 $HOME/.local/share/westlake/after-reboot-icon-recovery-20261023/**
### 禁止
- 61b/5ea、应用数据、部署、重启/杀进程、REA、此前停止对象
## 验收标准
场景: 初态无child且图标明确
  审核: human
  测试: after_reboot_icon_recovery_review
  假设白名单空闲且当前布局可定位目标图标
  当单次普通图标点击并按有界采样观察
  那么给真实截图/身份/时间和新启动现象，恢复原power并释锁，不称修复
场景: 已有实例或前置失败
  审核: human
  测试: after_reboot_icon_recovery_review
  假设已有活child、holder冲突、凭据界面、未知目标或读取失败
  当前置或窗口停止条件触发
  那么不强行制造初态或换板，保留真实原因并完成必要恢复
## 排除范围
冷断电保证、白屏修复、随机崩溃预防。
