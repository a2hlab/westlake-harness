spec: task
name: "T96 deployed runtime ordinary log clock"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t94-startup-clock-binding]
---
## 意图
T94本地源码未找到TOUCH21计时实现，但外环在历史已验运行库SHA完全匹配的本地封板副本中确认了该字符串。用REA只读定位日志引用和计时表达式，补上日志时间单位/时钟域证据。
## 已定决策
- Codex唯一分析者，先读reverse-engineer-anything技能并核现有REA会话，优先复用匹配目标，不改客户端配置或审批。使用本地benchmark/2026-10-12-v1-seal-execution/restore-v6-full-package/runtime/liboh_android_runtime.so，SHA256为8ab6742d58de5b9df94a2bfa80cebed46f136c0251083793fcbef8293cc23ab1、2206152字节。
- 只定位TOUCH21-POLL/TOUCH21-WAKE字符串及直接引用函数的计时调用、单位换算。记录REA实际工具回执/Evidence ID、函数/地址和不完整范围；静态结果不冒充运行时观察或源码完整性。
- 先字符串/符号和已有分析结果，必要时Ghidra只读反编译相关函数。无设备操作、调试器、内存/故障归属、修改二进制、T91或先前停止对象；工具拒绝立即保存原文并停止，不换入口重试。
- 5分钟首次交件，工具长任务用真实句柄报状态，不以等待超时重开。结束关闭自建REA会话。结果只在自己analysis树、持久目录；已知git权限不再重试，外环收文件。
## 边界
### 允许修改
- benchmark/2026-10-23-runtime-clock-rea/**
- 私有 $HOME/.local/share/westlake/runtime-clock-rea-20261023/**
### 禁止
- 设备、运行时或二进制修改、CC分析、先前停止对象与动作、权限配置
## 验收标准
场景: 找到日志计时表达式
  审核: human
  测试: runtime_clock_rea_review
  假设目标SHA符合且REA可用
  当仅检查标记引用及相关计时指令
  那么列出实际调用、单位和证据地址，无法证明的时钟跨域关系保持unknown
场景: 工具失败或证据不足
  审核: human
  测试: runtime_clock_rea_review
  假设目标不符、工具拒绝或未能定位引用
  当首次检查失败或达到首交时限
  那么保留真实回执和缺口，不猜测单位，不换入口重试被拒操作
## 排除范围
白屏修复部署、崩溃或内存分析、冷启动签认。
