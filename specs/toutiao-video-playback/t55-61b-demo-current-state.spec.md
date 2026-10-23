spec: task
name: "T55 current61b demo inventory and white-screen intake"
inherits: project
depends: [t54-service-source-chain]
satisfies: [REQ-TTVIDEO]
---
## 意图
按用户新优先级暂停原神，确认61b演示封板当前状态，先核头条重开白屏与冷启动要求。按用户明示移除历史排除的13个APK，不把历史115首屏展示冒充当前断电重启可手点启动。
## 已定决策
- 唯一设备61b0657200000000000000000324012c；先读锁、boot、bm清单和当前宿主/运行时配置，未获锁不写。复用已有board_note锁；单窗口不超过30分钟，所有实际argv/stdout/stderr/rc/时间持久记录。
- 排除对象只能来自benchmark/2026-10-14-final61b-full128-outer/demo-list.json的13项，逐项绑定peer原始record SHA和包名。先核现安装信息及可恢复APK来源；卸载用bm uninstall -k保留用户数据，已不存在只记absent，不卸载其他包。前后包集合差必须等于实际成功目标子集；头条/BoatAttack不得属于目标。
- 首轮头条核查只读：当前boot、宿主bundle信息、活动cfg与精确ROOT、guardian/parent/child的stat和现有事件状态、桌面/前台截图。不得读environ/FD2，不做T38流程，不启动guardian，不杀进程，不改权限/运行时或清数据。5cd历史T45/T54结论不得当61b当前根因。
- 读取最新61b演示签认与后续头条变更记录，分别标历史签认、现在指纹、安装和实际画面；没发生真实断电就写cold_power_cycle=unverified。正常软件重启也不是断电证明。本卡不重启。
- 输出小README/results以及可恢复安装映射，记录每项unknown和下一步真正阻塞。不新建通用工具或报告测试套件；保留现有工具真实退出和逐条现场证据，外环读图确认。
## 边界
### 允许修改
- benchmark/2026-10-23-61b-demo-current-state/**
- 私有$HOME/.local/share/westlake/61b-demo-current-state-20261023/**
- 持锁并完成只读核对后仅卸载13项中现存的已确认目标且保留数据
### 禁止
- 其他板、原神、运行时/权限/冻结/旧证据修改、重新安装、删用户数据、重启、进程信号、environ/FD2、T38路径/测试、修改主树或commit/push。
## 验收标准
场景: 白名单移除并保留其他安装
  审核: human
  测试: existing_61b_inventory_receipts
  假设13项排除映射绑定原始record与当前安装且独占锁持有
  当使用保留数据的卸载方式移除现存目标
  那么前后安装包集合差仅含已确认目标，缺失项如实记录，头条和BoatAttack保留
场景: 缺少身份或锁拒绝写板
  审核: human
  测试: existing_61b_inventory_receipts
  假设包名来源不符或无可恢复APK或锁被占用
  当准备清理该对象
  那么不执行卸载并记录具体缺口，不扩大名单
场景: 当前白屏与历史首屏分列
  审核: human
  测试: existing_61b_inventory_receipts
  假设已取得当前boot配置和截图
  当报告演示能力
  那么只对当前实际样本下结论，历史115首屏与13排除及未验证断电启动分开，不声称白屏已修复
## 排除范围
白屏实现、冷启动实验、全115功能验收、原神和重新研究框架权限。
