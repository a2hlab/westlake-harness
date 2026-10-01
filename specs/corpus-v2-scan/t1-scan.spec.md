spec: task
name: "Scan admitted APK batches and freeze identity-bound predictions"
inherits: project
---

## 意图

Consume each available verified input batch, scan all DEX and native members using the existing scanner, classify launch manifests and framework profiles, and publish first-wall candidates separately from t20 hypotheses.

## 已定决策

- Pin the selected CSV and JSON from corpus-v2; do not replace their metadata predictions in place.
- Use exact APK SHA and indexed signer fingerprints, with explicit pending states for absent or rejected inputs.
- Reuse B10 method_scan, inspect_method and elf_info; retain DEX method/offset/line and native member hashes.
- Bind actual U7 JAR and native bytes before evaluating JNI coverage. Historical v3 coverage cannot silently substitute for U7.
- A reference is not execution. Startup candidates use bounded launcher/Application/provider lifecycle paths; wider calls remain secondary candidates.
- Publish a versioned prediction CSV, compact replay evidence and a SHA freeze only after complete identity and scan validation.

## 边界

### 允许修改
- benchmark/2026-10-01-corpus-v2/apk-scan-v1/**
- specs/corpus-v2-scan/**
- tools/spec-checks/tests/corpus_v2_scan.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: APK identities and signer mismatches are rejected
  测试: corpus_v2_scan_identity
  假设 A pinned candidate with altered bytes or signer fingerprints
  当 Input admission is checked
  那么 The candidate is rejected rather than counted as a complete scan

场景: Existing scan rules retain positive and negative distinctions
  测试: corpus_v2_scan_rules
  假设 DEX service calls native references and manifest launchers
  当 Existing scanner functions and profile classification run
  那么 Evidence records exact call coordinates and unsupported or unresolved contracts stay conditional

场景: Incomplete cohorts cannot freeze
  测试: corpus_v2_scan_freeze
  假设 Missing duplicated rejected or incompletely scanned keys
  当 A prediction freeze is requested
  那么 Freeze is refused until all one hundred unique candidate identities and runtime pins pass

场景: Evidence-bound predictions replay
  测试: corpus_v2_scan_replay
  假设 Compact APK facts and a hash-bound runtime profile
  当 Prediction JSON and CSV are regenerated
  那么 Artifacts match exactly and original corpus selection files remain unchanged

## 排除范围

- Implementing runtime repairs, deciding screenshot truth or treating absence of an alert as a proved first-frame success.
