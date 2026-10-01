spec: task
name: "Score all signed corpus-v2 keys and publish conservative rule feedback"
inherits: project
---

## 意图

Publish a reproducible two-by-six confusion table, input and screenshot identity receipts, per-key rule attribution, and a separately versioned conservative scanner.

## 已定决策

- Pin PREDICTIONS.csv ab51ab2df4fa6d8e66989d8713da71b79ef5e9c9e6b473f6c54a4bd1d1bc21b1 and master signoff 5641749091f0a12f084494f8e173ce75c04e05ee.
- Require exactly one hundred unique identical key sets; reject unknown verdict classes and identity mismatches.
- Bind APK, package, version, sidecars, scheduled screenshot bytes and the three run fingerprint receipts; state the limits of device-byte attestation.
- Attribute scanner coverage and abstention mechanisms separately from unobserved runtime root causes.
- Preserve exact WebView content API evidence, distinguish utility APIs, and abstain on bounded startup Activity transitions and Koin initialization.
- Ship deterministic replay, positive and negative rule controls, landing paths and exact shared-document additions.

## 边界

### 允许修改
- benchmark/2026-10-01-cv2-scoring/**
- benchmark/2026-10-01-corpus-v2/apk-scan-v2/**
- specs/cv2-scoring/**
- tools/spec-checks/tests/cv2_scoring.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Signed scoring rejects changed or ambiguous inputs
  测试: cv2_scoring_identity
  假设 Duplicate missing keys an unknown verdict or an altered frozen CSV
  当 The scoring join is requested
  那么 It refuses to manufacture a complete score

场景: Abstentions and fallback UI remain separate
  测试: cv2_scoring_confusion
  假设 The one hundred outer signed verdicts and seventy three positive predictions
  当 The confusion matrix and precision are computed
  那么 All six columns sum correctly and unknown is not counted as true negative or false negative

场景: New rules have exact API evidence and negative controls
  测试: cv2_scoring_feedback
  假设 Content WebView utility WebView bounded Activity transitions and Koin calls
  当 Version two rules evaluate offline APK evidence
  那么 Only supported candidate contracts alter confidence and no candidate claims a proved fatal point

场景: Published artifacts replay without changing the freeze
  测试: cv2_scoring_replay
  假设 Pinned signoff run evidence and static APK evidence
  当 Scoring and retrospective scanner outputs are regenerated
  那么 All published rows reproduce and the version one freeze remains unchanged

## 排除范围

- Runtime repairs, screenshot reclassification, device operations and replacing oc-t4's separately assigned fatal-cluster investigation.
