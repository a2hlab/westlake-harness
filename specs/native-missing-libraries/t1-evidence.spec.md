spec: task
name: "Correct four missing-library diagnoses from pinned evidence"
inherits: project
---

## 意图

Deliver machine-readable evidence for Element, BurgerKing, Chessclock and Mindustry, correcting plan errors using deployed ELF and DEX plus PID-bound fatal lines.

## 已定决策

- Use SHA256, SONAME, DT_NEEDED and exact undefined/exported symbols, not filenames, as donor identity.
- Preserve the original plans' hashes and record their rejected conclusions separately.
- Chessclock uses media_jni, not mediandk; libmediandk stays outside this batch.

## 边界

### 允许修改
- benchmark/2026-10-01-native-missing-libraries/**
- specs/native-missing-libraries/**
- tools/spec-checks/tests/native_missing_libraries.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Real alias and providers remain identity bound
  测试: native_missing_library_evidence
  假设 Pinned U8 artifacts and the r109c alias donor
  当 Evidence is collected and replayed
  那么 Alias SONAME and dependency and complete symbol coverage match their hashes

场景: Misnamed media diagnosis is rejected
  测试: native_missing_library_evidence
  假设 The U8 MediaPlayer static initializer and Chessclock fatal chain
  当 The requested loadLibrary argument is compared with the manifest
  那么 media_jni and registered runtime ownership are recorded and mediandk is not an unlock

场景: Changed provider bytes fail closed
  测试: native_missing_library_evidence
  假设 A donor with the right filename but a different SHA256 or missing exports
  当 The identity and coverage checks run
  那么 A ValueError is raised and no verified donor claim is emitted

## 排除范围

- Runtime acceptance, real media playback and predicting later fatal walls.
