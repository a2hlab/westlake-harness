spec: task
name: "T56 current61b ordinary desktop reentry observation"
inherits: project
depends: [t55-61b-demo-current-state]
satisfies: [REQ-TTVIDEO]
---
## 意图
在T55当前61b身份上区分正常图标首次启动与用户关闭后再打开白屏。直接复用已验普通UI入口取得最小事实，不以5cd历史替代61b。
## 已定决策
- 唯一板61b0657200000000000000000324012c；T55 boot350d374d仅作历史参考，每次fresh核boot、锁、宿主HAP完整SHA、活动cfg/ROOT/guardian身份及实际电源前像。未知或漂移先停并交外环，不猜当前值。
- 持本轮board_note独占锁，使用现成普通UI命令；先目读当前屏幕，正常唤醒/无密码上滑解锁/Home，从当前layout识别精确头条图标与bounds，禁止旧坐标猜点、aa start或手工启动后台进程。
- 最多两次图标点击：第一次观察最长120秒，保留启动后30秒/120秒截图及同boot现有进程stat/guardian状态、事件和有界hilog。只在明确出现头条内容后用普通最近任务UI关闭该宿主卡片，再从桌面点同一图标观察最长120秒；这是automated_desktop_click，不冒称用户亲手触屏。
- 最近任务卡片身份必须来自当前layout/截图；不能用信号、force-stop、清数据或关闭其他应用替代；无法辨认就交unknown。首启白屏不继续重复点；遇密码、权限提示、拒绝或未知操作结果立即停止并保留失败。
- 不改HAP、运行时、cfg、guardian、权限、APK、冻结项；不重启，不执行T38、REA、debugger、environ/FD2。脚本记录原始argv/start/end/stdout/stderr/rc和正文状态；ui造成电源超时变化须恢复本轮前像并读回。
- 20分钟内停止观测，保留10分钟恢复电源/释锁；锁释放后才写长报告。截图只证明实际可见内容，不把宿主/进程READY当头条信息流。自然退出仅记现象，不研究随机崩溃。
- 本卡是人工读图的现场观察，测试选择器仅占位且未实现；不得宣称lifecycle PASS，不为低风险观察新增镜像测试套件。结论字段逐项写observed/failed/unknown及原件引用。
- 外环现场addendum（首启结果保留，不改判）：T56当前boot的s120事件已记child6243严格退出与AWAITING_REENTRY，30秒和120秒均白屏。允许使用原第二次点击额度，从正常Home回桌面停留至少3秒，再按新layout确认同一图标后点击一次，观察120秒；这是“自然退出后再点图标”单独观察，不冒称“正常关闭后重开”通过，不重置原窗口预算，不诊断/诱发崩溃。若已经释锁则本卡不自动开新窗。
## 边界
### 允许修改
- benchmark/2026-10-23-61b-normal-icon-reentry/**
- 私有$HOME/.local/share/westlake/61b-normal-icon-reentry-20261023/**
- 持锁下61b普通桌面UI、唤醒、截图临时文件及实际电源前像恢复
### 禁止
- 其他板、源代码、构建、部署、重启、卸载、用户数据、进程信号、权限、运行时、守护编排、T38路径及已拒绝操作重试；不得提交推送。
## 验收标准
场景: 当前图标启动与正常关闭重开
  审核: human
  测试: existing_61b_normal_ui_receipts
  假设fresh身份完整且本轮持独占锁
  当从目读确认的当前桌面图标启动并在有内容后正常关闭再点开
  那么分别保存首启和重开实际截图与有界只读状态，并恢复实际电源前像后释锁；未观察到内容不得判通过
场景: 身份不明或普通UI操作失败
  审核: human
  测试: existing_61b_normal_ui_receipts
  假设身份漂移、找不到精确图标、首启白屏或任一步被拒
  当达到该停止条件
  那么保留原始回执并停止后续操作，不猜坐标不绕过拒绝，不将未执行重开判失败根因
场景: 恢复或证据缺失
  审核: human
  测试: existing_61b_normal_ui_receipts
  假设截图、进程身份或电源恢复有缺口
  当汇总结果
  那么标unknown与具体缺项，不宣称封板、断电验证、白屏修复或lifecycle通过
场景: 已自然退出后的图标观察
  审核: human
  测试: existing_61b_normal_ui_receipts
  假设本轮已记录严格child退出和AWAITING_REENTRY且仍持原锁
  当用剩余一次额度正常Home停留后从当前图标重新打开
  那么独立记录自然退出后的新画面与事件，保留首启失败和正常关闭未执行的原判，原恢复截止不变
## 排除范围
实现修复、随机崩溃根因、视频声音复验、断电冷启动、全115应用验收与原神。
