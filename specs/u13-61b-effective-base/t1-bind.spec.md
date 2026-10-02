spec: task
name: "Exact board-local service reference rebind"
inherits: project
---

## 意图

Correct the metadata source of the61b full-identity refusal without changing service or candidate output bytes.

## 已定决策

- Keep libinstalls outside native mounts; it is inherited board state, not an optional addition.
- Change exactly two candidate runtime reference values and bind static checks to the61b baseline evidence variant.
- Compare316 baseline and319 candidate identities with signed61b maps before handing over replay.

## 边界

### 允许修改
- benchmark/2026-10-03-u13-61b-effective-base/**
- specs/u13-61b-effective-base/**
- tools/spec-checks/tests/u13_61b_effective_base.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Signed identities keep both service aliases unchanged
  测试: u13_61b_effective_base
  假设 Source51e1 and the61b signed baseline and candidate maps agree
  当 Metadata-only variants are prepared
  那么 Full maps agree and neither service alias occurs in additions or changes

场景: Wrong reference or a service write is rejected
  测试: u13_61b_effective_base
  假设 Exactly two runtime reference lines require correction
  当 A third identity changes or a service action is introduced
  那么 Validation rejects instead of relaxing full-identity assertions

场景: Fresh gates do not borrow production success
  测试: u13_61b_effective_base
  假设 Original and variant static and active native checks exist
  当 Offline results are handed over
  那么 Checks pass with unchanged native bindings and fresh Mac VM production remains pending

## 排除范围

- Deployment, board locks, window authorization, active registry mutation and service unification.
