spec: project
name: "Spare installer rehearsal"
---

## 意图

准备空闲板安装器统一与重启验收；离线交件不是上板授权。

## 约束

- 本轮只读本机归档，不操作板、VM 或 SSH。
- 写板必须外环另批时间窗并持有对应板锁；61b 不可写，5ea 后续单独派单。
- 不改运行时、JAR、安装包数据、自启配置或门表，不杀进程。
- 截图签认是点亮判据；安装器一致不能掩盖独立的 daemon 启动失败。

## 边界

### 允许修改
- benchmark/2026-10-10-spare-installer-unify/**
- specs/spare-installer-unify/**
- tools/spec-checks/tests/spare_installer.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 排除范围

- 实际替换、重启、BoatAttack 移植、61b 实验、AppSpawnX 修复与晋级。
