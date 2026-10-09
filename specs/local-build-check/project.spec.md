spec: project
name: "本机 native 退路构建检查"
---

## 意图

按 benchmark/2026-10-09-local-build-check/TASK.md 核验退路构建能力。以 U13 部署指纹和实际源码为依据，区分编译能力与修复位置。

## 约束

- 板操作限定为只读哈希；不取锁、不安装、不重启、不部署。
- 不改其他车道源码或冻结项；源码只读复制到独立临时目录。
- 原始 stdout/stderr 在执行时 tee 到持久目录，报告记路径、SHA 和退出码。
- 仅本地提交；黑板用 olp-board-append.sh 追加 PROGRESS(91)，不推送。

## 已定决策

- 先本地查源，再查 OrbStack；hw248 不作为依赖。
- ABI 使用 scripts/lab/abi_diff.py；差异逐 ELF 节与指令比较。

## 边界

### 允许修改
- benchmark/2026-10-09-local-build-check/**
- specs/local-build-check/**
- tools/spec-checks/tests/local_build_check.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md
- .octos/OPS-RUNBOOK.md
