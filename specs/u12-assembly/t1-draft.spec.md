spec: task
name: "U12 native draft and disabled three-board observation plans"
inherits: project
---

## 意图

Compose reviewed ICU and mediandk/policy artifacts on U10.1T8, report exact native findings on Mac and VM, and prepare disabled complete-key observation plans without waiting for other lanes.

## 已定决策

- Native inputs are pinned ICU 1e206531, mediandk 8fc0752d and policy 2a6ec73f; declared policy aliases update together.
- Leave N11h-r2, runtime/stubs/boot and combined predictions pending; no approval-table writes.
- Plans cover 166 keys with 45/35-minute budgets and unconditional U10.1T8 restoration.

## 边界

### 允许修改
- benchmark/2026-10-02-u12-assembly/**
- specs/u12-assembly/**
- tools/spec-checks/tests/u12_assembly.rs

### 禁止做
- Device access, board locks, native builds, exception approval or enabling execution.

## 验收标准

场景: Pinned native members and pending components remain explicit
  测试: u12_assembly_native
  假设 Signed U10.1T8 and the reviewed native inputs
  当 Draft identities and reports are checked offline
  那么 Four effective native paths differ and pending layers cannot enable deployment

场景: Three plans preserve coverage and restoration discipline
  测试: u12_assembly_plans
  假设 Signed 166-key baseline and per-board 318 identities
  当 Disabled observation plans are checked
  那么 Key union is exactly166 without overlap and finish restores U10.1T8 with 45/35-minute limits

## 排除范围

- Native rebuilds, resolving other lanes' pending artifacts, board validation, promotion or exception registration.
