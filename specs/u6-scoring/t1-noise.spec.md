spec: task
name: "Repair omitted common native probe signature"
inherits: project
---

## 意图

Explain and repair the missing B8-NATIVE HTML compatibility probe signature using original lit-app PID evidence, without rewriting historical replay receipts.

## 已定决策

- Report manual selection omission rather than attributing it to PID filtering or the support threshold.
- Extend the live registry to 18 entries and retain a byte-pinned 17-entry replay snapshot.
- Project baseline noise into U6 triage only for the exact frozen runtime and boot inventories, retaining all raw evidence.

## 边界

### 允许修改
- knowledge/gates/benign-log-signatures.json
- benchmark/2026-10-01-u5-investigate/test_classify.py
- benchmark/2026-10-01-u6-scoring/**
- specs/u6-scoring/**
- tools/spec-checks/tests/u6_scoring.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Omitted HTML probe has app-scoped support
  测试: u6_scoring_noise_support
  假设 Original U5 lit-app signature candidates and the historical registry
  当 The live registry and retained replay are checked
  那么 HTML probe has 24 distinct packages and 28 occurrences and old replay still passes unchanged

场景: Noise cannot hide terminal failure or cross unknown candidates
  测试: u6_scoring_noise_safety
  假设 Supported noise and terminal fatal events in target and foreign PIDs
  当 U5 rehearsal or exact frozen U6 triage is prepared
  那么 Only contextual target noise is marked and mismatched runtime disables projection

## 排除范围

- Fixing native libraries or declaring universal harmlessness.
