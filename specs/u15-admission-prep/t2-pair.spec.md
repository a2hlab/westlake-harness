spec: task
name: "Prepare paired bake receipt and final assembly readiness"
inherits: project
depends: ["t1-bindings.spec.md"]
---

## 意图

Prepare a two-run paired receipt template and a fail-closed arrival checklist for assembling the single U15 version when both image group and runtime JAR arrive.

## 已定决策

- Exactly nine pinned BCP inputs include framework9e55 and stubs94a9; both runs require 27 distinct outputs and independent live logs/statuses.
- Pending actual argv, output, log, toolchain and return-code fields remain null; old boot.art approvals are not copied.
- Native objects and both installer profiles are fixed, non-BCP runtime JAR candidate is unknown; transaction baselines remain explicit future parameters.
- No ready or execution flag may become true before final composition and fresh gate reports.

## 边界

### 允许修改
- benchmark/2026-10-03-u15-admission-prep/**
- specs/u15-admission-prep/**
- tools/spec-checks/tests/u15_admission_prep.rs

## 验收标准

场景: Arrival checklist retains unknowns without historical PASS
  测试: u15_admission_pair
  假设 The bake and new runtime JAR are still pending
  当 Receipt templates and assembly inputs are checked
  那么 Both runs contain nine pinned inputs and 27 null outputs and no final bundle or production readiness is claimed

场景: Missing member failed tee or historical exception cannot attest the new pair
  测试: u15_admission_pair
  假设 Actual evidence is needed for both complete bake runs
  当 A receipt lacks an output has failed logging or substitutes the old U14 approval
  那么 Validation rejects it while the admission packet remains disabled

## 排除范围

- Poll or execute remote builders, compose a partial bake or approve image nondeterminism.

