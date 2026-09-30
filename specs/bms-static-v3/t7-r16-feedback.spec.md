spec: task
name: "R16 post-evaluation static feedback"
inherits: project
depends: [t6-r16-prospective]
---

## 意图

Continue the authorized queue after r16 scoring: add evidence-backed service/provider/JNI misses as conditional static requirements without changing the prospective forecast.

## 已定决策

- Use the existing bounded startup scanner and exact 32 APK cohort; keep all 66 run keys in the coverage table, with 34 explicitly unscanned.
- Detect eight requirement families: foreground service, battery, vibrator, PendingIntent, AlarmManager, Process CPU JNI, documents-provider permission and storage initializer.
- Static API use does not prove a null object, missing JNI or a runtime failure. Provider permission gaps require matching manifest provider and direct DocumentsProvider superclass initialization evidence.
- Preserve r16 forecast/scoring hashes. This scan learned from r16 and cannot be scored as an r16 prospective success.

## 边界

### 允许修改
- benchmark/2026-09-30-r16-feedback/**
- specs/bms-static-v3/**
- tools/spec-checks/**
- README.md

### 禁止
- No devices, runtime fixes, APK writes, git metadata writes, or changes under the frozen r16-prospective directory.

## 验收标准

场景: 规则正反例与不确定性
  测试: r16_feedback_rules
  假设 DEX invokes contain relevant framework APIs and unrelated names
  当 Eight requirement predicates inspect them
  那么 Exact API owners produce conditional requirements and unrelated owners do not
  并且 DocumentsProvider missing permission is distinguished from non-document providers and present permissions

场景: 矩阵覆盖与前瞻冻结不变
  测试: r16_feedback_matrix
  假设 Thirty-two pinned APKs and sixty-six observed keys exist
  当 The feedback matrix is emitted
  那么 All 256 app-family cells have explicit evidence or unknown/no-reference status
  并且 The original r16 prospective output and scorer hashes remain unchanged

## 排除范围

- Proving first-screen execution, inventing causes for seven unknown visual failures, and retroactively improving r16 prospective accuracy.
