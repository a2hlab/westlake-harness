spec: task
name: "Fresh Mac diagnostics and correct external VM environment"
inherits: project
depends: ["t1-binding.spec.md"]
---

## 意图

Run fresh Mac production dry-runs and independent component gates against each U14 BASE, preserving raw refusals and providing guarded external VM replay with shared temporary DEX files.

## 已定决策

- Preserve pending registry and exact-class refusals; do not label required missing G2 as PASS.
- VM replay prepends trusted wrappers, uses shared TMPDIR and inherited or discovered Mac HOME.
- Default replay exits 78 before probes; local environment models are not actual VM verification.

## 边界

### 允许修改
- benchmark/2026-10-03-u15-on-u14-base/**
- benchmark/2026-10-03-u14-on-u13-base/replay-production.sh
- benchmark/2026-10-03-u15-final-assembly/replay-production.sh
- specs/u15-on-u14-base/**
- tools/spec-checks/tests/u15_on_u14_base.rs
- README.md
- .octos/OPS-RUNBOOK.md

## 验收标准

场景: Fresh component failures remain visible without production authority
  测试: u15_u14_replay
  假设 Pending exact classes registry rebinding and unavailable oatdump remain unresolved
  当 Mac dry-runs and independent gates execute
  那么 Every exit and evidence hash is retained with execution and promotion false

场景: VM tools read temporary DEX through the shared workspace
  测试: u15_u14_replay
  假设 A simulated VM has distinct ambient tools and Mac HOME
  当 Both guarded replay entries prepare their environment
  那么 Trusted wrappers precede ambient tools TMPDIR is shared and MAC_HOME is not VM HOME

## 排除范围

- Actual VM access, board operations and changes to gate policies.
