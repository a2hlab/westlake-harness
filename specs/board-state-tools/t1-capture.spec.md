spec: task
name: "Transport-independent capture and integrity-aware diff"
inherits: project
---

## 意图

一条命令采集规定状态，离线逐项对照并把不完整证据显式列出。

## 已定决策

- 采集标签全树与全部部署 target，不截断挂载列表。
- 记录每条命令 stdout/stderr/exit 与哈希，boot 变化使快照不完整。
- 多个同 exe 进程不折叠；缺失、被修改、symlink 的原始证据不可比较。

## 验收标准

场景: Complete fixture collection remains read only
  测试: board_state_readonly
  假设 A transport fixture provides 56 targets and 85 mounted targets
  当 The collector captures labels parameters init config hashes layers and process views
  那么 All paths and raw bytes are retained with no write commands or environment values

场景: Failed or rebooted collection cannot be complete
  测试: board_state_readonly
  假设 A read fails the boot changes or the deployment plan is absent
  当 The collector stores the snapshot
  那么 It keeps raw stdout stderr exit and names the incomplete evidence

场景: Missing evidence never means no difference
  测试: board_state_readonly
  假设 An otherwise identical snapshot has missing modified or symlink raw files
  当 Offline comparison checks the evidence hashes
  那么 It is incomparable and any seccomp observations remain noncausal hints
