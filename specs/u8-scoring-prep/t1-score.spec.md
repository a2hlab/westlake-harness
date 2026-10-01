spec: task
name: "Prepare the single-entry three-freeze scorer and 166-key change table"
inherits: project
---

## 意图

Read cv2 v1, ActionBar and WebView frozen CSVs once, join an outer-signoff-v1 document and produce scoring and U7-to-U8 change artifacts.

## 已定决策

- Reject CSV SHA drift, duplicate or wrong signoff keys, wrong runtime/image state and inconsistent verdict totals.
- Read the old 66 U7 signed reviews and cv2 signed baseline; compare app-owned UI and functional fallback changes separately.
- Keep unobserved old keys unknown in the cv2 structure replay instead of padding fake U8 with baseline outcomes.
- Provide optional run roots for PID-bound first_fatal analysis, reject duplicate attempts and require matching facts before using log roots.
- Publish separate cv2 confusion, ActionBar tier outcome/coverage and WebView exact-class confusion; do not invent ActionBar t20 labels.

## 边界

### 允许修改
- benchmark/2026-10-01-u8-scoring-prep/**
- specs/u8-scoring-prep/**
- tools/spec-checks/tests/u8_scoring_prep.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Formal input failures are rejected
  测试: u8_scoring_prep_identity
  假设 CSV drift duplicate keys wrong U8 identity or only one hundred signed keys
  当 Formal scoring admits inputs
  那么 It rejects each mismatch before publishing a formal score

场景: Unknown and fallback classes stay distinct
  测试: u8_scoring_prep_visual
  假设 An abstention a lit WebView fallback and a functional UI transition
  当 Visual scoring and changes run
  那么 Abstentions do not create TN or FN and fallback changes preserve their own secondary axis

场景: Signed UI does not invent wall or checkpoint truth
  测试: u8_scoring_prep_risks
  假设 A lit later-only key missing diagnostic evidence or conflicting raw run attempts
  当 ActionBar and WebView scoring runs
  那么 Wall and checkpoint truth remains unknown and conflicting attempts are refused

场景: The cv2 fixture replay remains explicit and reproducible
  测试: u8_scoring_prep_replay
  假设 The signed cv2 one hundred key document used as a fake U8
  当 The replay flag is supplied
  那么 Three prediction tables and all 166 change rows reproduce with 66 unobserved outcomes and no formal U8 claim

## 排除范围

- Actual U8 screenshot review or formal scoring before outer supplies its signed full document.
- Inventing page-exercise evidence, root causes from screenshot classes or APK identity from key names.
