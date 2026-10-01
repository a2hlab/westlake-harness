spec: task
name: "Publish version-pinned F-Droid selection and static priors"
inherits: project
---

## 意图

Give oc-t4 a deterministic list of one hundred distinct packages absent from the existing corpus, with APK versions URLs hashes and per-app static metadata predictions suitable for input preparation.

## 已定决策

- Bind index SHA e0fde6a3d0882f4ff88b48b594e4cb818e4ad5ed46005007c47d203a2819d330 and validate its entry.jar size/hash reference.
- Select stable compatible versions: no release channel or anti-feature flags; use the preferred signer and reject native-only ABIs without arm64-v8a.
- Eighty priority candidates must have no declared nativecode in the selected index manifest; twenty explicit description-backed coverage slots comprise ten Compose six WebView four GL.
- Exclude existing package IDs and reject duplicate package or APK hashes. Preserve versionName versionCode minimum/target SDK and signer fingerprints.
- Predictions identify their evidence level. Index nativecode absence does not establish Java/Kotlin language, AndroidX classes, launch reachability or measured t20 success.
- Publish CSV JSON selected-index evidence and a handoff checklist. APK preparation and verification belong to oc-t4.

## 边界

### 允许修改
- benchmark/2026-10-01-corpus-v2/**
- specs/corpus-v2/**
- tools/spec-checks/tests/corpus_v2.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Index and selected APK identities reproduce
  测试: corpus_v2_identity
  假设 Pinned official index and entry reference with existing corpus identities
  当 The selection rows are constructed
  那么 One hundred unique new packages preserve exact indexed versions URLs SHA and signer identities

场景: Invalid ABI or source identities are rejected
  测试: corpus_v2_rejection
  假设 A mismatched index duplicate package or non-arm64 native-only candidate
  当 Input identity and eligibility checks run
  那么 The selection fails with a specific reason instead of inventing a compatible artifact

场景: Prediction priors retain evidence limits and coverage
  测试: corpus_v2_prediction
  假设 Eighty ABI-free priority and twenty description-backed coverage candidates
  当 The static metadata priors are generated
  那么 Every row separates first-wall uncertainty from t20 hypothesis and APK scanning remains explicitly pending

场景: Handoff tables replay deterministically
  测试: corpus_v2_replay
  假设 Compact source evidence and the exact seed list
  当 JSON CSV and README are regenerated
  那么 Output identities match and apps.json is unchanged

## 排除范围

- Treating an unsigned JSON hash match as cryptographic signer validation, accepting APK signature bytes, or hardcoding app runtime implementations.
