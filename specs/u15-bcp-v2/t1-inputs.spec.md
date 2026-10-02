spec: task
name: "Pin the U15 Bitmap and NSD inputs"
inherits: project
---

## 意图

Replace the historical single-BCP forecast with a separately versioned nine-input snapshot selecting framework9e55 and stubs94a9, and record the newly arrived Flutter ATrace donor without claiming composition.

## 已定决策

- Exactly framework.jar and adapter-mainline-stubs.jar change; seven BCP JARs and the separate runtime JAR0349 retain their accepted hashes.
- Snapshot and hash both content profiles, the persistent NSD release and donor source receipts; no new build or promotion is inferred.
- Native partial94c3/9e3a/b96a is a referenced draft, not a complete bundle; the newly authorized Flutter9b824 donor is arrived but uncomposed in this BCP packet.

## 边界

### 允许修改
- benchmark/2026-10-03-u15-bcp-v2/**
- specs/u15-bcp-v2/**
- tools/spec-checks/tests/u15_bcp_v2.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Nine inputs have exactly two approved swaps
  测试: u15_bcp_v2_inputs
  假设 Accepted U14 bases and the two persistent donors have pinned full hashes
  当 The updated offline plan is validated
  那么 Nine ordered inputs have exactly two swaps and 27 distinct outputs remain unknown

场景: Wrong unchanged input or false donor completion is rejected
  测试: u15_bcp_v2_inputs
  假设 Seven BCP inputs are unchanged and Flutter9b824 has arrived without composition
  当 An unchanged hash or donor completion status is altered
  那么 Validation rejects it without writing gate registries or claiming promotion

## 排除范围

- Compose a deployable bundle or apply any gate exception.
