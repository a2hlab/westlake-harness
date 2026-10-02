spec: project
name: "U14 offline single batch"
---

## 意图

Assemble one disabled U14 batch from pinned U13 bytes, without borrowing missing image execution evidence.

## 已定决策

- Keep artifact comparison against U13 91272eaf independent of the parameterized transaction baseline.
- Do not build native outputs, use a VM, deploy, mutate approvals, or authorize a window.

## 边界

### 允许修改
- benchmark/2026-10-03-u14-final-assembly/**
- specs/u14-final-assembly/**
- tools/spec-checks/tests/u14_final_assembly.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md
