spec: task
name: "T86 collect existing ordinary launch output"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t85-reboot-launch-trace]
---
## 意图
T85已证明新boot普通图标点击创建child7049后退出，但没有采到该启动的普通stdout/stderr。只读收取仍留存的启动输出，判断是否存在明确的配置、类加载或依赖缺失错误；不再用截图重复确认白屏。
## 已定决策
- 补充读取（首批已终态后单独记区间，不重置首批时钟）：T70已收录普通child stderr命名/data/service/el1/public/appspawnx/adapter_child_<pid>.stderr。本次允许唯一候选/data/service/el1/public/appspawnx/adapter_child_7049.stderr，先读stat再最多末200行/128KiB，另限60秒；名称来自已知规则只是候选，不凭名称认本boot，须核mtime与T85启动时段，不能绑定就写unknown。禁止转读其他PID或faultlog，不做退出归属分析。
- CC为唯一设备读取者，设备61b0657200000000000000000324012c；开始核boot与无其他板任务。预期boot为61aa5791-fd69-4bbb-a7b5-333b5d913c81，若变化即停并报告，不重启、不点击。
- 只读已知/data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261021-r3/boots/61aa5791-fd69-4bbb-a7b5-333b5d913c81中的spawn.txt、parent-start.txt、readiness-reentry-7049-12973.jsonl、events.log、state及目录文件元数据。允许沿上述普通文本明确引用的既有stdout/stderr日志路径读取，每文件最多末200行、每文件最多128KiB；不读取shell源码或执行其中命令，不猜全盘路径。
- 不读faultlog/core/tombstone/内存，不分析信号归属或内存损坏，不重试此前被拒绝的源码读取。没有明确应用错误则结论保持unknown。所有命令argv/起止/rc/stdout/stderr保存到持久私有目录；rc0仍检查正文错误。
- 绝对单调时间预算180秒，每命令不超过20秒且不超过剩余预算；无重试、无设备写入、无trace。只读无锁时先查其他holder，有holder就停止避免并发实验干扰。
- Codex离线读新原件，仅抽取明确启动错误与PID/boot绑定；不做二次板操作。若没有日志或身份无法绑定，列明确缺口，不启动下一次实验。本卡交件只需results.json和短README，不等待长报告或提交才向外环报告关键事实。
## 边界
### 允许修改
- benchmark/2026-10-23-existing-launch-output/**
- 私有 $HOME/.local/share/westlake/existing-launch-output-20261023/**
### 禁止
- 任何设备写入、重启或点击、配置与源码修改、读取安全拒绝过的脚本、内存或故障转储分析、其他设备、未绑定boot的历史日志归因
## 验收标准
场景: 取得本次启动普通输出
  审核: human
  测试: existing_launch_output_receipts_review
  假设boot一致且无其他holder
  当180秒内读取已知普通日志并保留命令原件
  那么记录明确错误原文与文件行号及身份依据，或明确没有此类错误，不宣称已修复
场景: 缺失或读取失败
  审核: human
  测试: existing_launch_output_receipts_review
  假设boot变化、holder存在、日志缺失或命令正文错误
  当遇到失败或预算截止
  那么停止相应读取且保留失败原件，不重试、不改设备、不用旧日志补本次证据
## 排除范围
修复代码、重新复现、故障归属、封板签认、原神与全量APK。
