spec: task
name: "T62 61b demo homepage handoff after one reboot"
inherits: project
depends: [t61-61b-test24-reboot-feed]
satisfies: [REQ-TTVIDEO]
---
## 意图
T61B已证重启自动联网与桌面首点进入头条信息流，内容点击后child退出失败保留。用户要一块可拿去展示的板：本卡只做最终交付摆放，一次标准重启后从桌面首点头条，信息流可见即停在首页交付；不是内容验收、不是完整封板。
## 已定决策
- 唯一板61b0657200000000000000000324012c；fresh只读核boot、锁、宿主HAP b18978b8、cfg、guardian、无遗留采集任务、实际power前像与WiFi状态。若发现他人持锁或用户现场操作则只读停止；T61证据不覆盖。
- 新board_note独占锁下执行一次标准hdc target boot，就绪判断去尾部空白后比较true，自动联网等待上限120秒；不运行手工bootstrap、aa、guardian或启动命令，不改任何runtime、cfg、权限或数据。
- 从当前layout识别的桌面头条图标首点一次，最多等待120秒，按30秒与到点截图读图；信息流可见即停在头条首页，不点文章或视频、不滚动、不force-stop、不杀进程。无信息流则保存失败截图停止，不反复重试、不重开。
- 交付后恢复实际power前像并读回、释放锁，保留头条首页原截图。结果字段明确demo_homepage_only与content_operation_not_accepted，不签完整封板，不宣称物理断电或真人触屏。
- 最多10分钟停止操作、20分钟闭窗；原始argv/start/end/stdout/stderr/rc与截图SHA持久保存，沿既有脚本，不新增工具。人工读图回执入口未实现，不宣称lifecycle PASS。
## 边界
### 允许修改
- benchmark/2026-10-23-61b-demo-homepage-handoff/**
- 私有$HOME/.local/share/westlake/61b-demo-homepage-handoff-20261023/**
- 持锁下61b一次标准软件重启、桌面头条首点、截图与power前像恢复
### 禁止
- 其他板、源码、构建、部署、回滚、卸载、清数据、进程信号、权限、运行时、守护编排、T38、REA、environ/FD2、网络与凭据修改、文章或视频点击；不push。
## 验收标准
场景: 重启后首页交付
  审核: human
  测试: existing_61b_demo_homepage_receipts
  假设fresh身份一致、无他人锁且本轮独占锁有效
  当一次标准重启自动联网后从桌面首点头条并出现信息流
  那么停在头条首页，保存首页截图与联网时间线，恢复power前像并释锁，结果标demo_homepage_only
场景: 无信息流或联网超时
  审核: human
  测试: existing_61b_demo_homepage_receipts
  假设120秒内未自动联网或首点120秒仍无信息流
  当到达上限
  那么保存失败截图与状态，停止不重试，恢复power释锁并报告缺口
场景: 他人锁或现场操作
  审核: human
  测试: existing_61b_demo_homepage_receipts
  假设fresh读到他人持锁或屏幕正被人操作
  当准入检查
  那么只读停止，不加锁不重启，报告现场状态
## 排除范围
内容打开与返回验收、音视频、关闭重开、随机崩溃诊断、其他APK、物理断电和完整封板。
