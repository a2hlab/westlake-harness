spec: task
name: "Bind common lit-app noise and subtract before triage"
inherits: project
depends: [t2-classify]
---

## 意图

Create knowledge/gates/benign-log-signatures.json from U5 own-UI controls. Normalize volatile timestamp PID TID and addresses, record distinct-app support and example lines, and subtract only exact supported signatures before candidate classification and fatal inspection.

## 已定决策

- Each signature requires at least three distinct outer-reviewed lit application packages, not duplicate keys or global compositor logs.
- Retain matched line references and raw excerpts; a terminal fatal marker cannot be suppressed even with a malformed or overbroad registry entry.
- Bind the registry to the U5 candidate and source hashes; it is contextual noise evidence, not a blanket exception for future generations.

## 边界

### 允许修改
- knowledge/gates/benign-log-signatures.json
- benchmark/2026-10-01-u5-investigate/**
- specs/u5-investigate/**
- tools/spec-checks/tests/u5_investigate.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Common lit signatures normalize volatile identifiers
  测试: investigate_benign_support
  假设 PID-scoped errors and warnings from the 24 outer-reviewed lit keys
  当 The registry support and examples are validated
  那么 Each entry has at least three distinct packages counts and numbered source examples without using foreign compositor events

场景: Unsupported or fatal signatures are not silently suppressed
  测试: investigate_benign_safety
  假设 Common caught probes plus a fatal marker and a different-generation observation
  当 The triage noise filter runs
  那么 Only exact contextual noise is subtracted while fatal and unmatched-generation events remain visible and matched raw evidence remains available

## 排除范围

- Editing frozen predictors or treating harmlessness on three lit apps as universal semantic correctness.
