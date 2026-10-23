spec: task
name: "T72 ordinary desktop recovery and content check"
inherits: project
depends: [t71-passive-first-exit-attribution]
satisfies: [REQ-TTVIDEO]
---
## 意图
用户重申头条得点开。独立于已停止的崩溃归属诊断，检查当前桌面一次普通点击是否能进入信息流和内容；成功可说明当前可展示，但不替代开机首启稳定性验收，不宣称修复。
## 已定决策
- 仅61b0657200000000000000000324012c，先只读核boot/板锁/power与网络连接；无写锁才持独占锁。复用T68普通UI辅助工具，保留原始argv/时间/rc和实图。原有私有目录只读，新证据另持久目录。
- 若没有连接网络，停止交现状，不改网络。如果已连接，则普通唤醒解锁、回桌面并用新鲜layout定位头条图标；不得直接aa/bootstrap/guardian调用，不重启、不终止进程、不清数据、不改运行时。
- 只点击一次桌面图标（如果头条已显示信息流则保留不重新点击），在30/120秒实图检查；出现信息流后点一条普通文章、看正文并应用内返回。不得循环点击、查崩溃日志或分析异常原因。
- 如果正文与返回通过，则停留信息流供用户当前展示；白屏或退出则截图并停，不再重试。5分钟内停止实验，10分钟内恢复进入前power数值读回并释锁；不能把成功重新打开当作原先开机首启已修复。
- 只commit不push；测试选择器尚未实现，仅人工回执，不能报lifecycle PASS。该卡不重新执行T71被拒绝诊断，也不调用REA/debugger/内存/符号分析。
## 边界
### 允许修改
- benchmark/2026-10-23-ordinary-desktop-recovery-check/**
- 私有$HOME/.local/share/westlake/ordinary-desktop-recovery-check-20261023/**
- 持锁下普通桌面与应用UI操作及power恢复
### 禁止
- 崩溃诊断、运行时修改、进程控制、重启、网络配置变更、其他板、第三方安全机制分析。
## 验收标准
场景: 当前桌面进入内容返回
  审核: human
  测试: existing_ordinary_desktop_recovery_receipts
  假设网络已连接并持有当前板独占锁
  当一次普通桌面点击进入信息流后打开正文并返回
  那么每步保留实图并停留信息流，恢复power释锁，明确仅当前重开通过不等于开机首启修复
场景: 无网络或界面失败
  审核: human
  测试: existing_ordinary_desktop_recovery_receipts
  假设网络未连接、120秒白屏或内容失败
  当到达对应停止条件
  那么保留失败且不重试，恢复power释锁，不诊断失败原因
## 排除范围
崩溃归因与修复、开机首启稳定性签认、全量APK、物理断电。
