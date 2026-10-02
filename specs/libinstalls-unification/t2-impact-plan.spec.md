spec: task
name: "Count existing installs and propose guarded alignment"
inherits: project
depends:
  - t1-identity.spec.md
---

## 意图

Count recorded installation results for166 apps and isolate the other165 from Toutiao, then propose a non-executable, reversible service alignment with independent admission gates.

## 已定决策

- Select U9 attempts by the signed key-to-shard mapping; do not silently substitute latest attempts or count all logs as independent trials.
- Retain failed previous Seal and Toutiao attempts separately from selected U9 successes; unrelated install-fatal log lines cannot outweigh terminal bm installation receipts.
- Proposed order is5ea then5cd,61b check-only; foundation restart needs explicit user-present review and current-generation recovery, not the obsolete v3a recipe.

## 边界

### 允许修改
- benchmark/2026-10-02-libinstalls-unification/**
- specs/libinstalls-unification/**
- tools/spec-checks/tests/libinstalls_unification.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Counts distinguish observed install outcomes from missing evidence
  测试: libinstalls_install_stats
  假设 Recorded bm install receipts and the U9 signed166 key selection
  当 Per-board installation and payload observations are counted
  那么 Each key is counted once, Toutiao is separated from the other165, unknown stays unknown, and comparative attempts carry file line and SHA witnesses

场景: The proposed plan cannot authorize a restart
  测试: libinstalls_alignment_plan
  假设 The two old boards and the already updated61b and the existing manifest-driven transaction interface
  当 The alignment plan is validated offline
  那么 Execution is disabled, only the two libinstalls aliases on5ea and5cd change, rollback preserves their exact old hashes, and static plus identity plus installation plus recovery gates remain required

## 排除范围

- No causal regression rate from disjoint boards and no claim that install success proves app UI.
