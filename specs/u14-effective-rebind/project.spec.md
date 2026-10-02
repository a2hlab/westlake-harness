spec: project
name: "U14 conditional U13 transaction binding"
---

## 意图

Prepare disabled per-board U14 metadata against the planned U13 promotion without altering the landed first U14 packet.

## 已定决策

- No device, VM, compilation, image bake or active approval registry changes.
- U13 promotion remains unconfirmed; all generated bundles remain disabled.

## 边界

### 允许修改
- benchmark/2026-10-03-u14-effective-rebind/**
- specs/u14-effective-rebind/**
- tools/spec-checks/tests/u14_effective_rebind.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md
