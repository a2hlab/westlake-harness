spec: task
name: "T83 bounded foreground predicate replay"
inherits: project
satisfies: [REQ-TTVIDEO]
---
## 意图
对新观察到的 FOREGROUND_HOST_NOT_READY 普通启动拒绝，仅核独立 launch-common.sh 前台窗口判据，使用既有 WMS 和进程文本做离线复现，判断是否存在可证明的解析错误。不重跑先前被停止的 watchdog/reentry 等待流程分析。
## 已定决策
- Codex 优先。仅阅读 benchmark/2026-10-21-t34-demo61b-video/reentry-retirement-01/deploy-package-r3-root/payload/launch-common.sh 中产生该拒绝的前台谓词；若依赖需要进入 watchdog.sh、reentry-common.sh 或其他被停止分析，停在边界报告缺口，不改派模型绕过。
- 输入为应急及 T82 已采普通 WMS/ps/命令输出，保留采样时间。16:13:57拒绝和16:16:05点击后hold是两次尝试，晚于拒绝的窗口不能证明当时状态。复现只用本地文本夹具，不执行板命令、启动脚本或加载产物。
- 若合法前台宿主样本被纯解析谓词误拒，另目录给最小候选与正反例测试：有效本包前台、其他包前台、PID不匹配、缺失或畸形输出；禁止删除检查、硬编码通过、强制重试或清除hold。无可证缺陷则交no-candidate。
- 3分钟首交实际源码位置/谓词与复现结果，最多8分钟完成候选；只写本车道独立benchmark目录，不git不push，避免既有共享ref权限失败。CC不上板等外环验收。
## 边界
### 允许修改
- benchmark/2026-10-23-foreground-predicate-replay/**
### 禁止
- watchdog/reentry源码分析、故障/内存/安全机制诊断、设备调用、原部署件修改、审批或沙箱修改、强制跳过就绪检查
## 验收标准
场景: 离线窗口谓词存在可复现误拒
  审核: human
  测试: foreground_predicate_replay_evidence_review
  假设已有可绑定时间的普通WMS和进程文本
  当隔离复现前台谓词并核正反例
  那么候选只修文本解析或身份匹配，保留不就绪拒绝，并提供实际执行回执
场景: 无缺陷或遇边界
  审核: human
  测试: foreground_predicate_replay_evidence_review
  假设既有样本不支持误拒、关键时间缺证或所需分析被拒
  当达到证据或工具边界
  那么交no-candidate和原文，不扩大任务或换模型重试被拒动作
## 排除范围
守护重入状态机修复、上板部署、随机崩溃、冷启动封板和任何权限修改。
