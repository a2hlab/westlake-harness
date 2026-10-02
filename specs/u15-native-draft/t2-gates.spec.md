spec: task
name: "Fresh U15 native static review"
inherits: project
depends: ["t1-compose.spec.md"]
---

## 意图

Run available native gates and per-object open-site, namespace, strings, dynamic ABI and consumer comparisons against U14 content, retaining exact review evidence without granting admission.

## 已定决策

- Fresh N1/N2 reports bind the candidate manifest, actual source profiles and ANL namespace owner.
- Auto-identical rows are preview only; new findings and string/open deltas remain unsigned.
- Preserve raw return codes and hash-bound portable evidence, including failures or tool errors.
- Two computational Rust selectors run cold without private native artifacts; image and production gates remain pending.

## 边界

### 允许修改
- benchmark/2026-10-03-u15-native-draft/**
- specs/u15-native-draft/**
- tools/spec-checks/tests/u15_native_draft.rs

## 验收标准

场景: Reports retain native findings for review
  测试: u15_native_review
  假设 Native gate inputs and source profiles are tied to the composed ELF hashes
  当 Fresh Mac reports and binding previews are examined
  那么 Raw exits and new findings are retained while approvals and execution remain disabled

场景: Missing evidence or false approval is rejected
  测试: u15_native_review
  假设 No outer approval or completed U15 image build exists
  当 A report omits raw status or claims a preview was applied
  那么 Validation rejects the claim rather than substituting historical PASS

## 排除范围

- Apply exceptions, alter active tables, run production executors or use device/VM tools.
