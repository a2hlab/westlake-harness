spec: task
name: "T123 existing 61b ordinary desktop reentry with absent child"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t107-current-demo-entry, t122-ordinary-log-suffix]
---
## 意图
61b只读快照显示现有宿主和appspawn存活而无头条child。用板上现有版本的一次普通桌面点击，区分是否新建child及是否出现信息流，验证真实手动重开路径，不部署候选、不修随机崩溃。
## 已定决策
- 唯一板61b0657200000000000000000324012c；执行前核新鲜锁/boot/进程/电源/控制文件SHA与已知T116，控制文件只取SHA不读实现。无锁、身份改变、已有别的写任务则停。
- 先取得独占锁并记录电源前像，正常唤醒后内环结合新鲜截图和layout确认只含时钟/壁纸且无凭据控件，才允许一次普通上滑并保存解锁后初始截图；不能确认则停。若已见可用头条界面则保留并停止后继操作；有凭据屏则停，不输入凭据。
- 若初态为桌面或宿主白屏且无article child，普通Home并遍历实际桌面布局定位唯一可见可操作的org.westlake.imehost.EntryAbility图标，最多12页，每页不超过一次划动；找不到或不唯一则停。只允许一次图标点击，不直接调用宿主/child启动接口、不杀进程/重启/部署。
- 点击后采实际10/30/60/90/120秒截图、ps、boot及现有状态文本。截图为判定，首个feed即报并保留，不继续新闻视频操作。不得把alive/READY当信息流。
- 单命令10秒上限，截图/布局操作可到15秒；总实验8分钟，最后2分钟只恢复power前像并释锁。失败后普通Home回桌面；原件持久保存，临时截图不覆盖旧证据。
- 准备阶段不设备写；外环检查普通UI驱动/恢复路径后执行。锁屏图不再单独等待外环回执，最终桌面/白屏图仍必须外环图审方可Home/点击；不改120秒图审、180秒点击、360秒主动工作/480秒总限。首轮仅上滑、未点击且cleanup已确认后的新窗口另起run_id，不续旧计时。所有原始argv/stdout/stderr/rc/开始结束时间保存，不提交个人日志。明确本次是现有版本状态验证，不能当代码修复或冷启动封板。
## 边界
### 允许修改
- benchmark/2026-10-24-existing-demo-reentry/**
- tools/spec-checks/tests/current_reentry_observation.rs
- 私有 $HOME/.local/share/westlake/existing-demo-reentry-20261024/**
- 独占锁内61b普通UI、截图及电源前像恢复
### 禁止
- 5cd/5ea写、任何部署/进程控制/重启/清数据/改网络、停止对象及watchdog执行器实现、REA被拒动作、故障/保护机制分析
## 验收标准
场景: 无child的一次桌面点击
  审核: human
  测试: current_reentry_observation_receipts
  假设初始为桌面或宿主白屏且无article child并持有正确板锁
  当唯一可见图标被点击一次并按有界时段观察
  那么保存真实截图/身份/rc及电源恢复释锁回执，分别报告新child和真实feed，不报告修复或冷启动封板
场景: 初态可用或条件不满足
  审核: human
  测试: current_reentry_observation_receipts
  假设已有可用头条界面或出现锁冲突身份不明凭据屏无唯一图标
  当触发停止条件
  那么不继续点击，保留原件并恢复已改变的电源状态和释放自持锁
## 排除范围
新控制件部署、强制杀进程制造退出、随机退出预防、UI外接口启动、自动重试和物理断电验收。
