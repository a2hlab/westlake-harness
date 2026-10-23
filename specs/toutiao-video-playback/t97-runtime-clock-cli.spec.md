spec: task
name: "T97 authorized offline REA CLI clock inspection"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t96-runtime-clock-rea]
---
## 意图
T96的MCP会话状态查询未执行，不能视作本地分析结果。按REA已安装技能connection-and-recovery的unattended CLI恢复流程，在用户此前明确授权的本地REA只读分析范围内检查运行库日志计时；保留原客户端拒绝，不重试该MCP查询或改变审批设置。
## 已定决策
- 仅Codex内环执行已安装REA 6.7.0公共CLI。先核目标SHA和已装Ghidra/Java路径，使用本地封板库benchmark/2026-10-12-v1-seal-execution/restore-v6-full-package/runtime/liboh_android_runtime.so，SHA8ab6742d58de5b9df94a2bfa80cebed46f136c0251083793fcbef8293cc23ab1。无下载/安装/网络/设备。
- 本地公开help已核：rea search <path> TOUCH21 --kind strings --provider ghidra --format json；后继只查询所得引用和必要计时函数，可用同一持久snapshot减少重复分析。保留argv/rc/完整输出/Evidence；实际工具无结果不写REA完成。
- 不调用被拒binary_session、不改任何审批/配置、不接续T91或其他内容停止动作。CLI若被宿主权限拒绝也立即停止，不换入口；此流程只分析普通日志计时，不分析故障/内存，不修改目标。原T96停止记录不变。
- 持久输出、5分钟首交；长Ghidra任务保留真实句柄并报告，不因观察超时重启。公开结果只包含目标hash/工具回执/计时指令与限定结论。时钟对齐证据不全仍unknown。
- Addendum T97D：CLI失败已终止。仅做一次本机只读环境诊断：读取实际Swift编译器位置/版本、xcode-select和已有SDK版本元数据、已安装REA的compiler/cache选择代码、现有Java/Ghidra路径。不得编译测试、重跑REA分析或doctor、创建缓存、修改环境/权限/配置、下载或安装。2分钟交最小成因/兼容现有工具链候选或明确缺口；此诊断不解除原拒绝，也不授权后继执行。
## 边界
### 允许修改
- benchmark/2026-10-23-runtime-clock-cli/**
- 私有 $HOME/.local/share/westlake/runtime-clock-cli-20261023/**
### 禁止
- 设备与运行时改动、MCP审批配置、先前内容停止对象、目标二进制修改、CC分析
## 验收标准
场景: 本地CLI成功给出静态结果
  审核: human
  测试: runtime_clock_cli_review
  假设目标SHA符合且现有provider可用
  当CLI只检查日志计时调用与单位转换
  那么保存实际Evidence和地址，区分静态表达式与运行时对齐，不宣称白屏已修复
场景: CLI失败或未完成
  审核: human
  测试: runtime_clock_cli_review
  假设出现权限拒绝、provider失败或真实任务未终止
  当检查结果或首交期限到达
  那么分别保留失败或报告活句柄，不重试拒绝、不伪造分析结论
## 排除范围
修复部署、审批策略修改和冷启动签认。
