spec: task
name: "T77 historical agent action versus ordinary icon evidence comparison"
inherits: project
satisfies: [REQ-TTVIDEO]
---
## 意图
用户问为何agent能启动而手点白屏，并要求Codex静态与REA。对既有成功和失败执行记录做独立入口对照，先核是否真的存在agent专用成功路径；不得将执行者身份当因果或将旧成功包装成冷启动验收。
## 已定决策
- 仅本地现有公开报告和普通命令回执：T34最终演示、T61B、T68、T72、T75 C、T76，既有T55 rea报告可作历史包元数据证据。分别列输入方式、调用命令、boot、是否补启动/部署、时钟、截图结果和证据覆盖；未覆盖项unknown，不能以未看到命令证明未发生。
- T75 C实际是一回UITest桌面点击且120秒白屏，不能说agent点击现在通过。T72一次同boot重开出现feed但随后退出，与冷启动分开；T61B历史首启成功也保留，不删反例。
- T55中REA open_binary曾因客户端approval policy never被拒，此卡不重试同调用、不换CLI/车道/上下文规避、不改权限。当前REA仅记录该已知执行缺口；不报新REA结果。已有包元数据/源码摘要和新REA反编译是不同证据等级。
- 不读T71故障/内存记录，不分析T74已拒的watchdog/reentry源码或同等替代件，不继续T38路径，不启动设备、进程、服务或构建。可读既有普通UITest argv/rc/start/end、截图、普通状态和源报告引用。
- 限时8分钟首交README.md/results.json和精简对照表，候选解释必须有证据并标非因果；若没有确定差异则明确unknown，不发明修复。只commit本车道分支不push；human证据审核，不声明未实现测试通过。
## 边界
### 允许修改
- benchmark/2026-10-23-launch-path-evidence-comparison/**
### 禁止
- 板写或设备调用、运行时/配置改动、被拒分析/工具调用重试、任何审批配置修改、他人工作树修改、故障归因
## 验收标准
场景: 已有回执区分成功路径和普通点击
  审核: human
  测试: launch_path_evidence_comparison_review
  假设现有记录包含T61B成功与T75 C失败
  当逐项核命令argv和boot及截图来源
  那么对照表逐项附SHA/路径并区分操作者和调用入口，同boot重开不替代断电首启
场景: 回执缺失或REA未执行
  审核: human
  测试: launch_path_evidence_comparison_review
  假设某步骤覆盖不足或既有REA被客户端拒绝
  当形成结论
  那么对应字段unknown且REA明确未执行，不重试规避、不把无证据当路径相同或根因
## 排除范围
代码修复、崩溃诊断、再次上板、T74静态分析续跑、T55被拒REA重试、全量APK。
