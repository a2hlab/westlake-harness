spec: task
name: "Final U12 bundle and strict offline admission"
inherits: project
---

## 意图

Bind ICU, mediandk policy, exact private-zlib donor and U12 r2 paired Java/images into one immutable candidate; report real production gate outcomes without self approval.

## 已定决策

- N11h-r2 and compat relocation deferred to U13.
- Keep zlib private; no root alias and no extra policy name.
- Mac and VM production PATH run actual final artifacts.
- Three plans remain disabled with 55/55/56 keys and unconditional U10.1T8 restoration.

## 边界

### 允许修改
- benchmark/2026-10-02-u12-final-assembly/**
- specs/u12-final-assembly/**
- tools/spec-checks/tests/u12_final_assembly.rs

### 禁止做
- Write gate registries, approve rollout, transport device commands or deploy.

## 验收标准

场景: Exact reviewed final members and paired boot inputs
  测试: u12_final_members
  假设 Signed U10.1T8 and reviewed donors
  当 Final candidate is validated offline
  那么 Exact native and Java hashes are pinned with private additions and matching nine input and 27 output receipt

场景: Strict gate evidence and new admission proposals
  测试: u12_final_gates
  假设 Real Mac and VM production tools and final candidate
  当 Final native static image and frozen gates run
  那么 Reports bind final manifest and unchanged registries with exact new member proposals and honest refusal until outer admission

场景: Disabled observation plans restore signed U10.1T8
  测试: u12_final_plans
  假设 Outer signed 166 keys and 116 lit baseline
  当 Three observation plans and key partition are checked
  那么 Plans stay disabled with 45/35 limits 55/55/56 disjoint keys pair-sheet reference and unconditional 318 restoration

## 排除范围

- Registry approval, runtime source fixes, board execution or U13 mechanisms.
