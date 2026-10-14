spec: project
name: "Recoverable worktree retirement"
---
## 约束
- 用户授权以最安全方式清理；保留主树、所有分支、未合并代码、未归档文件、演示运行时与远程构建依赖。
- 仅普通 git worktree remove；禁止 force、git clean、分支删除、对象 GC、设备操作。
- 移除前须完整私有归档、逐成员哈希验证、远端副本哈希一致、无占用进程；任一未证则保留。
