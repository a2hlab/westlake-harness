spec: task
name: "U14 arrived native slot inputs"
inherits: project
depends: ["t1-inputs.spec.md"]
---

## 意图

Fill a new input-level slot ledger from arrived native donors without mutating the historical bridge-only bundle.

## 已定决策

- Host341c is selected only after both donor files match their full SHA256.
- Preserve the outer A-prime semantic baseline approval instead of claiming byte reproduction of host2a871.
- Pending Flutter, native ABI and ICU artifacts stay unbound until exact persistent input identities exist.

## 边界

### 允许修改
- benchmark/2026-10-03-u14-jar-image-plan/**
- specs/u14-jar-image-plan/**
- tools/spec-checks/tests/u14_jar_image_plan.rs

## 验收标准

场景: Arrived host is staged but not deployed
  测试: u14_native_slot_inputs
  假设 The accepted host341c double build is available and the historical bridge-only bundle is immutable
  当 The next slot ledger is validated
  那么 Host input identity is complete while applied and execution_enabled remain false

场景: A pending slot cannot become a fake candidate
  测试: u14_native_slot_inputs
  假设 A donor lacks a full SHA or persistent artifact
  当 Its slot is evaluated
  那么 Candidate identity remains null and final batch completeness remains false

## 排除范围

- Native rebuild, final native composition, registry writes, VM or board operations.
