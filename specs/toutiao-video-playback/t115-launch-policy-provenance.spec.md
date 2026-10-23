spec: task
name: "T115 ordinary launch-policy provenance comparison"
inherits: project
satisfies: [REQ-TTVIDEO]
depends: [t109-spare-board-power-entry, t112-after-reboot-icon-recovery, t114-host-lifecycle-after-retry-limit]
---
## 意图
T114证明T112点击已到宿主，但RETRY_LIMIT未启动新child。T106只核核心库/HAP，不包含启动管理配置；对照现有两板启动管理交付记录，查是否已有可复用的已验证版本或配置差异。
## 已定决策
- Codex离线只读既有发布/恢复manifest、签认、README、配置schema/参数记录和sha清单。优先T34/T61/T85/T87/T109/T112，以及主树现有恢复包元数据；绑定board/boot/实际部署SHA，区分计划版本和部署版本。
- 不读取watchdog.sh及其改名/复制源码，不访问T71/T74/T91被停止的分析/部署对象或重试流程；本卡是独立元数据核对，不源码补丁/退出归因。没有当前哈希时标unknown，可以给后续最小只读hash需求而不自行上板。
- 比较普通启动重试次数、人工重入/自动重试模式、交付代次，只有原记录明确包含才列。不得由事件状态名倒推配置值；若已有可复用恢复包，给原始批准与构建/哈希证据链和适用对象，不直接建议跨板盲拷贝。
- 五分钟首交，只产一张有证据路径的比较表与缺项，不重复核心18库/HAP扫描。无明确差异就报告缺项，不制造修复候选。
## 边界
### 允许修改
- benchmark/2026-10-23-launch-policy-provenance/**
### 禁止
- 设备调用、运行时部署、停止源码/改名副本、权限改动、随机崩溃归因
## 验收标准
场景: 两板控制配置有已绑定记录
  审核: human
  测试: launch_policy_provenance_review
  假设实际交付记录包含board/版本/配置和SHA
  当对照本次事件及已验证恢复包
  那么给明确相同或不同的证据，不用核心库相同替代控制配置相同
场景: 只有计划或缺当前身份
  审核: human
  测试: launch_policy_provenance_review
  假设仅有历史计划、文件名或事件名
  当形成结论
  那么标unknown和最小缺证，不猜参数值或把恢复件称已部署
## 排除范围
源码修改、构建、部署、随机退出、T91时间戳候选。
