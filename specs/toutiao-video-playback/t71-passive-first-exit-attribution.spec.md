spec: task
name: "T71 passive first-launch exit attribution"
inherits: project
depends: [t70-current-launch-readonly]
satisfies: [REQ-TTVIDEO]
---
## 意图
用户已允许看看本次首启退出归属，并要求头条桌面能点开。仅从已有系统退出记录判断T68 child8088的故障模块；若证据指向桥接源码，提出最小修复方向，若指向头条自身或没有记录则如实交界限。
## 已定决策
- 限15分钟，仅61b0657200000000000000000324012c只读；先核板锁和boot。目标历史boot33f35797-8fc2-450d-9f62-9ea5d6336b2f、child8088、12:14:24点击、12:14:57附近退出。当前boot不同不抹掉历史对象，不把PID单独当身份。
- 复用仓库scripts/lab/sc17_run.sh:64-66中已有faultlog位置知识，不执行该完整实验脚本。先列/data/log/faultlog/temp目录，仅选择能由类别、进程、PID、时间共同绑定该次退出的既有原生崩溃记录。最多3个候选；如果没有匹配则最多核一份已有同窗系统日志，不全盘搜、不制造新崩溃。
- 仅保存记录头部、Reason、fault thread与模块/栈摘要，不读取内存内容、寄存器转储或账户信息。原始命令回执存私有持久目录；公开只放脱敏小摘要及SHA。systemwarning不是native crash，其他PID/旧boot记录不代替目标。
- 若找到模块PC，只与本地已有对应源码/符号/构建ID核对，记录匹配强度；首个栈模块不是故障根因证明。最多一个有依据的修复建议，不改代码、不部署、不重启应用。本卡不使用REA、debugger、hook、注入、信号、权限变更或第三方安全机制分析；先前拒绝的工具路径不重试。
- 只commit不push。没有精确匹配就交unknown与已查范围；人工回执选择器未实现，不报lifecycle PASS。本卡完成不等于首启验收通过。
## 边界
### 允许修改
- benchmark/2026-10-23-first-exit-attribution/**
- 私有$HOME/.local/share/westlake/first-exit-attribution-20261023/**
### 禁止
- 设备写入、应用重开、重启、内存/寄存器读取、debugger/REA/hook、第三方反虚拟化分析、构建部署、其他设备。
## 验收标准
场景: 找到目标退出记录
  审核: human
  测试: existing_passive_first_exit_attribution_receipts
  假设存在绑定目标PID和时间的原生退出记录
  当只读Reason和模块摘要并核本地符号来源
  那么给身份时间关联、记录类别、模块PC和来源哈希及归属置信度，不将候选解释写为根因
场景: 记录缺失或不匹配
  审核: human
  测试: existing_passive_first_exit_attribution_receipts
  假设目录无匹配、只有syswarning、读失败或15分钟预算到达
  当结束只读核查
  那么保留缺口和搜索边界，不扩大权限、不重新启动应用、不虚报修复
## 排除范围
关闭后重开、随机崩溃机制修复、网络排障、全量APK、原神。
