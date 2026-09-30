spec: task
name: "Task90 lane queue batch feedback and static missed families"
inherits: project
depends: [t4-r15c-next-walls]
---

## 意图

Continue the authorized lane queue without waiting for redispatch: evaluate completed batches against immutable predecessors, then add static candidate detectors for evidence-backed missing families.

## 已定决策

- Reject incomplete full batches by default; explicit partial mode cannot report full-batch completion.
- Join exact APK hashes, distinguish fatal from tolerated observations and preserve unknown denominators.
- Keep old prediction hashes unchanged; training observations are not prospective evaluation.
- Reuse bounded startup graph for CommonEvent, JobScheduler, ShortcutManager, Flutter guest load, JNA, EGL/camera references and native dependency inventory.
- Static APIs imply runtime requirements, not missing runtime implementations or actual execution; absent bounded paths remain unknown.

## 边界

### 允许修改
- benchmark/2026-09-29-static-wall-prediction/**
- tools/spec-checks/**
- specs/bms-static-v3/**
- README.md
- .octos/KNOWLEDGE-DIGEST.md

### 禁止
- No device operations, runtime changes, input writes, git metadata writes or mutation of frozen v4-r2/task90-r15c outputs.

## 验收标准

场景: 全量回测门与不确定性分母
  测试: b90_batch_feedback
  假设 Frozen predictions and a completed or incomplete batch exist
  当 The evaluator scores exact APK matches
  那么 Partial batches fail the default gate and unknown or tolerated observations are excluded explicitly
  并且 The r15c evaluation preserves the frozen predecessor hashes

场景: 漏报族规则有正反例
  测试: b90_feedback_rules
  假设 Synthetic DEX calls include framework wrappers and unrelated same-name methods
  当 New static rules inspect instructions
  那么 Supported wrapper signatures produce conditional candidates and unrelated methods do not
  并且 JNI or namespace implementation absence is never inferred from a call alone

场景: 新扫描覆盖三十二APK且证据可追踪
  测试: b90_feedback_coverage
  假设 The pinned 32 APK cohort and bounded startup scanner exist
  当 The feedback scan emits its machine-readable matrix
  那么 All seven families have an explicit verdict for every APK with hashes and startup evidence
  并且 New predictions are labeled outcome-informed and separate from earlier frozen outputs

## 排除范围

- Device repairs, accepting screenshots, proving a latent reference causes a specific failure, or treating partial r16 sanity as a completed full run.
