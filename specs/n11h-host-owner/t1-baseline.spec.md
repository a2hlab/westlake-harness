spec: task
name: "Reproduce accepted r3 in a new offline directory"
inherits: project
---

## 意图

Establish the exact accepted host as the build baseline instead of reusing a U9-shaped proxy.

## 已定决策

- Verify source507bf160, clang6a5ec844 and all reused object hashes before compiling.
- Preserve the source basename and apply an exact baseline file-prefix map to reproduce r3 without rewriting its inputs.
- Persist sources, commands, compiler hashes and unfiltered tee build logs in the new handoff.

## 边界

### 允许修改
- benchmark/2026-10-02-n11h-host-owner/**
- specs/n11h-host-owner/**
- tools/spec-checks/tests/n11h_host_owner.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Exact baseline and deterministic candidate builds
  测试: n11h_baseline
  假设 Verified r3 source and the recorded frozen host object recipe
  当 The baseline and candidate are built in new fixed paths twice
  那么 Baseline equals65cc3535 and both candidate outputs are byte identical with persisted input receipts

## 排除范围

- No generation promotion or source/header writes into accepted r3 inputs.
