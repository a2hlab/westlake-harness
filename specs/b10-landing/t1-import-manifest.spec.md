spec: task
name: "Prepare reproducible B10 landing instructions"
inherits: project
---

## 意图

Deliver exact new paths, B10 selector additions and a root README row for the outer loop to import. Reproduce the resulting master regression gate and explicitly list any unresolved acceptance exceptions instead of silently weakening checks.

## 已定决策

- Pin source and destination commits; paths.txt names files absent at the destination, not directories. Source-tracked inputs come from the pinned commit; eight ignored export lists are supplied as separately hash-verified recovery payloads matching the historical freeze.
- Preserve B10's complete scanner tree and the recorded evidence dependencies of its contracts; do not copy unrelated branch selectors.
- Run the imported selectors in a temporary master export. Document gate output, required local artifacts and any newly required exception separately from actual passes.

## 边界

### 允许修改
- benchmark/2026-10-01-b10-landing/**
- specs/b10-landing/**
- README.md
- .octos/KNOWLEDGE-DIGEST.md

### 禁止
- No historical evidence rewrites, existing scanner or selector edits, shared master writes, runtime deployment or pushes.

## 验收标准

场景: Imported core JNI evidence
  测试: b10_jni_matrix_known_answers
  假设 The additive import contains the original B10 matrices
  当 The imported known-answer selector runs in the master export
  那么 Both 5406-method matrices retain their known JNI classifications

场景: Native replay provenance is preserved
  测试: native_initialization_provenance
  假设 The native rule replay is included in the import
  当 Its provenance checks run from the disposable master export
  那么 Original source hashes replay coordinates and input-tamper rejection remain valid

场景: Feedback rules are executable
  测试: v2_feedback_rules
  假设 B10 feedback modules and dependencies are imported without changing their bytes
  当 The rule checks run from the disposable master export
  那么 Rule-level negative controls pass without changing frozen forecasts

## 排除范围

- Fixing baseline failures, approving new exceptions on behalf of the outer loop, importing unrelated BMS deployment contracts.
