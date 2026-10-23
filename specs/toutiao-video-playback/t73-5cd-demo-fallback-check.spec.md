spec: task
name: "T73 5cd ordinary UI demonstration fallback check"
inherits: project
depends: [t72-ordinary-desktop-recovery-check]
satisfies: [REQ-TTVIDEO]
---
## 意图
用户急需头条可点开演示；61b当前不稳定。利用已授权空闲5cd的现有安装做普通UI检查，判断能否提供临时演示备选。该卡不修复或诊断61b，不替代61b开机首启目标，不重复T71被拒的分析。
## 已定决策
- 仅5cd1e3dd00000000000000000923012c，先只读锁、boot、power、网络、HAP/两cfg指纹及当前窗口；他人锁/任务活动则停止。只记录现状，不要求与61b相同，不部署或改配置。原始回执持久保存。
- 网络已连接才持锁操作；没有网络则停止，不改变网络。普通唤醒解锁；若已经是头条信息流，保留当前状态直接验正文返回并注明没有测桌面首点。否则通过新鲜layout找到真实桌面图标（最多两分钟），只点一次，不猜坐标、不执行aa/bootstrap/guardian。
- 至多120秒等待，以30/60/120秒截图和实际UI为准。出现信息流后立即普通文章正文、应用内返回、上下滚动并观察60秒，每步保留截图。无屏/退出/错误页则停止，不重复启动。
- 成功留信息流供用户当前展示；失败回桌面。10分钟内停止实验，15分钟内恢复原power并读回释锁。只报告当前开机周期可用性；未做断电重启、不签61b或全量APK通过。
- 不读故障记录、不做源码/内存/符号分析，不调用REA/debugger/hook，不改变运行时或进程控制。只commit不push；人工选择器未实现，不报lifecycle PASS。
## 边界
### 允许修改
- benchmark/2026-10-23-5cd-demo-fallback-check/**
- 私有$HOME/.local/share/westlake/5cd-demo-fallback-check-20261023/**
- 持锁下5cd普通UI与power恢复
### 禁止
- 61b/5ea操作、部署、重启、清数据、进程控制、网络修改、崩溃分析、重复尝试。
## 验收标准
场景: 当前5cd可作为演示备选
  审核: human
  测试: existing_5cd_demo_fallback_receipts
  假设5cd无锁且已连接网络
  当普通UI进入信息流、文章正文、返回和滚动并观察60秒
  那么各步留实图、恢复power释锁并说明只验证当前5cd，不代替61b修复
场景: 前置或交互未通过
  审核: human
  测试: existing_5cd_demo_fallback_receipts
  假设网络不可用、锁占用、图标未找到或120秒/内容失败
  当达到停止条件
  那么保存失败、恢复power释锁，不反复点击或改变系统配置
## 排除范围
61b修复、断电开机保证、视频重复验收、崩溃归因、其他APK。
