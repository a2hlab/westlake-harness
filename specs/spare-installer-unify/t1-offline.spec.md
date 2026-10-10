spec: task
name: "Prepare pinned installer transaction"
inherits: project
---

## 意图

追溯51e1源码、补丁、构建日志与产物，准备只替换5cd两处物理安装器的事务和严格重启验收。

## 已定决策

- 优先使用b79持久归档，不重建或从61b取件；默认dry-run不创建设备连接。
- 两处原厂备份经本机SHA核对后才能remount写入；标签、权限、boot与锁均须复核。
- 回滚只用本事务的2c9原件；任何失败保锁，不自动重启或恢复Mac票据。

## 边界

### 允许修改
- benchmark/2026-10-10-spare-installer-unify/**
- specs/spare-installer-unify/**
- tools/spec-checks/tests/spare_installer.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Archived source identity is pinned
  测试: spare_installer_offline
  假设 The original and candidate archives and build receipts exist locally
  当 The provenance verifier runs without device access
  那么 It verifies the exact artifact source patch toolchain and build log hashes and refuses changed inputs

场景: Unauthorized or drifting transactions refuse before writes
  测试: spare_installer_offline
  假设 A prepared transaction has no approval or a wrong serial boot lock hash or mount
  当 The installer is invoked with a mocked transport
  那么 It refuses before mutation and dry run never opens a device connection

场景: Atomic replacement and explicit rollback preserve physical state
  测试: spare_installer_offline
  假设 Two stock aliases have verified backups and original metadata
  当 The transaction replaces or rolls back both aliases in a simulated filesystem
  那么 It restores mode and context hashes both aliases and remounts read only on success or failure

场景: Reboot UI proof remains independent
  测试: spare_installer_offline
  假设 Runtime files match but the daemon is absent or one control screenshot is white
  当 The acceptance checker reads offline observations and outer signoff
  那么 It refuses and only a changed boot exact fingerprint init parent and two signed lit t20 screenshots can pass

## 排除范围

- 本契约测试不构成真实上板验收或开窗授权；物理板的恢复与截图须另行审核。
