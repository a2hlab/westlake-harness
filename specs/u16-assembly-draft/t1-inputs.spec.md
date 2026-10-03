spec: task
name: "U16 exact content and pending slots"
inherits: project
---

## 意图

Prepare a disabled U16 composition ledger from U15 common29c8/61b8a26, replacing exactly stubs8593 and non-BCP runtime JARf6f5, with native slots pending.

## 已定决策

- Resolve effective nine BCP inputs from complete content bundles; only stubs changes, framework9e55 stays.
- Keep M1 runtime split and Flutter Impeller proc repair pending, t2 excluded and t5 A0-blocked.
- Require a future per-board armed U15 transaction BASE parameter; never infer it from content candidates.
- Eight donor auxiliary classes remain pending outer allow_add approval; do not invent a final bundle or image hash.

## 边界

### 允许修改
- benchmark/2026-10-03-u16-assembly-draft/**
- specs/u16-assembly-draft/**
- tools/spec-checks/tests/u16_assembly_draft.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Exact U15 and U16 identities are pinned
  测试: u16_draft_inputs
  假设 Both U15 content variants and two U16 donor JARs have exact SHA256 identities
  当 The offline composition ledger is checked
  那么 Nine ordered BCP inputs contain exactly one stubs swap and the runtime JAR is explicitly outside BCP with all transaction bases null

场景: Arrival readiness and source drift reject
  测试: u16_draft_inputs
  假设 Native artifacts approval and image output identities are still pending
  当 A slot is marked applied or a pinned input source snapshot changes
  那么 The preparation check rejects rather than claiming a complete deployable bundle

## 排除范围

- Build native artifacts, compose an executable generation, apply allow_add or run production replay.

