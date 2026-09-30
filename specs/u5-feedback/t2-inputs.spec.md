spec: task
name: "Separate input blockers and freeze a new forecast version"
inherits: project
depends: [t1-rules.spec.md]
---

## 意图

Report split inputs, invalid AArch64 sidecars and APK pin drift separately from runtime risk families for all 66 frozen cohort keys.

## 已定决策

- Directory APK multiplicity, actual ELF headers and actual APK hashes determine input findings.
- Multiple input findings may coexist; do not rewrite pins, drop libraries or silently install splits.
- New predictions use a distinct version and retain the original CSV SHA.

## 边界

### 允许修改
- benchmark/2026-09-29-static-wall-prediction/rules_u5_feedback.py
- benchmark/2026-09-29-static-wall-prediction/scan_u5_feedback.py
- benchmark/2026-10-01-u5-feedback-v1/**
- specs/u5-feedback/**
- tools/spec-checks/tests/u5_feedback.rs
- README.md
- .octos/KNOWLEDGE-DIGEST.md

## 验收标准

场景: Input blockers are independent of app walls
  测试: u5_feedback_inputs
  假设 Split APKs invalid ELF headers and mismatched pins plus valid controls are present
  当 Input rules run
  那么 Three distinct blocker categories appear and a split key with pin drift retains both while mono multidex is not called split

场景: New forecasts preserve frozen evidence and can be replayed
  测试: u5_feedback_version
  假设 The 66-key frozen CSV and the versioned facts are available
  当 Predictions are verified
  那么 Original CSV SHA remains bae8fd74 and new JSON and CSV agree with independently regenerated results

## 排除范围

- Editing app inputs, repairing sidecars, changing existing selectors or exception approvals.

