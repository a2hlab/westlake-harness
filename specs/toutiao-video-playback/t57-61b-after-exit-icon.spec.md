spec: task
name: "T57 ordinary icon after observed exit on61b"
inherits: project
depends: [t56-61b-normal-icon-reentry]
satisfies: [REQ-TTVIDEO]
---
## 意图
T56已观察首启白屏、child6243退出和AWAITING_REENTRY，并于10:25:23释放锁。本卡仅检验用户要求的“退出后再点图标能否打开”，不诊断随机崩溃，不改T56首启失败结论。
## 已定决策
- 唯一板61b0657200000000000000000324012c；重新只读核boot、活动cfg/ROOT、宿主HAP b18978b875098bc66f1ee78e471ef64c7899978bf46052502c41801f168e9ff0、当前guardian状态、屏幕和实际power前像。绑定当前观察，不引用旧锁或旧power值；已不是AWAITING_REENTRY则先报告，不制造退出。
- 新board_note独占锁下只用现成普通UI：唤醒/无密码上滑/Home，当前截图/layout确认桌面停留至少3秒；从当前布局识别头条图标，点击一次。不是权限或安全工具拒绝重试，也不运行T38编排。
- 点击后30秒/120秒截图和同boot现有state/events/WMS/进程stat，只读绑定新实例或无实例。长等待以绝对截止为准；无论成功失败不追加第三次点击、不清数据、不force-stop、不信号、不手启守护、不重启不部署不读取environ/FD2。
- 锁内实验最多10分钟，另留5分钟恢复实际power前像并核对、释放锁；先恢复后报告。原始命令、时间、stdout/stderr/rc及截图SHA持久保存，目读实际内容，界面白屏即未通过。
- 若密码/权限提示、操作拒绝、图标身份或结果未知，停止后续动作；不更换入口或模型绕过。正常关闭未执行、物理断电未执行须分列，不以本次成功替代它们。
- 不加通用编排工具或低风险镜像测试。测试选择器为未实现的人工回执入口，不称lifecycle PASS；外环独立读图及核原始证据。
## 边界
### 允许修改
- benchmark/2026-10-23-61b-after-exit-icon/**
- 私有$HOME/.local/share/westlake/61b-after-exit-icon-20261023/**
- 持锁下61b正常桌面UI、截图与实际power前像恢复
### 禁止
- 源码/二进制/冻结项/权限/数据/第三方崩溃诊断/设备重启/进程信号/守护编排/T38/REA/父environ/FD2/其他板；不提交推送。
## 验收标准
场景: 已退出后的普通图标启动
  审核: human
  测试: existing_61b_after_exit_receipts
  假设fresh状态为AWAITING_REENTRY且本轮独占锁有效
  当正常回到当前桌面停留后点击确认的头条图标一次
  那么记录30秒及120秒画面与是否出现新实例，恢复实际power前像并释放锁；只以实际内容判断该次恢复是否成功
场景: 身份不明或拒绝
  审核: human
  测试: existing_61b_after_exit_receipts
  假设fresh身份不符、图标无法确认或操作被拒绝
  当准备动作或读取结果
  那么停止后续动作并保留原始失败，不制造退出、不扩大权限、不重试其他入口
场景: 仍为白屏或证据缺失
  审核: human
  测试: existing_61b_after_exit_receipts
  假设120秒仍无头条内容或证据/恢复缺失
  当汇总结果
  那么分别报告failed或unknown，保留T56首启失败，不宣称封板、正常关闭重开或断电验收通过
## 排除范围
白屏修复实现、随机崩溃诊断、正常最近任务关闭验证、全115个APK、声音复验和原神。
