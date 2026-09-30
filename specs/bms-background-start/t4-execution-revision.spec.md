spec: task
name: "Record hwui rollback and stratify actual execution profiles"
inherits: project
depends: [t3-r17op]
---

## 意图

Record the reported 05:20 hwui rollback separately from the accepted v3 forecast. Classify future runs by actual fingerprint without treating the reverted native library or an unforecast JAR as the frozen profile.

## 已定决策

- Preserve v3 predictions, profiles, scorer and receipt byte-for-byte.
- The notice names base hwui be59260f and possible r17q, but does not supply r17q bytes; its hash stays unknown until measured.
- Compare run-local facts and runtime-fingerprint hashes against each frozen profile. Group by actual runtime fingerprint and board; mismatches receive no same-profile score or alternative-column rescue.

## 边界

### 允许修改
- benchmark/2026-09-30-r17op-execution-revision/**
- specs/bms-background-start/t4-execution-revision.spec.md
- tools/spec-checks/src/lib.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

### 禁止
- No board operations or edits under benchmark/2026-09-30-r17op-prospective/.

## 验收标准

场景: 实际运行件差异与未知JAR
  测试: r17op_execution_profiles
  假设 Runtime fingerprints contain pinned r17o with rolled-back hwui or an unknown JAR
  当 The companion auditor emits JSON strata
  那么 It identifies the actual hashes and rejects both from frozen same-profile eligibility
  并且 An unchanged exact profile is distinguished without claiming device validation from the notice

场景: 缺失证据拒绝与冻结不变
  测试: r17op_execution_integrity
  假设 Facts fingerprints are missing or inconsistent
  当 The integrity gate compares them and the v3 receipt
  那么 Invalid runs remain unverified and receive no profile identity
  并且 All v3 frozen hashes and original scoring code remain unchanged

## 排除范围

- New r17q forecasts, device verification, outcome adjudication and retroactive profile amendments.
