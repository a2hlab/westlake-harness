spec: task
name: "Retire only recoverable merged worktrees"
inherits: project
---
## 意图
清理失效注册和已合入主分支的闲置工作树，保存可恢复副本与清理回执。尚有独有内容或身份不明的工作树保持原位，避免将本轮交付完成误认为历史目录均可丢弃。

## 已定决策
- 首批目录白名单仅 westlake-harness-label 与 agent-a2ef2d12ea17a76fc。
- Git管理数据、分支引用与未提交二进制patch先私有备份；待删除目录包含ignored文件完整归档。
- 归档逐文件校验并实际解包复核；远端hw248保留独立SHA一致副本。
- 其他本地目录与远程构建/证据目录只读保留；删除仅在执行前再次核同HEAD、状态、内容哈希及进程无占用。

## 边界
### 允许修改
- specs/worktree-retirement/**
- benchmark/2026-10-14-worktree-retirement/**
- tools/spec-checks/tests/worktree_retirement.rs
- README.md
### 禁止
- 不移除master工作树、未合并分支或任何分支引用。
- 不公开原始patch、Git配置、私有归档内容。
- 不修改演示设备、远程构建环境或其他agent窗格。

## 完成条件
场景: 归档后移除已合并工作树
  审核: human
  测试: worktree_retirement
  Given two allowlisted merged worktrees with verified full archives
  When retiring them with normal git worktree remove
  Then each removal has matching local remote archive hashes and a successful restore audit

场景: 独有内容或占用时保留
  测试: worktree_retirement
  Given worktrees with changes untracked files unmerged heads or active processes
  When evaluating cleanup eligibility
  Then each is retained and no force removal is executed

场景: 陈旧注册只删除元数据
  审核: human
  测试: worktree_retirement
  Given seven stale registrations and archived Git administrative metadata
  When pruning expired worktree registrations
  Then existing residual directories remain untouched and branch references are unchanged
