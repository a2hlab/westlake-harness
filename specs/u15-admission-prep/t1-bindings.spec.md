spec: task
name: "Prepare exact native exception and admission previews"
inherits: project
---

## 意图

Prepare 204 validated U14-to-U15 native partial mappings, exact signed strings evidence and conditional new-native admission requirements without applying them.

## 已定决策

- Keep current partial bindings separate from final manifest and inputs, which are null pending JAR and image arrival.
- Use existing auto-identical semantic classification and require 204 matches with zero new findings; final report must be freshly regenerated, not string-replaced.
- Flutter9b824 replaces an existing private target; the current new-native gate only requires a row when that target is absent from the actual baseline.
- Host9e3a and ANL b96a root/route aliases must ship and roll back together; no signature applies to changed bytes.

## 边界

### 允许修改
- benchmark/2026-10-03-u15-admission-prep/**
- specs/u15-admission-prep/**
- tools/spec-checks/tests/u15_admission_prep.rs

## 验收标准

场景: Exact preview preserves all historical findings
  测试: u15_admission_bindings
  假设 Native v2 has 204 identical findings and a signed exact strings table
  当 The preparation packet is validated
  那么 99 N1 and 105 N2 mappings retain actual evidence with final hashes null and no applied registry rows

场景: Split routing or fabricated new-native admission is rejected
  测试: u15_admission_bindings
  假设 Flutter is a replacement and Meet requires two matching native-domain lists
  当 An alias is omitted or an existing target is represented as a new member
  那么 Validation rejects the incorrect claim rather than writing a gate row

## 排除范围

- Sign final manifest, apply exceptions or infer promotion from content comparison.

