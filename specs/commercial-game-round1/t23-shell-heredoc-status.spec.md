spec: task
name: "G23 preserve heredoc boundaries in the original board transport"
inherits: project
depends: [t22-u7-start-binding]
satisfies: [REQ-COMMERCIAL-GAME]
---
## 意图
修复 G21 原始执行暴露的命令拼接错误：Board.raw_shell 将返回码标记接到 heredoc 结束行，原标签配方无法解析且原回滚启动也受影响。保留真实失败回执，用本地真实 shell 验证最小修订后恢复原事务。
## 已定决策
- 只修现有传输器的命令与返回码标记之间的行分隔；不写新部署器，不跳过标签检查，不修改门禁或重试未知写操作。
- 使用实际 /bin/sh 执行捕获到的命令形态，覆盖末行有换行与无换行、普通命令、远端非零返回码、标记丢失拒绝及只读重试边界。
- 保留 G21 原 journal、挂载恢复及失败日志。原 apply 终止后才接入修复，使用同一 journal 的原 rollback 恢复；当前窗口不重新部署候选、不首启原神，时限沿用原锁时间。
- 内环只在自身 worktree 改码和离线验收；外环独立检查后落库，设备恢复由外环持原锁执行。
## 边界
### 允许修改
- benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py
- benchmark/2026-09-28-bms-route-deploy/batch/test_bms_batch.py
- benchmark/2026-10-21-commercial-game/shell-heredoc-status/**
- benchmark/2026-10-21-commercial-game/gles-bounded-window/**
- tools/spec-checks/tests/bms_shell_heredoc_status.rs
### 禁止
- 不改变标签配方、门禁、权限、游戏和运行时源码；不重试 G14/T38；不对61b或5cd执行操作。
## 验收标准
场景: 原标签命令完整通过实际 shell 传输
  测试: bms_batch_offline
  假设原命令的 heredoc 关闭行有或没有末尾换行
  当真实 Board.raw_shell 在本地 shell 回放
  那么关闭行独占一行且正文完整到达，返回码标记在命令结束后被正确解析
场景: 失败保持失败且写操作不重放
  测试: bms_batch_offline
  假设命令返回非零或返回码标记丢失
  当原传输器解析结果
  那么保留真实非零返回码或明确拒绝，不将失败转为成功且不自动重复未知写操作
场景: 原回滚恢复有设备证据
  测试: u7_executor
  审核: human
  假设原 apply 已终止且原锁和boot身份仍一致
  当使用原 journal 运行原 rollback
  那么原标签配方及全部基线校验通过，保存真实恢复日志截图并在原窗口时限内释放锁
## 排除范围
候选再次部署、原神可玩性、头条白屏部署、通用传输器重构。
