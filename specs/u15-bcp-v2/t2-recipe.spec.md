spec: task
name: "Prepare the executable but disabled U15 dual BCP recipe"
inherits: project
depends: ["t1-inputs.spec.md"]
---

## 意图

Provide an outer-authorized hw248 recipe for two complete image builds with identical work paths, frozen tools, live logging and fresh paired evidence.

## 已定决策

- Default entry exits 78 before probing any machine; separate outer approval is required for execution.
- hw248 means ecs-9f6c Linux x86_64 with explicitly supplied FZ-005 home identity, frozen ae865 compiler and 14b1 driver.
- Two runs use a new shared work root and distinct immutable output and log names; actual argv, tool hashes, hostlibs and all tee statuses are retained.
- The new 9e55 plus 94a9 input pair cannot inherit the U14 or T7d boot.art exception.

## 边界

### 允许修改
- benchmark/2026-10-03-u15-bcp-v2/**
- specs/u15-bcp-v2/**
- tools/spec-checks/tests/u15_bcp_v2.rs

## 验收标准

场景: Recipe stays disabled and paired receipt remains unexecuted
  测试: u15_bcp_v2_recipe
  假设 No separate execution authorization or actual build evidence exists
  当 The default entry and receipt templates are checked
  那么 Entry exits 78 before probes and both runs retain null actual argv logs statuses and outputs

场景: Partial output failed logging or reused approval is rejected
  测试: u15_bcp_v2_recipe
  假设 Two complete 27-member output groups and fresh input-bound evidence are required
  当 Output count logging status or exception input identity is incorrect
  那么 Validation rejects the receipt rather than accepting a partial build or historical approval

## 排除范围

- Execute dex2oat, contact hw248 or a2hlab, or run production or board replay.

