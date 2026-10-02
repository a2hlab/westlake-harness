spec: task
name: "U14 partial composition and scope"
inherits: project
---

## 意图

Compose the available native and JAR components while keeping missing boot images visibly pending.

## 已定决策

- Verify every selected artifact hash; change only the declared private aliases and existing ICU pair.
- Remove the old bundle descriptor and old paired receipt from the partial output.
- Require an explicit transaction baseline argument for finalization, not a hidden U12 default.

## 边界

### 允许修改
- benchmark/2026-10-03-u14-final-assembly/**
- specs/u14-final-assembly/**
- tools/spec-checks/tests/u14_final_assembly.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Pinned partial composition is disabled
  测试: u14_final_composition
  假设 Only native and JAR artifacts are available
  当 Partial composition is validated
  那么 Eight declared existing payload members change, one ICU shim is added, and no executable bundle descriptor exists

场景: Private alias drift is rejected
  测试: u14_final_composition
  假设 Flutter and Gecko changes belong to different private domains
  当 Root or other private aliases change, or a selected hash differs
  那么 Validation rejects the output

场景: Missing transaction baseline is rejected
  测试: u14_final_composition
  假设 Content comparison and transaction baselines are independent
  当 Finalization lacks an explicit baseline identity
  那么 Validation rejects rather than assuming U13 promotion

## 排除范围

- Native compilation, VM access and device operations.
